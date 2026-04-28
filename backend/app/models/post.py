"""
Post model — maps to the `posts` table.
Schema source: docs/context/database_design.md §3.2
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Float, Text, DateTime, Index, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base


class Post(Base):
    """Stores per-post state: credibility, variance, urgency, propagation radius."""

    __tablename__ = "posts"

    post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[dict | None] = mapped_column(JSONB, nullable=True, doc="Post embedding vector")

    # ── Credibility (Formulas 8 & 10) ──
    c_bayes: Mapped[float | None] = mapped_column(Float, nullable=True, doc="C_Bayes ∈ [0,1]")
    c_ml: Mapped[float | None] = mapped_column(Float, nullable=True, doc="C_ML (Phase 5)")
    c_memory: Mapped[float | None] = mapped_column(Float, nullable=True, doc="C_memory (Phase 5)")
    c_final: Mapped[float | None] = mapped_column(Float, nullable=True, doc="C_final ∈ [0,1]")

    # ── Stability (Formula 9) ──
    variance: Mapped[float | None] = mapped_column(Float, nullable=True, doc="Var_j ≥ 0")

    # ── Interaction mass (Formula 6) ──
    n_effective: Mapped[float] = mapped_column(Float, default=0.0, doc="N_j(t) effective mass")
    s_plus: Mapped[float] = mapped_column(Float, default=0.0, doc="S_j⁺ positive signal mass")
    s_minus: Mapped[float] = mapped_column(Float, default=0.0, doc="S_j⁻ negative signal mass")

    # ── Urgency (Algorithm 5) ──
    urgency: Mapped[float | None] = mapped_column(Float, nullable=True, doc="U_j ∈ [0,1]")

    # ── Propagation ──
    radius: Mapped[float] = mapped_column(Float, default=1000.0, doc="Current propagation radius (meters)")

    # ── Location ──
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lon: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── Timing ──
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        Index("idx_posts_credibility", "c_final"),
        Index("idx_posts_created", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Post {self.post_id} C={self.c_final} U={self.urgency}>"
