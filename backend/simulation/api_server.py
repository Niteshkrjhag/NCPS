"""
Simulation API Server -- Phase 6 Dashboard Backend.

Standalone FastAPI server that runs simulations and serves results
for the frontend dashboard. Does NOT require PostgreSQL/Redis/Kafka.
"""

from __future__ import annotations

import sys
import os
import json
import uuid
from datetime import datetime, timezone

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from simulation.runner import ExperimentConfig, run_experiment, run_all_experiments
from simulation.simulator import Simulator, UserType, PostLabel
from app.engine.user_engine import InteractionRecord, compute_user_state, compute_reliability
from app.engine.post_engine import PostInteraction, compute_post_state
from app.engine.graph_engine import VoteRecord, run_graph_pipeline
from app.engine.spatial import (
    LocationRecord, compute_location_confidence,
    compute_location_inconsistency,
)
from app.engine.signal_engine import compute_all_extended_signals
from app.engine.ml_engine import (
    CredibilityMLModel, MemoryEngine, AnomalyMLModel,
    MemoryEntry, extract_post_features, extract_user_behavior_features,
)

app = FastAPI(title="NCPS Dashboard API", version="0.6.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Serve frontend ──
# frontend/ is at repo root: NCPS/frontend
# This file is at NCPS/backend/simulation/api_server.py
_backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
frontend_dir = os.path.join(os.path.dirname(_backend_dir), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")


class SimulationRequest(BaseModel):
    scenario: str = "attack"  # attack, baseline, noisy
    phase: int = 6


class CompareRequest(BaseModel):
    pass


@app.get("/")
async def index():
    """Serve the dashboard."""
    return FileResponse(os.path.join(frontend_dir, "index.html"))


@app.get("/post.html")
async def post_page():
    return FileResponse(os.path.join(frontend_dir, "post.html"))


@app.get("/user.html")
async def user_page():
    return FileResponse(os.path.join(frontend_dir, "user.html"))


@app.get("/compare.html")
async def compare_page():
    return FileResponse(os.path.join(frontend_dir, "compare.html"))


@app.get("/map.html")
async def map_page():
    return FileResponse(os.path.join(frontend_dir, "map.html"))


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "0.6.0"}


@app.post("/api/simulation/run")
async def run_simulation(req: SimulationRequest):
    """Run a single simulation and return full state."""
    attack_cfg = dict(num_honest=40, num_noisy=5, num_adversarial=5,
                      num_bots=20, bot_groups=4) if req.scenario == "attack" else \
                 dict(num_honest=70, num_noisy=0, num_adversarial=0, num_bots=0)

    cfg = ExperimentConfig(
        name=f"Phase {req.phase}: {req.scenario}",
        **attack_cfg,
        use_graph=req.phase >= 3,
        use_spatial=req.phase >= 4,
        use_ml=req.phase >= 5,
        use_signals=req.phase >= 6,
    )

    # Run full sim and collect state for dashboard
    result = _run_full_state(cfg)
    return result


@app.get("/api/simulation/compare")
async def compare_phases():
    """Run all phases and return comparison data."""
    results = run_all_experiments()
    comparison = {}
    for key, metrics in results.items():
        comparison[key] = {
            "accuracy": round(metrics.accuracy, 3),
            "attack_success": round(metrics.attack_success_rate, 3),
            "brier_score": round(metrics.brier_score, 3),
            "weight_correlation": round(metrics.weight_correlation, 3),
            "anomaly_precision": round(metrics.anomaly_precision, 3),
            "anomaly_recall": round(metrics.anomaly_recall, 3),
        }
    return comparison


def _run_full_state(cfg: ExperimentConfig) -> dict:
    """Run simulation and return full state for dashboard visualization."""
    import random
    random.seed(cfg.seed)

    sim = Simulator(
        num_honest=cfg.num_honest, num_noisy=cfg.num_noisy,
        num_adversarial=cfg.num_adversarial, num_bots=cfg.num_bots,
        bot_groups=cfg.bot_groups, num_true_posts=cfg.num_true_posts,
        num_false_posts=cfg.num_false_posts, seed=cfg.seed,
    )
    interactions = sim.generate_interactions(
        time_steps=cfg.time_steps, interactions_per_step=cfg.interactions_per_step,
    )
    t_now = datetime.now(timezone.utc)

    # Build user interaction maps
    user_interactions = {}
    user_action_counts = {}
    user_votes = {}
    for inter in interactions:
        uid = str(inter.user_id)
        if uid not in user_interactions:
            user_interactions[uid] = []
            user_action_counts[uid] = {"vote_up": 0, "vote_down": 0}
            user_votes[uid] = []
        user_interactions[uid].append(InteractionRecord(
            timestamp=inter.timestamp, is_correct=inter.is_correct, quality=1.0,
        ))
        user_votes[uid].append(inter.vote)
        if inter.vote == 1:
            user_action_counts[uid]["vote_up"] += 1
        else:
            user_action_counts[uid]["vote_down"] += 1

    # R_i*
    r_star_scores = {}
    for user in sim.users:
        uid = str(user.user_id)
        _, _, _, _, r_star = compute_reliability(user_interactions.get(uid, []), t_now)
        r_star_scores[uid] = r_star

    # Graph
    graph_trust = {}
    coord_scores = {}
    graph_edges = []
    if cfg.use_graph:
        vote_records = [VoteRecord(user_id=str(i.user_id), post_id=str(i.post_id),
                                   vote=i.vote, timestamp=i.timestamp) for i in interactions]
        graph_state = run_graph_pipeline(vote_records, r_star_scores)
        graph_trust = graph_state.trust_scores
        coord_scores = graph_state.coordination_scores
        for uid, neighbors in graph_state.edges.items():
            for nid, weight in neighbors.items():
                if weight > 0.1:
                    graph_edges.append({"source": uid, "target": nid, "weight": round(weight, 3)})

    # Spatial
    location_confidences = {}
    location_inconsistencies = {}
    if cfg.use_spatial:
        raw_histories = sim.generate_location_history(time_steps=cfg.time_steps)
        for user in sim.users:
            uid = str(user.user_id)
            hist = [LocationRecord(lat=r["lat"], lon=r["lon"], timestamp=r["timestamp"],
                                   accuracy_meters=r["accuracy"], source=r["source"])
                    for r in raw_histories.get(uid, [])]
            location_confidences[uid] = compute_location_confidence(hist)
            location_inconsistencies[uid] = compute_location_inconsistency(hist)

    # Extended signals
    ext_signals = {}
    if cfg.use_signals:
        user_metadata = sim.generate_user_metadata(interactions)
        for user in sim.users:
            uid = str(user.user_id)
            meta = user_metadata.get(uid, {})
            signals = compute_all_extended_signals(
                device_ids=meta.get("device_ids"),
                ip_addresses=meta.get("ip_addresses"),
                ip_locations=meta.get("ip_locations"),
                timestamps=meta.get("timestamps"),
            )
            ext_signals[uid] = {
                "navigation": round(signals.navigation_deviation, 3),
                "device": round(signals.device_consistency, 3),
                "ip": round(signals.ip_consistency, 3),
                "session": round(signals.session_continuity, 3),
                "timing": round(signals.timing_irregularity, 3),
            }

    # ML
    ml_anomaly_scores = {}
    ml_cred_scores = {}
    if cfg.use_ml:
        cred_model = CredibilityMLModel()
        anom_model = AnomalyMLModel()

        # Train
        train_features, train_labels = [], []
        post_vote_counts = {}
        post_early_votes = {}
        for inter in interactions:
            pid = str(inter.post_id)
            post_vote_counts[pid] = post_vote_counts.get(pid, 0) + 1
            if post_vote_counts[pid] <= 3:
                if pid not in post_early_votes:
                    post_early_votes[pid] = []
                post_early_votes[pid].append(inter.vote)

        for post in sim.posts:
            pid = str(post.post_id)
            if post.label == PostLabel.AMBIGUOUS:
                continue
            feats = extract_post_features(
                content=post.content,
                early_votes=post_early_votes.get(pid),
                interaction_count=post_vote_counts.get(pid, 0),
                time_span_seconds=max(cfg.time_steps * 60, 1),
            )
            train_features.append(feats)
            train_labels.append(1 if post.label == PostLabel.TRUE else 0)
        cred_model.train(train_features, train_labels)

        for post in sim.posts:
            pid = str(post.post_id)
            feats = extract_post_features(
                content=post.content,
                early_votes=post_early_votes.get(pid),
                interaction_count=post_vote_counts.get(pid, 0),
                time_span_seconds=max(cfg.time_steps * 60, 1),
            )
            ml_cred_scores[pid] = cred_model.predict(feats)

        # Anomaly
        total_time = max(cfg.time_steps * 60.0, 1.0)
        user_feats_list = []
        for user in sim.users:
            uid = str(user.user_id)
            ext = ext_signals.get(uid, {}) if cfg.use_signals else {}
            feats = extract_user_behavior_features(
                interactions_count=len(user_interactions.get(uid, [])),
                total_time_seconds=total_time,
                action_counts=user_action_counts.get(uid, {"vote_up": 0, "vote_down": 0}),
                consensus_deviation=1.0 - r_star_scores.get(uid, 0.5),
                coordination_score=coord_scores.get(uid, 0.0),
                location_inconsistency=location_inconsistencies.get(uid, 0.0),
                votes=user_votes.get(uid, []),
                navigation_deviation=ext.get("navigation", 0.0),
                device_consistency=ext.get("device", 1.0),
                ip_consistency=ext.get("ip", 1.0),
                session_continuity=ext.get("session", 1.0),
                timing_irregularity=ext.get("timing", 1.0),
            )
            user_feats_list.append(feats)
        user_type_labels = [1 if u.user_type in (UserType.ADVERSARIAL, UserType.BOT) else 0 for u in sim.users]
        anom_model.train(user_feats_list, user_type_labels)
        for i, user in enumerate(sim.users):
            ml_anomaly_scores[str(user.user_id)] = anom_model.predict(user_feats_list[i])

    # Compute user states
    users_out = []
    user_weights = {}
    for user in sim.users:
        uid = str(user.user_id)
        state = compute_user_state(
            interactions=user_interactions.get(uid, []),
            action_counts=user_action_counts.get(uid, {"vote_up": 0, "vote_down": 0}),
            t_now=t_now,
            coordination_score=coord_scores.get(uid, 0.0) if cfg.use_graph else 0.0,
            location_inconsistency=location_inconsistencies.get(uid, 0.0) if cfg.use_spatial else 0.0,
            trust_override=graph_trust.get(uid) if cfg.use_graph else None,
            anom_ml=ml_anomaly_scores.get(uid, 0.0) if cfg.use_ml else 0.0,
        )
        user_weights[uid] = state.weight

        users_out.append({
            "id": uid[:8],
            "full_id": uid,
            "type": user.user_type.value,
            "reliability": round(state.r_star, 3),
            "experience": round(state.exp_score, 3),
            "anomaly": round(state.anomaly_score, 3),
            "trust": round(state.trust_score, 3),
            "weight": round(state.weight, 3),
            "location_confidence": round(location_confidences.get(uid, 0.5), 3),
            "coordination": round(coord_scores.get(uid, 0.0), 3),
            "signals": ext_signals.get(uid, {}),
            "lat": round(user.lat, 4),
            "lon": round(user.lon, 4),
        })

    # Compute post states
    post_interactions_map = {}
    for inter in interactions:
        pid = str(inter.post_id)
        uid = str(inter.user_id)
        if pid not in post_interactions_map:
            post_interactions_map[pid] = []
        post_interactions_map[pid].append(PostInteraction(
            user_weight=user_weights.get(uid, 0.0), vote=inter.vote, timestamp=inter.timestamp,
        ))

    posts_out = []
    for post in sim.posts:
        pid = str(post.post_id)
        c_ml = ml_cred_scores.get(pid) if cfg.use_ml else None
        post_state = compute_post_state(
            interactions=post_interactions_map.get(pid, []),
            t_now=t_now, c_ml=c_ml,
        )
        posts_out.append({
            "id": pid[:8],
            "full_id": pid,
            "content": post.content[:80],
            "label": post.label.name,
            "credibility": round(post_state.c_final, 3),
            "c_bayes": round(post_state.c_bayes, 3),
            "c_ml": round(c_ml, 3) if c_ml is not None else None,
            "variance": round(post_state.variance, 3),
            "n_effective": round(post_state.n_effective, 1),
            "lat": round(post.lat, 4),
            "lon": round(post.lon, 4),
        })

    # Metrics
    from simulation.evaluator import (
        compute_accuracy, compute_brier_score,
        compute_attack_success_rate, compute_weight_correlation,
        compute_anomaly_detection,
    )

    # Simpler approach for metrics
    cred_list = []
    truth_list = []
    f_creds = []
    for post in sim.posts:
        pid = str(post.post_id)
        if post.label == PostLabel.AMBIGUOUS:
            continue
        c = next((p["credibility"] for p in posts_out if p["full_id"] == pid), 0.5)
        cred_list.append(c)
        truth_list.append(post.label.value)
        if post.label == PostLabel.FALSE:
            f_creds.append(c)

    metrics = {
        "accuracy": round(compute_accuracy(cred_list, truth_list), 3),
        "brier_score": round(compute_brier_score(cred_list, truth_list), 3),
        "attack_success": round(compute_attack_success_rate(f_creds), 3),
        "weight_correlation": round(compute_weight_correlation(
            [u["weight"] for u in users_out],
            [u.p_correct for u in sim.users],
        ), 3),
    }

    return {
        "users": users_out,
        "posts": posts_out,
        "edges": graph_edges,
        "metrics": metrics,
        "config": {
            "scenario": cfg.name,
            "phase": 6 if cfg.use_signals else (5 if cfg.use_ml else (4 if cfg.use_spatial else (3 if cfg.use_graph else 1))),
            "num_users": len(sim.users),
            "num_posts": len(sim.posts),
        },
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
