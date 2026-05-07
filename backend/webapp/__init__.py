"""
Webapp API Server — Production User-Facing Backend.

Standalone FastAPI server for the user-facing webapp.
Uses in-memory storage by default, prefers PostgreSQL when available.

Run: python -m webapp.server
  OR: cd backend && python -m webapp.server

Completely independent from simulation/api_server.py.
"""

from __future__ import annotations

import os
import sys
import uuid
from datetime import datetime, timezone

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from app.database.memory_store import memory_store

app = FastAPI(title="NCPS — User App", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Serve webapp static files ──
_backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
webapp_dir = os.path.join(os.path.dirname(_backend_dir), "webapp")

if os.path.exists(webapp_dir):
    app.mount("/static", StaticFiles(directory=webapp_dir), name="static")


# ── Request schemas ──

class CreatePostRequest(BaseModel):
    user_id: str
    content: str = Field(..., min_length=1, max_length=5000)
    lat: float | None = None
    lon: float | None = None


class VoteRequest(BaseModel):
    user_id: str
    post_id: str
    vote: int = Field(..., description="+1 or -1")


class LocationRequest(BaseModel):
    user_id: str
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)


class RegisterRequest(BaseModel):
    user_id: str | None = None


# ── HTML Pages ──

@app.get("/")
async def index():
    return FileResponse(os.path.join(webapp_dir, "index.html"))


@app.get("/report.html")
async def report_page():
    return FileResponse(os.path.join(webapp_dir, "report.html"))


@app.get("/map.html")
async def map_page():
    return FileResponse(os.path.join(webapp_dir, "map.html"))


@app.get("/profile.html")
async def profile_page():
    return FileResponse(os.path.join(webapp_dir, "profile.html"))


# ── API Endpoints ──

@app.get("/api/health")
async def health():
    return {"status": "ok", "mode": "memory", "version": "1.0.0"}


@app.post("/api/register")
async def register(req: RegisterRequest):
    """Register or identify a user. Returns user_id."""
    user_id = req.user_id or str(uuid.uuid4())
    user = memory_store.get_or_create_user(user_id)
    return {
        "user_id": user.user_id,
        "trust_score": user.trust_score,
        "created": user.created_at,
    }


@app.get("/api/feed")
async def get_feed(lat: float | None = None, lon: float | None = None,
                   limit: int = 50):
    """Get feed ranked by credibility × proximity × urgency."""
    posts = memory_store.get_feed(lat, lon, limit)
    return {
        "posts": [_post_to_dict(p, lat, lon) for p in posts],
        "total": len(posts),
    }


@app.post("/api/post/create")
async def create_post(req: CreatePostRequest):
    """Create a new post."""
    post = memory_store.create_post(
        user_id=req.user_id,
        content=req.content,
        lat=req.lat,
        lon=req.lon,
    )
    return {
        "post_id": post.post_id,
        "credibility": post.c_final,
        "urgency": post.urgency,
        "message": "Post created. Credibility will update as the community votes.",
    }


@app.post("/api/post/vote")
async def vote_post(req: VoteRequest):
    """Vote on a post."""
    if req.vote not in (-1, 1):
        raise HTTPException(400, "Vote must be +1 or -1")
    try:
        result = memory_store.vote(req.user_id, req.post_id, req.vote)
        return {
            "interaction_id": result["interaction_id"],
            "post_id": result["post_id"],
            "updated_credibility": round(result["updated_credibility"], 3),
            "message": "Vote recorded",
        }
    except ValueError as e:
        raise HTTPException(404, str(e))


@app.get("/api/post/{post_id}")
async def get_post(post_id: str):
    """Get a single post with details."""
    post = memory_store.get_post(post_id)
    if not post:
        raise HTTPException(404, "Post not found")
    return _post_to_dict(post)


@app.post("/api/user/location")
async def update_location(req: LocationRequest):
    """Update user location."""
    memory_store.update_location(req.user_id, req.lat, req.lon)
    user = memory_store.get_user(req.user_id)
    return {
        "user_id": req.user_id,
        "location_confidence": round(user.location_confidence, 3) if user else 0.5,
        "message": "Location updated",
    }


@app.get("/api/user/{user_id}/state")
async def get_user_state(user_id: str):
    """Get user state — trust scores, experience, anomaly."""
    user = memory_store.get_user(user_id)
    if not user:
        raise HTTPException(404, "User not found")
    return {
        "user_id": user.user_id,
        "r_star": round(user.r_star, 3),
        "exp_score": round(user.exp_score, 3),
        "anomaly_score": round(user.anomaly_score, 3),
        "trust_score": round(user.trust_score, 3),
        "weight": round(user.weight, 3),
        "location_confidence": round(user.location_confidence, 3),
        "vote_count": user.vote_count,
        "post_count": user.post_count,
        "created_at": user.created_at,
    }


# ── Helpers ──

def _post_to_dict(post, user_lat=None, user_lon=None) -> dict:
    """Convert MemPost to API response dict."""
    distance = None
    if user_lat and user_lon and post.lat and post.lon:
        distance = round(memory_store._haversine(user_lat, user_lon, post.lat, post.lon))

    # Soft engagement indicators
    indicators = []
    if post.c_final >= 0.75 and post.n_effective >= 5:
        indicators.append("Community Verified")
    if post.urgency >= 0.6:
        indicators.append("Trending")
    if post.n_effective >= 8:
        indicators.append("Frequently Discussed")
    if post.c_final >= 0.6 and post.variance < 0.1:
        indicators.append("Recommended")

    return {
        "post_id": post.post_id,
        "user_id": post.user_id[:8],
        "content": post.content,
        "credibility": round(post.c_final, 3),
        "c_bayes": round(post.c_bayes, 3),
        "variance": round(post.variance, 3),
        "n_effective": round(post.n_effective, 1),
        "urgency": round(post.urgency, 2),
        "radius": round(post.radius),
        "lat": post.lat,
        "lon": post.lon,
        "created_at": post.created_at,
        "vote_count": len(post.votes),
        "distance_m": distance,
        "indicators": indicators,
    }


if __name__ == "__main__":
    import uvicorn
    print("\n  NCPS Webapp — http://localhost:8000\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
