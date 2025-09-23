"""
SQL execution module for db-router-svc.

This module provides whitelisted SQL templates and execution functions
for safe database queries.
"""

import asyncio
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional
import asyncpg
from loguru import logger
from models import Intent


# Whitelisted SQL templates with parameterized queries
INTENT_SQL = {
    Intent.FLIGHT_STATUS: (
        """
        SELECT flight_no, flight_date, origin, destination, sched_dep_time, sched_arr_time, status, tail_number
        FROM flights
        WHERE flight_no = $1
          AND (COALESCE($2, '') = '' OR flight_date = $2)
        ORDER BY flight_date DESC, sched_dep_time DESC
        LIMIT 1
        """,
        ["flight_no", "date"]
    ),
    
    Intent.NEXT_FLIGHT: (
        """
        SELECT flight_no, flight_date, origin, destination, sched_dep_time, sched_arr_time, status
        FROM flights
        WHERE destination = $1
          AND ($2::text IS NULL OR origin = $2::text)
          AND sched_dep_time > $3::timestamp
        ORDER BY sched_dep_time ASC
        LIMIT 3
        """,
        ["destination", "origin", "after_time"]
    ),
    
    Intent.FLIGHTS_FROM: (
        """
        SELECT flight_no, flight_date, origin, destination, sched_dep_time, sched_arr_time, status
        FROM flights
        WHERE origin = $1
          AND (COALESCE($2, '') = '' OR flight_date = $2)
        ORDER BY sched_dep_time ASC
        LIMIT 20
        """,
        ["origin", "date"]
    ),
    
    Intent.FLIGHTS_TO: (
        """
        SELECT flight_no, flight_date, origin, destination, sched_dep_time, sched_arr_time, status
        FROM flights
        WHERE destination = $1
          AND (COALESCE($2, '') = '' OR flight_date = $2)
        ORDER BY sched_dep_time ASC
        LIMIT 20
        """,
        ["destination", "date"]
    ),
    
    Intent.BOOKING_LOOKUP: (
        """
        SELECT pnr, passenger_name, flight_no, flight_date, has_connection, connecting_flight_no
        FROM bookings
        WHERE pnr = $1
        LIMIT 1
        """,
        ["pnr"]
    ),
    
    Intent.CREW_FOR_FLIGHT: (
        """
        SELECT r.crew_id, d.crew_name, r.flight_no, r.flight_date, r.crew_role
        FROM crew_roster r 
        JOIN crew_details d USING (crew_id)
        WHERE r.flight_no = $1 AND r.flight_date = $2
        LIMIT 20
        """,
        ["flight_no", "date"]
    ),
    
    Intent.AIRCRAFT_STATUS: (
        """
        SELECT tail_number, current_location, status
        FROM aircraft_status
        WHERE tail_number = $1
        LIMIT 1
        """,
        ["tail_number"]
    ),
    
    Intent.PASSENGER_COUNT: (
        """
        SELECT COUNT(*) as passenger_count, flight_no, flight_date
        FROM bookings
        WHERE flight_no = $1 AND flight_date = $2
        GROUP BY flight_no, flight_date
        LIMIT 1
        """,
        ["flight_no", "date"]
    ),
    
    Intent.CREW_AVAILABILITY: (
        """
        SELECT crew_id, crew_name, duty_start_time, max_duty_hours
        FROM crew_details
        WHERE duty_start_time > $1::timestamp
          AND ($2 IS NULL OR crew_role = $2)
        ORDER BY duty_start_time ASC
        LIMIT 50
        """,
        ["date", "role", "role"]
    ),
    
    Intent.AIRCRAFT_BY_LOCATION: (
        """
        SELECT tail_number, current_location, status
        FROM aircraft_status
        WHERE current_location = $1
        ORDER BY tail_number
        LIMIT 20
        """,
        ["location"]
    ),
}


