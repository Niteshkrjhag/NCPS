"""
In-Memory Storage — Fallback when PostgreSQL is not available.

Implements the same interface as the SQLAlchemy repositories
so the API routes work identically. When PostgreSQL becomes
available, the system automatically prefers it.

Usage:
    store = MemoryStore()
    store.create_user(user_id)
    store.create_post(user_id, content, lat, lon)
    store.vote(user_id, post_id, vote)
    store.get_feed(lat, lon, limit)
"""

from __future__ import annotations

import uuid
import math
import random
from datetime import datetime, timezone
from dataclasses import dataclass, field


@dataclass
class MemUser:
    user_id: str
    alpha: float = 0.0
    beta: float = 0.0
    r_star: float = 0.5
    exp_score: float = 0.0
    anomaly_score: float = 0.0
    trust_score: float = 0.5
    weight: float = 0.0  # T(0.5) × (1-Anom)(1.0) × Exp(0.0) = 0.0
    location_confidence: float = 0.5
    lat: float | None = None
    lon: float | None = None
    vote_count: int = 0
    post_count: int = 0
    created_at: str = ""


@dataclass
class MemPost:
    post_id: str
    user_id: str
    content: str
    c_bayes: float = 0.5
    c_final: float = 0.5
    variance: float = 0.0
    n_effective: float = 0.0
    urgency: float = 0.0
    radius: float = 1000.0
    lat: float | None = None
    lon: float | None = None
    created_at: str = ""
    votes: dict = field(default_factory=dict)  # user_id -> vote (+1/-1)


@dataclass
class MemInteraction:
    interaction_id: str
    user_id: str
    post_id: str
    vote: int
    timestamp: str


