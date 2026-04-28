"""
API Schemas — Pydantic models for request/response validation.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from pydantic import BaseModel, Field


# ── Request schemas ──

class CreatePostRequest(BaseModel):
    """POST /post/create"""

    user_id: uuid.UUID
    content: str = Field(..., min_length=1, max_length=5000)
    lat: float | None = None
    lon: float | None = None


class VoteRequest(BaseModel):
    """POST /post/vote"""

    user_id: uuid.UUID
    post_id: uuid.UUID
    vote: int = Field(..., description="+1 or -1")

    def model_post_init(self, __context: object) -> None:
        if self.vote not in (-1, 1):
            raise ValueError("Vote must be +1 or -1")


class LocationUpdateRequest(BaseModel):
    """POST /user/location"""

    user_id: uuid.UUID
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)


# ── Response schemas ──

class PostResponse(BaseModel):
    """Post data returned in API responses."""

    post_id: uuid.UUID
    user_id: uuid.UUID
    content: str
    credibility: float | None = None
    urgency: float | None = None
    variance: float | None = None
    radius: float
    n_effective: float
    lat: float | None = None
    lon: float | None = None
    created_at: datetime


class UserStateResponse(BaseModel):
    """User state data returned in API responses."""

    user_id: uuid.UUID
    r_star: float | None = None
    exp_score: float | None = None
    anomaly_score: float
    trust_score: float | None = None
    location_confidence: float
    lat: float | None = None
    lon: float | None = None


class VoteResponse(BaseModel):
    """Response after voting."""

    interaction_id: uuid.UUID
    post_id: uuid.UUID
    updated_credibility: float | None = None
    message: str = "Vote recorded"


class FeedResponse(BaseModel):
    """Response for the feed endpoint."""

    posts: list[PostResponse]
    total: int


class AlertResponse(BaseModel):
    """Alert notification data."""

    alert_id: uuid.UUID
    post_id: uuid.UUID
    user_id: uuid.UUID
    credibility: float
    urgency: float
    proximity: float
    timestamp: datetime