class DatabaseExecutor:
    """Handles database connections and query execution."""
    
    def __init__(self, database_url: str, max_connections: int = 10):
        """
        Initialize database executor.
        
        Args:
            database_url: PostgreSQL connection URL
            max_connections: Maximum number of connections in pool
        """
        self.database_url = database_url
        self.max_connections = max_connections
        self.pool: Optional[asyncpg.Pool] = None
    
    async def initialize(self):
        """Initialize database connection pool."""
        try:
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=1,
                max_size=self.max_connections,
                command_timeout=2.0,  # 2 second timeout
                server_settings={
                    'application_name': 'db-router-svc',
                    'timezone': 'UTC'
                }
            )
            logger.info("Database connection pool initialized")
        except Exception as e:
            logger.error(f"Failed to initialize database pool: {e}")
            raise
    
    async def close(self):
        """Close database connection pool."""
        if self.pool:
            await self.pool.close()
            logger.info("Database connection pool closed")
    
    async def execute_query(
        self, 
        intent: Intent, 
        args: Dict[str, Any], 
        role: str = "public"
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Execute a whitelisted SQL query.
        
        Args:
            intent: Query intent
            args: Query arguments
            role: User role for PII masking
            
        Returns:
            Tuple of (results, row_count)
        """
        if not self.pool:
            raise RuntimeError("Database pool not initialized")
        
        if intent not in INTENT_SQL:
            raise ValueError(f"Unknown intent: {intent}")
        
        sql_template, param_names = INTENT_SQL[intent]
        
        # Prepare parameters in the correct order
        params = []
        for param_name in param_names:
            value = args.get(param_name)

            if param_name == "after_time":
                value = self._normalize_after_time(value)

            params.append(value)
        
        logger.debug(f"Executing query for intent {intent} with params: {params}")
        
        try:
            async with self.pool.acquire() as conn:
                # Execute query with timeout
                rows = await asyncio.wait_for(
                    conn.fetch(sql_template, *params),
                    timeout=2.0
                )
                
                # Convert rows to dictionaries
                results = [dict(row) for row in rows]
                
                # Apply PII masking based on role
                if role != "agent" and role != "admin":
                    from util import mask_pii_data
                    results = [mask_pii_data(row, role) for row in results]
                
                logger.info(f"Query executed successfully: {len(results)} rows returned")
                return results, len(results)
                
        except asyncio.TimeoutError:
            logger.error(f"Query timeout for intent {intent}")
            raise RuntimeError("Query execution timeout")
        except Exception as e:
            logger.error(f"Query execution failed for intent {intent}: {e}")
            raise

    @staticmethod
    def _normalize_after_time(value: Optional[Any]) -> datetime:
        """Normalize after_time into a concrete UTC timestamp."""
        if isinstance(value, datetime):
            return value

        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"", "now", "current", "immediately"}:
                return datetime.utcnow()

            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                logger.warning(
                    "after_time parse failure for value '%s'; defaulting to current UTC time",
                    value
                )
                return datetime.utcnow()

        return datetime.utcnow()

    async def test_connection(self) -> bool:
        """
        Test database connection.

        Returns:
            True if connection successful, False otherwise
        """
        if not self.pool:
            return False
        
        try:
            async with self.pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
                return True
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False


# Global executor instance
_executor: Optional[DatabaseExecutor] = None


async def initialize_database(database_url: str, max_connections: int = 10):
    """
    Initialize the global database executor.
    
    Args:
        database_url: PostgreSQL connection URL
        max_connections: Maximum number of connections in pool
    """
    global _executor
    _executor = DatabaseExecutor(database_url, max_connections)
    await _executor.initialize()


async def close_database():
    """Close the global database executor."""
    global _executor
    if _executor:
        await _executor.close()
        _executor = None


async def execute_intent_query(
    intent: Intent, 
    args: Dict[str, Any], 
    role: str = "public"
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Execute a query for the given intent and arguments.
    
    Args:
        intent: Query intent
        args: Query arguments
        role: User role for PII masking
        
    Returns:
        Tuple of (results, row_count)
    """
    if not _executor:
        raise RuntimeError("Database not initialized")
    
    return await _executor.execute_query(intent, args, role)


async def get_database_health() -> Dict[str, Any]:
    """
    Get database health status.
    
    Returns:
        Dictionary with health information
    """
    if not _executor:
        return {"status": "unavailable", "error": "Database not initialized"}
    
    try:
        is_healthy = await _executor.test_connection()
        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "pool_size": _executor.pool.get_size() if _executor.pool else 0,
            "max_connections": _executor.max_connections
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


def get_supported_intents() -> List[str]:
    """
    Get list of supported intents.
    
    Returns:
        List of supported intent names
    """
    return list(INTENT_SQL.keys())


def validate_intent_args(intent: Intent, args: Dict[str, Any]) -> bool:
    """
    Validate that the provided args match the expected parameters for the intent.
    
    Args:
        intent: Query intent
        args: Query arguments
        
    Returns:
        True if args are valid, False otherwise
    """
    if intent == Intent.KNOWLEDGE_BASE:
        return True

    if intent not in INTENT_SQL:
        return False
    
    _, param_names = INTENT_SQL[intent]
    
    # Define which parameters are optional for each intent
    optional_params = {
        Intent.FLIGHT_STATUS: ["date"],
        Intent.NEXT_FLIGHT: ["origin", "after_time"],
        Intent.FLIGHTS_FROM: ["date"],
        Intent.FLIGHTS_TO: ["date"],
        Intent.CREW_FOR_FLIGHT: ["date"],
        Intent.PASSENGER_COUNT: ["date"],
        Intent.CREW_AVAILABILITY: ["role"],
    }
    
    # Check that all required parameters are present
    required_params = [p for p in param_names if p not in optional_params.get(intent, [])]
    for param_name in required_params:
        if param_name not in args or args[param_name] is None:
            logger.warning(f"Missing required parameter '{param_name}' for intent {intent}")
            return False
    
    return True
