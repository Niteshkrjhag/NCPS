"""
Interaction, UserLocation, UserGraph, and Alert models.
Schema source: docs/context/database_design.md §3.3–3.7
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Float,
    Integer,
    SmallInteger,
    DateTime,
    Index,
    ForeignKey,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base


class Interaction(Base):
    """Records each user vote on a post."""

    __tablename__ = "interactions"

    interaction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False
    )
    post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("posts.post_id"), nullable=False
    )
    vote: Mapped[int] = mapped_column(SmallInteger, nullable=False, doc="+1 or -1")
    weight: Mapped[float | None] = mapped_column(Float, nullable=True, doc="w_i at time of vote")
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        Index("idx_interactions_post", "post_id"),
        Index("idx_interactions_user", "user_id"),
        Index("idx_interactions_time", "timestamp"),
    )

    def __repr__(self) -> str:
        return f"<Interaction {self.user_id}→{self.post_id} vote={self.vote}>"


class UserLocation(Base):
    """Historical location samples for computing spatial signals."""

    __tablename__ = "user_locations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False
    )
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        Index("idx_user_locations_user_time", "user_id", "timestamp"),
    )


class UserGraph(Base):
    """Adjacency table for the user interaction graph (Phase 3 ready)."""

    __tablename__ = "user_graph"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True
    )
    neighbor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True
    )
    agreement_score: Mapped[float] = mapped_column(Float, default=0.0)
    time_similarity: Mapped[float] = mapped_column(Float, default=0.0)
    frequency_score: Mapped[float] = mapped_column(Float, default=0.0)
    edge_weight: Mapped[float] = mapped_column(Float, default=0.0)
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        Index("idx_graph_user", "user_id"),
    )


class Alert(Base):
    """Alerts sent to users about credible, urgent, nearby posts."""

    __tablename__ = "alerts"

    alert_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False
    )
    post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("posts.post_id"), nullable=False
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    delivered: Mapped[bool] = mapped_column(Boolean, default=False)

    __table_args__ = (
        Index("idx_alert_user_time", "user_id", "timestamp"),
    )


class UserAlertLimit(Base):
    """Rate-limiting table for user alerts."""

    __tablename__ = "user_alert_limits"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True
    )
    alert_count: Mapped[int] = mapped_column(Integer, default=0)
    last_reset: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
