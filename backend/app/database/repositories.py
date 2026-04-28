"""
Repository layer — CRUD operations for all models.
Abstracts database access for the API and engine layers.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.post import Post
from app.models.interaction import Interaction, UserLocation, Alert


# ──────────────────────────────────────────────────────────
# User Repository
# ──────────────────────────────────────────────────────────

class UserRepository:
    """Database operations for Users."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, user_id: uuid.UUID | None = None) -> User:
        """Create a new user with default state."""
        user = User(user_id=user_id or uuid.uuid4())
        self.session.add(user)
        await self.session.flush()
        return user

    async def get(self, user_id: uuid.UUID) -> User | None:
        """Get user by ID."""
        result = await self.session.execute(
            select(User).where(User.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_or_create(self, user_id: uuid.UUID) -> User:
        """Get existing user or create with defaults."""
        user = await self.get(user_id)
        if user is None:
            user = await self.create(user_id)
        return user

    async def update_state(
        self,
        user_id: uuid.UUID,
        alpha: float,
        beta: float,
        r_score: float,
        confidence: float,
        r_star: float,
        exp_raw: float,
        exp_score: float,
        anomaly_score: float,
        trust_score: float,
    ) -> None:
        """Update all computed user state fields."""
        user = await self.get(user_id)
        if user:
            user.alpha = alpha
            user.beta = beta
            user.r_score = r_score
            user.confidence = confidence
            user.r_star = r_star
            user.exp_raw = exp_raw
            user.exp_score = exp_score
            user.anomaly_score = anomaly_score
            user.trust_score = trust_score
            user.updated_at = datetime.now(timezone.utc)

    async def update_location(
        self,
        user_id: uuid.UUID,
        lat: float,
        lon: float,
        location_confidence: float = 0.5,
    ) -> None:
        """Update user's current location."""
        user = await self.get(user_id)
        if user:
            user.lat = lat
            user.lon = lon
            user.location_confidence = location_confidence
            user.updated_at = datetime.now(timezone.utc)


# ──────────────────────────────────────────────────────────
# Post Repository
# ──────────────────────────────────────────────────────────

class PostRepository:
    """Database operations for Posts."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        user_id: uuid.UUID,
        content: str,
        lat: float | None = None,
        lon: float | None = None,
        initial_radius: float = 1000.0,
    ) -> Post:
        """Create a new post."""
        post = Post(
            user_id=user_id,
            content=content,
            lat=lat,
            lon=lon,
            radius=initial_radius,
        )
        self.session.add(post)
        await self.session.flush()
        return post

    async def get(self, post_id: uuid.UUID) -> Post | None:
        """Get post by ID."""
        result = await self.session.execute(
            select(Post).where(Post.post_id == post_id)
        )
        return result.scalar_one_or_none()

    async def update_state(
        self,
        post_id: uuid.UUID,
        n_effective: float,
        s_plus: float,
        s_minus: float,
        c_bayes: float,
        c_final: float,
        variance: float,
    ) -> None:
        """Update post credibility and signal state."""
        post = await self.get(post_id)
        if post:
            post.n_effective = n_effective
            post.s_plus = s_plus
            post.s_minus = s_minus
            post.c_bayes = c_bayes
            post.c_final = c_final
            post.variance = variance
            post.updated_at = datetime.now(timezone.utc)

    async def update_urgency(self, post_id: uuid.UUID, urgency: float) -> None:
        """Update post urgency score."""
        post = await self.get(post_id)
        if post:
            post.urgency = urgency
            post.updated_at = datetime.now(timezone.utc)

    async def update_radius(self, post_id: uuid.UUID, radius: float) -> None:
        """Update propagation radius."""
        post = await self.get(post_id)
        if post:
            post.radius = radius
            post.updated_at = datetime.now(timezone.utc)

    async def get_feed(
        self,
        user_lat: float | None = None,
        user_lon: float | None = None,
        limit: int = 50,
    ) -> list[Post]:
        """Get posts ordered by credibility, optionally filtered by location."""
        query = (
            select(Post)
            .where(Post.c_final.isnot(None))
            .order_by(Post.c_final.desc(), Post.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())


# ──────────────────────────────────────────────────────────
# Interaction Repository
# ──────────────────────────────────────────────────────────

class InteractionRepository:
    """Database operations for Interactions."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        user_id: uuid.UUID,
        post_id: uuid.UUID,
        vote: int,
        weight: float | None = None,
    ) -> Interaction:
        """Record a new interaction (vote)."""
        interaction = Interaction(
            user_id=user_id,
            post_id=post_id,
            vote=vote,
            weight=weight,
        )
        self.session.add(interaction)
        await self.session.flush()
        return interaction

    async def get_by_post(self, post_id: uuid.UUID) -> list[Interaction]:
        """Get all interactions for a post."""
        result = await self.session.execute(
            select(Interaction)
            .where(Interaction.post_id == post_id)
            .order_by(Interaction.timestamp.asc())
        )
        return list(result.scalars().all())

    async def get_by_user(self, user_id: uuid.UUID) -> list[Interaction]:
        """Get all interactions by a user."""
        result = await self.session.execute(
            select(Interaction)
            .where(Interaction.user_id == user_id)
            .order_by(Interaction.timestamp.asc())
        )
        return list(result.scalars().all())

    async def check_duplicate(
        self, user_id: uuid.UUID, post_id: uuid.UUID
    ) -> bool:
        """Check if user already voted on this post."""
        result = await self.session.execute(
            select(func.count())
            .select_from(Interaction)
            .where(
                Interaction.user_id == user_id,
                Interaction.post_id == post_id,
            )
        )
        return result.scalar_one() > 0


# ──────────────────────────────────────────────────────────
# Alert Repository
# ──────────────────────────────────────────────────────────

class AlertRepository:
    """Database operations for Alerts."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        user_id: uuid.UUID,
        post_id: uuid.UUID,
    ) -> Alert:
        """Record a new alert."""
        alert = Alert(user_id=user_id, post_id=post_id)
        self.session.add(alert)
        await self.session.flush()
        return alert

    async def count_recent(
        self,
        user_id: uuid.UUID,
        window_seconds: float = 3600.0,
    ) -> int:
        """Count alerts sent to a user within a time window."""
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=window_seconds)
        result = await self.session.execute(
            select(func.count())
            .select_from(Alert)
            .where(
                Alert.user_id == user_id,
                Alert.timestamp >= cutoff,
            )
        )
        return result.scalar_one()


# ──────────────────────────────────────────────────────────
# Location History Repository
# ──────────────────────────────────────────────────────────

class LocationRepository:
    """Database operations for User Location History."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(
        self,
        user_id: uuid.UUID,
        lat: float,
        lon: float,
    ) -> UserLocation:
        """Record a location sample."""
        loc = UserLocation(user_id=user_id, lat=lat, lon=lon)
        self.session.add(loc)
        await self.session.flush()
        return loc

    async def get_history(
        self,
        user_id: uuid.UUID,
        limit: int = 100,
    ) -> list[UserLocation]:
        """Get recent location history for a user."""
        result = await self.session.execute(
            select(UserLocation)
            .where(UserLocation.user_id == user_id)
            .order_by(UserLocation.timestamp.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
