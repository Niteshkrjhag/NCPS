"""
Redis cache layer for real-time NCPS values.
Source: docs/context/database_design.md §5

Cached keys:
  user:{id}:weight   → w_i
  user:{id}:trust    → T_i
  post:{id}:credibility → C_j
  post:{id}:urgency  → U_j
  post:{id}:variance → Var_j
  alert_count:{user_id} → rate-limit counter
"""

from __future__ import annotations

import uuid
from typing import Optional

import redis.asyncio as redis

from app.config import config


class RedisCache:
    """Async Redis cache for real-time NCPS values."""

    def __init__(self) -> None:
        self._client: Optional[redis.Redis] = None

    async def connect(self) -> None:
        """Initialize Redis connection."""
        self._client = redis.from_url(
            config.redis_url,
            decode_responses=True,
        )

    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.close()

    @property
    def client(self) -> redis.Redis:
        if self._client is None:
            raise RuntimeError("Redis not connected. Call connect() first.")
        return self._client

    # ── User cache ──

    async def set_user_weight(self, user_id: uuid.UUID, weight: float) -> None:
        """Cache user weight w_i."""
        await self.client.set(f"user:{user_id}:weight", str(weight))

    async def get_user_weight(self, user_id: uuid.UUID) -> float | None:
        """Get cached user weight."""
        val = await self.client.get(f"user:{user_id}:weight")
        return float(val) if val else None

    async def set_user_trust(self, user_id: uuid.UUID, trust: float) -> None:
        """Cache user trust T_i."""
        await self.client.set(f"user:{user_id}:trust", str(trust))

    async def get_user_trust(self, user_id: uuid.UUID) -> float | None:
        """Get cached user trust."""
        val = await self.client.get(f"user:{user_id}:trust")
        return float(val) if val else None

    # ── Post cache ──

    async def set_post_credibility(self, post_id: uuid.UUID, credibility: float) -> None:
        """Cache post credibility C_j."""
        await self.client.set(f"post:{post_id}:credibility", str(credibility))

    async def get_post_credibility(self, post_id: uuid.UUID) -> float | None:
        """Get cached post credibility."""
        val = await self.client.get(f"post:{post_id}:credibility")
        return float(val) if val else None

    async def set_post_urgency(self, post_id: uuid.UUID, urgency: float) -> None:
        """Cache post urgency U_j."""
        await self.client.set(f"post:{post_id}:urgency", str(urgency))

    async def get_post_urgency(self, post_id: uuid.UUID) -> float | None:
        """Get cached post urgency."""
        val = await self.client.get(f"post:{post_id}:urgency")
        return float(val) if val else None

    async def set_post_variance(self, post_id: uuid.UUID, variance: float) -> None:
        """Cache post variance Var_j."""
        await self.client.set(f"post:{post_id}:variance", str(variance))

    async def get_post_variance(self, post_id: uuid.UUID) -> float | None:
        """Get cached post variance."""
        val = await self.client.get(f"post:{post_id}:variance")
        return float(val) if val else None

    # ── Alert rate limiting ──

    async def increment_alert_count(
        self, user_id: uuid.UUID, window_seconds: int = 3600
    ) -> int:
        """Increment alert counter for rate limiting with TTL."""
        key = f"alert_count:{user_id}"
        count = await self.client.incr(key)
        if count == 1:
            # First alert in window — set TTL
            await self.client.expire(key, window_seconds)
        return count

    async def get_alert_count(self, user_id: uuid.UUID) -> int:
        """Get current alert count for rate limiting."""
        val = await self.client.get(f"alert_count:{user_id}")
        return int(val) if val else 0

    # ── Bulk operations ──

    async def cache_user_state(
        self,
        user_id: uuid.UUID,
        weight: float,
        trust: float,
    ) -> None:
        """Cache all user state values in a pipeline."""
        async with self.client.pipeline() as pipe:
            pipe.set(f"user:{user_id}:weight", str(weight))
            pipe.set(f"user:{user_id}:trust", str(trust))
            await pipe.execute()

    async def cache_post_state(
        self,
        post_id: uuid.UUID,
        credibility: float,
        urgency: float,
        variance: float,
    ) -> None:
        """Cache all post state values in a pipeline."""
        async with self.client.pipeline() as pipe:
            pipe.set(f"post:{post_id}:credibility", str(credibility))
            pipe.set(f"post:{post_id}:urgency", str(urgency))
            pipe.set(f"post:{post_id}:variance", str(variance))
            await pipe.execute()


# Singleton instance
cache = RedisCache()