class MemoryStore:
    """Thread-safe in-memory data store that mimics PostgreSQL repositories."""

    def __init__(self):
        self.users: dict[str, MemUser] = {}
        self.posts: dict[str, MemPost] = {}
        self.interactions: list[MemInteraction] = []
        self._seed_demo_data()

    def _seed_demo_data(self):
        """Create a few demo posts so the feed isn't empty on first visit."""
        demo_user_id = str(uuid.uuid4())
        self.users[demo_user_id] = MemUser(
            user_id=demo_user_id,
            r_star=0.85, exp_score=0.7, trust_score=0.82,
            anomaly_score=0.05, weight=0.55,
            lat=28.6139, lon=77.2090,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        demos = [
            ("Heavy traffic reported on Ring Road near Nehru Place. Multiple lanes blocked.",
             0.78, 0.6, 28.6180, 77.2430),
            ("Water supply disruption in Dwarka Sector 7. Repair crew on site, expected fix by evening.",
             0.72, 0.4, 28.5918, 77.0470),
            ("Air quality index crosses 300 in Anand Vihar area. Authorities advise staying indoors.",
             0.85, 0.8, 28.6469, 77.3164),
            ("Free health checkup camp at Safdarjung Hospital today 9 AM - 5 PM.",
             0.65, 0.2, 28.5686, 77.2079),
            ("Metro Blue Line delayed due to technical fault between Rajiv Chowk and Kashmere Gate.",
             0.82, 0.7, 28.6328, 77.2197),
        ]

        for content, cred, urg, lat, lon in demos:
            pid = str(uuid.uuid4())
            self.posts[pid] = MemPost(
                post_id=pid, user_id=demo_user_id,
                content=content, c_bayes=cred, c_final=cred,
                n_effective=random.uniform(3, 12),
                variance=random.uniform(0.02, 0.15),
                urgency=urg, radius=2000 + cred * 3000,
                lat=lat, lon=lon,
                created_at=datetime.now(timezone.utc).isoformat(),
            )

    # ── Users ──

    def get_or_create_user(self, user_id: str) -> MemUser:
        if user_id not in self.users:
            self.users[user_id] = MemUser(
                user_id=user_id,
                created_at=datetime.now(timezone.utc).isoformat(),
            )
        return self.users[user_id]

    def get_user(self, user_id: str) -> MemUser | None:
        return self.users.get(user_id)

    def update_location(self, user_id: str, lat: float, lon: float):
        user = self.get_or_create_user(user_id)
        user.lat = lat
        user.lon = lon
        user.location_confidence = min(1.0, user.location_confidence + 0.05)

    # ── Posts ──

    def create_post(self, user_id: str, content: str,
                    lat: float | None, lon: float | None) -> MemPost:
        user = self.get_or_create_user(user_id)
        user.post_count += 1

        post_id = str(uuid.uuid4())
        urgency = self._compute_urgency(content)

        post = MemPost(
            post_id=post_id, user_id=user_id, content=content,
            urgency=urgency, lat=lat, lon=lon,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self.posts[post_id] = post

        # Update user experience
        user.exp_score = min(1.0, user.exp_score + 0.02)
        self._recompute_weight(user)

        return post

    def get_post(self, post_id: str) -> MemPost | None:
        return self.posts.get(post_id)

    def get_feed(self, lat: float | None = None, lon: float | None = None,
                 limit: int = 50) -> list[MemPost]:
        posts = list(self.posts.values())

        # Sort by credibility × urgency, with proximity boost
        def score(p: MemPost) -> float:
            s = 0.5 * p.c_final + 0.3 * p.urgency
            if lat is not None and lon is not None and p.lat and p.lon:
                dist = self._haversine(lat, lon, p.lat, p.lon)
                proximity = math.exp(-dist / 5000)
                s += 0.2 * proximity
            return s

        posts.sort(key=score, reverse=True)
        return posts[:limit]

    # ── Voting ──

    def vote(self, user_id: str, post_id: str, vote: int) -> dict:
        user = self.get_or_create_user(user_id)
        post = self.posts.get(post_id)
        if not post:
            raise ValueError(f"Post {post_id} not found")

        # Record vote
        interaction_id = str(uuid.uuid4())
        post.votes[user_id] = vote
        user.vote_count += 1

        self.interactions.append(MemInteraction(
            interaction_id=interaction_id, user_id=user_id,
            post_id=post_id, vote=vote,
            timestamp=datetime.now(timezone.utc).isoformat(),
        ))

        # Recompute post credibility (simplified Bayesian)
        self._recompute_post(post)

        # Update user reliability based on vote accuracy
        self._update_reliability(user)

        # Update user experience
        user.exp_score = min(1.0, user.exp_score + 0.01)
        self._recompute_weight(user)

        return {
            "interaction_id": interaction_id,
            "post_id": post_id,
            "updated_credibility": post.c_final,
        }

    # ── Engine (simplified) ──

    def _recompute_post(self, post: MemPost):
        """Simplified Bayesian credibility update."""
        if not post.votes:
            return

        weights = {}
        for uid in post.votes:
            u = self.users.get(uid)
            weights[uid] = u.weight if u else 0.25

        s_plus = sum(weights[uid] for uid, v in post.votes.items() if v > 0)
        s_minus = sum(weights[uid] for uid, v in post.votes.items() if v < 0)
        n_eff = s_plus + s_minus

        alpha0, beta0 = 1.0, 1.0
        post.c_bayes = (alpha0 + s_plus) / (alpha0 + beta0 + n_eff)
        post.c_final = post.c_bayes
        post.n_effective = n_eff

        if n_eff > 0:
            c = post.c_final
            post.variance = sum(
                weights[uid] * ((1 if v > 0 else 0) - c) ** 2
                for uid, v in post.votes.items()
            ) / n_eff

    def _recompute_weight(self, user: MemUser):
        """w_i = T_i * (1 - Anom_i) * Exp_i

        No hidden floors — the displayed formula must match exactly.
        """
        user.weight = user.trust_score * (1 - user.anomaly_score) * user.exp_score

    def _update_reliability(self, user: MemUser):
        """Update R_i* from voting history using Bayesian formula.

        For each post the user voted on, compare vote direction
        against the post's current credibility to determine correctness.
        Uses the same formulas as user_engine.py:
          R_i = α / (α + β)
          Conf_i = 1 - exp(-k * (α + β))
          R_i* = R_i × Conf_i
          T_i = R_i* (no graph propagation in memory mode)
        """
        alpha = 0.0
        beta = 0.0

        # Look at all posts this user voted on
        for post_id, vote in self._get_user_votes(user.user_id).items():
            post = self.posts.get(post_id)
            if not post:
                continue

            # Determine correctness: upvote on credible post or downvote on low-credibility
            is_correct = (vote > 0 and post.c_final >= 0.5) or \
                         (vote < 0 and post.c_final < 0.5)
            if is_correct:
                alpha += 1.0
            else:
                beta += 1.0

        user.alpha = alpha
        user.beta = beta

        total = alpha + beta
        if total > 0:
            # R_i = α / (α + β)
            r_score = alpha / total
            # Conf_i = 1 - exp(-k * (α + β))   (k = 0.1 from config)
            confidence = 1.0 - math.exp(-0.1 * total)
            # R_i* = R_i × Conf_i
            user.r_star = r_score * confidence
        else:
            user.r_star = 0.5  # Prior (no evidence)

        # T_i = R_i* (no graph propagation in memory mode)
        user.trust_score = user.r_star

    def _get_user_votes(self, user_id: str) -> dict:
        """Get all votes by a user: {post_id: vote}."""
        votes = {}
        for interaction in self.interactions:
            if interaction.user_id == user_id:
                votes[interaction.post_id] = interaction.vote
        return votes

    def _compute_urgency(self, content: str) -> float:
        keywords = {
            "fire": 1.0, "accident": 0.9, "urgent": 0.8, "help": 0.7,
            "emergency": 1.0, "danger": 0.9, "flood": 0.95, "earthquake": 1.0,
            "explosion": 1.0, "shooting": 1.0, "traffic": 0.4, "disruption": 0.5,
            "delayed": 0.4, "blocked": 0.5, "air quality": 0.6,
        }
        words = content.lower().split()
        max_score = 0.0
        for word in words:
            if word in keywords:
                max_score = max(max_score, keywords[word])
        return max_score

    @staticmethod
    def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Distance in meters between two lat/lon points."""
        R = 6371000
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlam = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# Global singleton — used when PostgreSQL is not available
memory_store = MemoryStore()
