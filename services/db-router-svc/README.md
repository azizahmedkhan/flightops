# Database Router Service

A FastAPI microservice that converts natural language queries into safe, parameterized database queries using LLM function calling.

## Overview

The db-router-svc provides intelligent routing of natural language airline queries to appropriate database intents, executing whitelisted SQL templates and formatting results into user-friendly responses.

## Features

- **LLM Function Calling**: Uses OpenAI/Anthropic models to route queries to appropriate intents
- **Whitelisted SQL**: Only executes pre-approved, parameterized SQL templates
- **IATA Code Mapping**: Automatically converts city names to IATA codes
- **Time Normalization**: Handles relative time references ("today", "tomorrow", "now")
- **PII Masking**: Masks sensitive data based on user role
- **Rate Limiting**: Built-in rate limiting and timeout protection
- **Comprehensive Logging**: Structured logging with Loguru

## Supported Intents

- `flight_status`: Get status of a specific flight
- `next_flight`: Find next flights to a destination
- `flights_from`: List flights from an origin
- `flights_to`: List flights to a destination
- `booking_lookup`: Look up booking by PNR
- `crew_for_flight`: Get crew assigned to a flight
- `aircraft_status`: Get aircraft status
- `passenger_count`: Get passenger count for a flight
- `crew_availability`: Find available crew
- `aircraft_by_location`: Find aircraft at a location

## API Endpoints

### POST /route
Route a natural language query to the appropriate database intent.

**Request:**
```json
{
  "text": "What's the status of NZ278?"
}
```

**Response:**
```json
{
  "intent": "flight_status",
  "args": {
    "flight_no": "NZ278",
    "date": null
  },
  "confidence": 0.95
}
```

### POST /smart-query
Execute a complete smart query: route -> execute -> format.

**Request:**
```json
{
  "text": "When is the next flight to Wellington?",
  "auth": {
    "role": "public"
  }
}
```

**Response:**
```json
{
  "answer": "The next flights to Wellington are:\n• NZ278 departing at 14:30 today\n• NZ280 departing at 18:45 today",
  "rows": [...],
  "intent": "next_flight",
  "args": {...},
  "metadata": {...}
}
```

### GET /healthz
Health check endpoint.

### GET /intents
List all supported intents.

### GET /database/health
Get database connection health status.

## Configuration

### Environment Variables

- `DATABASE_URL`: PostgreSQL connection URL
- `OPENAI_API_KEY`: OpenAI API key for LLM calls
- `ANTHROPIC_API_KEY`: Anthropic API key (alternative to OpenAI)
- `LOG_LEVEL`: Logging level (default: INFO)

### Database Schema

The service expects the following tables:

```sql
-- Flights table
CREATE TABLE flights (
    flight_no VARCHAR(10),
    flight_date DATE,
    origin VARCHAR(3),
    destination VARCHAR(3),
    sched_dep_time TIMESTAMP,
    sched_arr_time TIMESTAMP,
    status VARCHAR(20),
    tail_number VARCHAR(10)
);

-- Bookings table
CREATE TABLE bookings (
    flight_no VARCHAR(10),
    flight_date DATE,
    pnr VARCHAR(10),
    passenger_name VARCHAR(100),
    has_connection BOOLEAN,
    connecting_flight_no VARCHAR(10)
);

-- Crew details table
CREATE TABLE crew_details (
    crew_id VARCHAR(20),
    crew_name VARCHAR(100),
    duty_start_time TIMESTAMP,
    max_duty_hours INTEGER
);

-- Crew roster table
CREATE TABLE crew_roster (
    flight_no VARCHAR(10),
    flight_date DATE,
    crew_id VARCHAR(20),
    crew_role VARCHAR(50)
);

-- Aircraft status table
CREATE TABLE aircraft_status (
    tail_number VARCHAR(10),
    current_location VARCHAR(3),
    status VARCHAR(20)
);
```

## Security Features

- **Parameterized Queries**: All SQL uses parameter binding to prevent injection
- **Whitelisted Templates**: Only pre-approved SQL templates can be executed
- **PII Masking**: Sensitive data is masked based on user role
- **Rate Limiting**: Built-in protection against abuse
- **Input Validation**: Comprehensive validation of all inputs
- **Timeout Protection**: Query execution timeouts prevent hanging

## Development

### Local Development

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set environment variables:
```bash
export DATABASE_URL="postgresql://user:password@localhost:5432/flightops"
export OPENAI_API_KEY="your-api-key"
```

3. Run the service:
```bash
python main.py
```

### Docker

```bash
docker build -t db-router-svc .
docker run -p 8000:8000 db-router-svc
```

## Testing

The service includes comprehensive tests for:
- Intent routing accuracy
- SQL execution safety
- PII masking functionality
- Time normalization
- IATA code mapping
- Error handling

Run tests with:
```bash
pytest tests/
```

## Monitoring

The service provides:
- Structured logging with request tracing
- Database connection health monitoring
- Query execution metrics
- Error rate tracking
- Performance monitoring

## Integration

The service integrates with:
- **Gateway API**: `/smart-ask` endpoint proxies to this service
- **Shared Services**: Uses shared LLM client and base service
- **Database**: PostgreSQL with connection pooling
- **Monitoring**: Prometheus metrics and health checks

## Error Handling

The service handles:
- Invalid intents and arguments
- Database connection failures
- Query timeouts
- LLM API failures
- Malformed requests
- Rate limit exceeded

All errors are logged and return appropriate HTTP status codes with descriptive error messages.
