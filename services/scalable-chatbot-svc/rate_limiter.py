"""Rate limiting utilities for the scalable chatbot service."""

import time
from typing import Dict, List

from redis_manager import RedisManager


class RateLimiter:
    """Rate limiting for ChatGPT API calls."""

    def __init__(self, redis_manager: RedisManager) -> None:
        self.redis_manager = redis_manager
        self.local_limits: Dict[str, List[float]] = {}

    async def is_rate_limited(self, key: str, limit: int = 60, window: int = 60) -> bool:
        """Return True when the rate limit is exceeded for the given key."""
        current_time = time.time()

        if key in self.local_limits:
            self.local_limits[key] = [
                timestamp for timestamp in self.local_limits[key]
                if current_time - timestamp < window
            ]
        else:
            self.local_limits[key] = []

        if len(self.local_limits[key]) >= limit:
            return True

        self.local_limits[key].append(current_time)
        return False
