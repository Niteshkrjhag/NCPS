"""
API Routes — All NCPS endpoints.

Endpoints from: docs/context/ncps_architecture.md §3.1
  POST /post/create
  POST /post/vote
  POST /user/location
  GET  /feed
"""

from __future__ import annotations

import uuid
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import config
from app.database.connection import get_session
from app.database.cache import cache
from app.database.repositories import (
    UserRepository,
    PostRepository,
    InteractionRepository,
    AlertRepository,
    LocationRepository,
)
from app.engine.user_engine import (
    InteractionRecord,
    compute_user_state,
)
from app.engine.post_engine import (
    PostInteraction,
    compute_post_state,
)
from app.engine.urgency import compute_urgency
from app.engine.decision import (
    PropagationInput,
    AlertInput,
    decide_propagation,
    decide_alert,
)
from app.event_pipeline import NCPSEvent, producer
from app.api.schemas import (
    CreatePostRequest,
    VoteRequest,
    LocationUpdateRequest,
    PostResponse,
    VoteResponse,
    FeedResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ──────────────────────────────────────────────────────────
# POST /post/create
# ──────────────────────────────────────────────────────────

@router.post("/post/create", response_model=PostResponse)
async def create_post(
    req: CreatePostRequest,
    session: AsyncSession = Depends(get_session),
) -> PostResponse:
    """Create a new post and publish event."""
    user_repo = UserRepository(session)
    post_repo = PostRepository(session)

    # Ensure user exists
    await user_repo.get_or_create(req.user_id)

    # Create post
    post = await post_repo.create(
        user_id=req.user_id,
        content=req.content,
        lat=req.lat,
        lon=req.lon,
        initial_radius=config.propagation_r_initial,
    )

    # Publish event to Kafka
    try:
        event = NCPSEvent(
            event_type="POST",
            user_id=str(req.user_id),
            post_id=str(post.post_id),
            payload={"content": req.content, "lat": req.lat, "lon": req.lon},
        )
        await producer.publish(event)
    except Exception as e:
        logger.warning(f"Failed to publish POST event: {e}")

    return PostResponse(
        post_id=post.post_id,
        user_id=post.user_id,
        content=post.content,
        credibility=post.c_final,
        urgency=post.urgency,
        variance=post.variance,
        radius=post.radius,
        n_effective=post.n_effective,
        lat=post.lat,
        lon=post.lon,
        created_at=post.created_at,
    )


# ──────────────────────────────────────────────────────────
# POST /post/vote
# ──────────────────────────────────────────────────────────

@router.post("/post/vote", response_model=VoteResponse)
async def vote_post(
    req: VoteRequest,
    session: AsyncSession = Depends(get_session),
) -> VoteResponse:
    """
    Process a vote on a post.

    End-to-end flow (ncps_architecture.md §7):
      Vote → User State Update → Post State Update → Decision Engine
    """
    user_repo = UserRepository(session)
    post_repo = PostRepository(session)
    interaction_repo = InteractionRepository(session)
    alert_repo = AlertRepository(session)

    # Validate
    post = await post_repo.get(req.post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")

    # Check duplicate vote
    if await interaction_repo.check_duplicate(req.user_id, req.post_id):
        raise HTTPException(status_code=409, detail="Already voted on this post")

    # Ensure user exists
    user = await user_repo.get_or_create(req.user_id)
    t_now = datetime.now(timezone.utc)

    # ── Step 1: Get user's interaction history and compute state ──
    user_interactions_db = await interaction_repo.get_by_user(req.user_id)

    # Convert to engine format
    user_interactions = [
        InteractionRecord(
            timestamp=i.timestamp,
            is_correct=None,  # Ground truth not available in real-time
            quality=1.0,
        )
        for i in user_interactions_db
    ]

    # Compute user state (Algorithm 1)
    action_counts = {"vote_up": 0, "vote_down": 0}
    for i in user_interactions_db:
        if i.vote == 1:
            action_counts["vote_up"] += 1
        else:
            action_counts["vote_down"] += 1
    # Count the current vote too
    if req.vote == 1:
        action_counts["vote_up"] += 1
    else:
        action_counts["vote_down"] += 1

    user_state = compute_user_state(
        interactions=user_interactions,
        action_counts=action_counts,
        t_now=t_now,
    )

    # Save user state
    await user_repo.update_state(
        user_id=req.user_id,
        alpha=user_state.alpha,
        beta=user_state.beta,
        r_score=user_state.r_score,
        confidence=user_state.confidence,
        r_star=user_state.r_star,
        exp_raw=user_state.exp_raw,
        exp_score=user_state.exp_score,
        anomaly_score=user_state.anomaly_score,
        trust_score=user_state.trust_score,
    )

    # ── Step 2: Record the interaction ──
    interaction = await interaction_repo.create(
        user_id=req.user_id,
        post_id=req.post_id,
        vote=req.vote,
        weight=user_state.weight,
    )

    # ── Step 3: Update post state (Algorithm 3) ──
    post_interactions_db = await interaction_repo.get_by_post(req.post_id)

    post_interactions = [
        PostInteraction(
            user_weight=i.weight or 0.0,
            vote=i.vote,
            timestamp=i.timestamp,
        )
        for i in post_interactions_db
    ]

    post_state = compute_post_state(
        interactions=post_interactions,
        t_now=t_now,
    )

    await post_repo.update_state(
        post_id=req.post_id,
        n_effective=post_state.n_effective,
        s_plus=post_state.s_plus,
        s_minus=post_state.s_minus,
        c_bayes=post_state.c_bayes,
        c_final=post_state.c_final,
        variance=post_state.variance,
    )

    # ── Step 4: Compute urgency ──
    urgency_val = compute_urgency(
        text=post.content,
        interactions=post_interactions,
        t_now=t_now,
    )
    await post_repo.update_urgency(req.post_id, urgency_val)

    # ── Step 5: Cache to Redis ──
    try:
        await cache.cache_user_state(req.user_id, user_state.weight, user_state.trust_score)
        await cache.cache_post_state(req.post_id, post_state.c_final, urgency_val, post_state.variance)
    except Exception as e:
        logger.warning(f"Redis cache update failed: {e}")

    # ── Step 6: Propagation decision (Algorithm 6) ──
    post_age = _time_delta_seconds(t_now, post.created_at)

    # Gather contributor data for spatial trust
    contributor_weights = [i.weight or 0.0 for i in post_interactions_db]
    contributor_locs = []
    contributor_decays = []
    for i in post_interactions_db:
        u = await user_repo.get(i.user_id)
        contributor_locs.append(u.location_confidence if u else 0.5)
        import math
        dt = _time_delta_seconds(t_now, i.timestamp)
        contributor_decays.append(math.exp(-config.lambda_interaction * dt))

    prop_result = decide_propagation(PropagationInput(
        c_final=post_state.c_final,
        n_effective=post_state.n_effective,
        variance=post_state.variance,
        post_age_seconds=post_age,
        current_radius=post.radius,
        contributor_weights=contributor_weights,
        contributor_location_confs=contributor_locs,
        contributor_decays=contributor_decays,
    ))

    if prop_result.should_expand:
        await post_repo.update_radius(req.post_id, prop_result.new_radius)

    # ── Step 7: Publish event to Kafka ──
    try:
        event = NCPSEvent(
            event_type="VOTE",
            user_id=str(req.user_id),
            post_id=str(req.post_id),
            payload={
                "vote": req.vote,
                "credibility": post_state.c_final,
                "weight": user_state.weight,
            },
        )
        await producer.publish(event)
    except Exception as e:
        logger.warning(f"Failed to publish VOTE event: {e}")

    return VoteResponse(
        interaction_id=interaction.interaction_id,
        post_id=req.post_id,
        updated_credibility=post_state.c_final,
        message="Vote recorded successfully",
    )


# ──────────────────────────────────────────────────────────
# POST /user/location
# ──────────────────────────────────────────────────────────

@router.post("/user/location")
async def update_location(
    req: LocationUpdateRequest,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Update user location and record in history."""
    user_repo = UserRepository(session)
    location_repo = LocationRepository(session)

    user = await user_repo.get_or_create(req.user_id)

    # Record in history
    await location_repo.add(req.user_id, req.lat, req.lon)

    # Update current location (simplified L_i for MVP)
    await user_repo.update_location(
        user_id=req.user_id,
        lat=req.lat,
        lon=req.lon,
        location_confidence=0.5,  # Default in MVP; full computation in Phase 4
    )

    # Publish event
    try:
        event = NCPSEvent(
            event_type="LOCATION",
            user_id=str(req.user_id),
            payload={"lat": req.lat, "lon": req.lon},
        )
        await producer.publish(event)
    except Exception as e:
        logger.warning(f"Failed to publish LOCATION event: {e}")

    return {"status": "ok", "user_id": str(req.user_id), "lat": req.lat, "lon": req.lon}


# ──────────────────────────────────────────────────────────
# GET /feed
# ──────────────────────────────────────────────────────────

@router.get("/feed", response_model=FeedResponse)
async def get_feed(
    user_lat: float | None = None,
    user_lon: float | None = None,
    limit: int = 50,
    session: AsyncSession = Depends(get_session),
) -> FeedResponse:
    """
    Get the credibility-ranked feed.

    Feed ranking: score = w1 × credibility + w2 × proximity + w3 × urgency
    Source: frontend_system_design.md §8
    """
    post_repo = PostRepository(session)

    posts = await post_repo.get_feed(
        user_lat=user_lat,
        user_lon=user_lon,
        limit=limit,
    )

    post_responses = [
        PostResponse(
            post_id=p.post_id,
            user_id=p.user_id,
            content=p.content,
            credibility=p.c_final,
            urgency=p.urgency,
            variance=p.variance,
            radius=p.radius,
            n_effective=p.n_effective,
            lat=p.lat,
            lon=p.lon,
            created_at=p.created_at,
        )
        for p in posts
    ]

    return FeedResponse(posts=post_responses, total=len(post_responses))


def _time_delta_seconds(t_now: datetime, t_event: datetime) -> float:
    """Compute time difference in seconds."""
    delta = (t_now - t_event).total_seconds()
    return max(delta, 0.0)
