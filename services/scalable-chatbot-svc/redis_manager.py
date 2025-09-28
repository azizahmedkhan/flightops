"""Redis-backed session and response caching for the chatbot service."""

import json
from typing import Any, Dict, Optional

import redis.asyncio as redis


class RedisManager:
    """Redis-based session and context management."""

    def __init__(self, redis_url: str = "redis://redis:6379") -> None:
        self.redis_url = redis_url
        self.redis_client = None

    async def connect(self) -> None:
        """Initialize Redis connection."""
        self.redis_client = redis.from_url(self.redis_url, decode_responses=True)

    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()

    async def get_session_context(self, session_id: str) -> Dict[str, Any]:
        """Get session context from Redis."""
        if not self.redis_client:
            return {}

        try:
            context_data = await self.redis_client.hgetall(f"session:{session_id}")
            if context_data:
                for key in ["flight_data", "policy_data", "sentiment_history"]:
                    if key in context_data:
                        try:
                            context_data[key] = json.loads(context_data[key])
                        except Exception:
                            context_data[key] = {}

                if "message_count" in context_data:
                    try:
                        context_data["message_count"] = int(context_data["message_count"])
                    except (ValueError, TypeError):
                        context_data["message_count"] = 0

            return context_data
        except Exception as exc:
            print(f"Redis get error: {exc}")
            return {}

    async def set_session_context(self, session_id: str, context: Dict[str, Any], ttl: int = 3600) -> None:
        """Store session context in Redis with TTL."""
        if not self.redis_client:
            return

        try:
            serialized_context: Dict[str, str] = {}
            for key, value in context.items():
                if isinstance(value, (dict, list)):
                    serialized_context[key] = json.dumps(value)
                else:
                    serialized_context[key] = str(value)

            await self.redis_client.hset(f"session:{session_id}", mapping=serialized_context)
            await self.redis_client.expire(f"session:{session_id}", ttl)
        except Exception as exc:
            print(f"Redis set error: {exc}")

    async def cache_response(self, query_hash: str, response: str, ttl: int = 1800) -> None:
        """Cache ChatGPT response to avoid duplicate API calls."""
        if not self.redis_client:
            return

        try:
            await self.redis_client.setex(f"response:{query_hash}", ttl, response)
        except Exception as exc:
            print(f"Redis cache error: {exc}")

    async def get_cached_response(self, query_hash: str) -> Optional[str]:
        """Get cached ChatGPT response."""
        if not self.redis_client:
            return None

        try:
            return await self.redis_client.get(f"response:{query_hash}")
        except Exception as exc:
            print(f"Redis get cache error: {exc}")
            return None
