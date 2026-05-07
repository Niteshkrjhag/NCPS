"""
Experiment Runner — Phase 6 (Final).

Full pipeline: MVP + Graph + Spatial + ML + Extended Signals + Frontend.

Pipeline:
  1. Generate synthetic data + location histories + device/IP metadata
  2. Train ML models on simulation data
  3. Compute R_i*, graph trust, spatial signals
  4. Compute extended signals (S_nav, S_device, S_ip, S_session, S_timing)
  5. Predict Anom_ML (11 features), C_ML, C_memory
  6. Compute user states with all signals blended
  7. Compute post credibility with C_ML + C_memory
  8. Evaluate + compare all phases
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from dataclasses import dataclass

from simulation.simulator import (
    Simulator, SimulatedUser, SimulatedPost,
    SimulatedInteraction, UserType, PostLabel,
)
from simulation.evaluator import (
    EvaluationMetrics, compute_accuracy, compute_brier_score,
    compute_attack_success_rate, compute_weight_correlation,
    compute_anomaly_detection,
)
from app.engine.user_engine import (
    InteractionRecord, compute_user_state, compute_reliability,
)
from app.engine.post_engine import PostInteraction, compute_post_state
from app.engine.urgency import compute_urgency
from app.engine.graph_engine import VoteRecord, run_graph_pipeline
from app.engine.spatial import (
    LocationRecord, compute_location_confidence,
    compute_location_inconsistency, compute_proximity,
    compute_spatial_trust, estimate_post_location,
)
from app.engine.decision import AlertInput, decide_alert
from app.engine.ml_engine import (
    CredibilityMLModel, MemoryEngine, AnomalyMLModel,
    MemoryEntry, PostFeatures, UserBehaviorFeatures,
    extract_post_features, extract_user_behavior_features,
)
from app.engine.signal_engine import compute_all_extended_signals


@dataclass
class ExperimentConfig:
    """Configuration for a simulation experiment."""
    name: str = "baseline"
    num_honest: int = 50
    num_noisy: int = 10
    num_adversarial: int = 5
    num_bots: int = 10
    bot_groups: int = 2
    num_true_posts: int = 30
    num_false_posts: int = 20
    time_steps: int = 100
    interactions_per_step: int = 10
    seed: int = 42
    use_graph: bool = True
    use_spatial: bool = False
    use_ml: bool = False
    use_signals: bool = False  # Phase 6: extended signals


def run_experiment(cfg: ExperimentConfig) -> EvaluationMetrics:
    """Run a complete simulation experiment with all phases."""
    phase_tag = []
    if cfg.use_graph: phase_tag.append("Graph")
    if cfg.use_spatial: phase_tag.append("Spatial")
    if cfg.use_ml: phase_tag.append("ML")
    if cfg.use_signals: phase_tag.append("Signals")

    print(f"\n{'='*60}")
    print(f"Running: {cfg.name}")
    print(f"  Active: {' + '.join(phase_tag) if phase_tag else 'Base only'}")
    print(f"{'='*60}")

    # ── Step 1: Generate synthetic data ──
    sim = Simulator(
        num_honest=cfg.num_honest, num_noisy=cfg.num_noisy,
        num_adversarial=cfg.num_adversarial, num_bots=cfg.num_bots,
        bot_groups=cfg.bot_groups, num_true_posts=cfg.num_true_posts,
        num_false_posts=cfg.num_false_posts, seed=cfg.seed,
    )
    interactions = sim.generate_interactions(
        time_steps=cfg.time_steps,
        interactions_per_step=cfg.interactions_per_step,
    )
    print(f"  Users: {len(sim.users)} | Posts: {len(sim.posts)} | Interactions: {len(interactions)}")

    # ── Step 2: Spatial ──
    t_now = datetime.now(timezone.utc)
    location_confidences: dict[str, float] = {}
    location_inconsistencies: dict[str, float] = {}

    if cfg.use_spatial:
        raw_histories = sim.generate_location_history(time_steps=cfg.time_steps)
        location_histories: dict[str, list[LocationRecord]] = {}
        for uid, readings in raw_histories.items():
            location_histories[uid] = [
                LocationRecord(lat=r["lat"], lon=r["lon"], timestamp=r["timestamp"],
                               accuracy_meters=r["accuracy"], source=r["source"])
                for r in readings
            ]
        for user in sim.users:
            uid = str(user.user_id)
            hist = location_histories.get(uid, [])
            location_confidences[uid] = compute_location_confidence(hist)
            location_inconsistencies[uid] = compute_location_inconsistency(hist)

    # ── Step 3: Build interaction maps ──
    user_interactions: dict[str, list[InteractionRecord]] = {}
    user_action_counts: dict[str, dict[str, int]] = {}
    user_votes: dict[str, list[int]] = {}

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

    # ── Step 3a: R_i* ──
    r_star_scores: dict[str, float] = {}
    for user in sim.users:
        uid = str(user.user_id)
        _, _, _, _, r_star = compute_reliability(user_interactions.get(uid, []), t_now)
        r_star_scores[uid] = r_star

    # ── Step 3b: Graph pipeline ──
    graph_trust: dict[str, float] = {}
    coord_scores: dict[str, float] = {}
    if cfg.use_graph:
        vote_records = [
            VoteRecord(user_id=str(i.user_id), post_id=str(i.post_id),
                       vote=i.vote, timestamp=i.timestamp)
            for i in interactions
        ]
        graph_state = run_graph_pipeline(vote_records, r_star_scores)
        graph_trust = graph_state.trust_scores
        coord_scores = graph_state.coordination_scores

    # ── Step 4: Phase 6 — Extended signals ──
    extended_signals: dict[str, dict] = {}
    if cfg.use_signals:
        user_metadata = sim.generate_user_metadata(interactions)

        # Also generate location tuples for navigation deviation
        loc_tuples: dict[str, list[tuple]] = {}
        if cfg.use_spatial:
            for uid, hist in location_histories.items():
                loc_tuples[uid] = [(r.lat, r.lon, r.timestamp.timestamp()) for r in hist]

        for user in sim.users:
            uid = str(user.user_id)
            meta = user_metadata.get(uid, {})
            locs = loc_tuples.get(uid, [])

            signals = compute_all_extended_signals(
                locations=locs if locs else None,
                device_ids=meta.get("device_ids"),
                ip_addresses=meta.get("ip_addresses"),
                ip_locations=meta.get("ip_locations"),
                timestamps=meta.get("timestamps"),
            )
            extended_signals[uid] = {
                "nav": signals.navigation_deviation,
                "device": signals.device_consistency,
                "ip": signals.ip_consistency,
                "session": signals.session_continuity,
                "timing": signals.timing_irregularity,
            }

        # Print Phase 6 stats
        low_device = sum(1 for s in extended_signals.values() if s["device"] < 0.5)
        low_ip = sum(1 for s in extended_signals.values() if s["ip"] < 0.5)
        print(f"  Signals: {low_device} low-device, {low_ip} low-IP users")

    # ── Step 5: ML models ──
    cred_model = CredibilityMLModel()
    memory_engine = MemoryEngine()
    anom_model = AnomalyMLModel()
    ml_anomaly_scores: dict[str, float] = {}
    ml_cred_scores: dict[str, float] = {}
    ml_memory_scores: dict[str, float | None] = {}

    if cfg.use_ml:
        post_lookup = {str(p.post_id): p for p in sim.posts}
        post_early_votes: dict[str, list[int]] = {}
        post_vote_counts: dict[str, int] = {}
        for inter in interactions:
            pid = str(inter.post_id)
            post_vote_counts[pid] = post_vote_counts.get(pid, 0) + 1
            if post_vote_counts[pid] <= 3:
                if pid not in post_early_votes:
                    post_early_votes[pid] = []
                post_early_votes[pid].append(inter.vote)

        # Train C_ML
        train_features, train_labels = [], []
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
                content=post.content, early_votes=post_early_votes.get(pid),
                interaction_count=post_vote_counts.get(pid, 0),
                time_span_seconds=max(cfg.time_steps * 60, 1),
            )
            ml_cred_scores[pid] = cred_model.predict(feats)

        # Memory
        memory_entries = []
        for post in sim.posts:
            if post.label != PostLabel.AMBIGUOUS:
                known_cred = 0.9 if post.label == PostLabel.TRUE else 0.1
                memory_entries.append(MemoryEntry(
                    post_id=str(post.post_id), content=post.content, credibility=known_cred,
                ))
        memory_engine.build_memory(memory_entries)
        for post in sim.posts:
            ml_memory_scores[str(post.post_id)] = memory_engine.query(post.content)

        # Train Anom_ML (with Phase 6 extended features if available)
        user_features_list, user_labels = [], []
        total_time = max(cfg.time_steps * 60.0, 1.0)
        for user in sim.users:
            uid = str(user.user_id)
            ext = extended_signals.get(uid, {}) if cfg.use_signals else {}
            feats = extract_user_behavior_features(
                interactions_count=len(user_interactions.get(uid, [])),
                total_time_seconds=total_time,
                action_counts=user_action_counts.get(uid, {"vote_up": 0, "vote_down": 0}),
                consensus_deviation=1.0 - r_star_scores.get(uid, 0.5),
                coordination_score=coord_scores.get(uid, 0.0),
                location_inconsistency=location_inconsistencies.get(uid, 0.0),
                votes=user_votes.get(uid, []),
                navigation_deviation=ext.get("nav", 0.0),
                device_consistency=ext.get("device", 1.0),
                ip_consistency=ext.get("ip", 1.0),
                session_continuity=ext.get("session", 1.0),
                timing_irregularity=ext.get("timing", 1.0),
            )
            user_features_list.append(feats)
            user_labels.append(1 if user.user_type in (UserType.ADVERSARIAL, UserType.BOT) else 0)

        anom_model.train(user_features_list, user_labels)
        for i, user in enumerate(sim.users):
            ml_anomaly_scores[str(user.user_id)] = anom_model.predict(user_features_list[i])

    # ── Step 6: Compute user states ──
    user_weights: dict[str, float] = {}
    user_states = {}
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
        user_states[uid] = state

    # ── Step 7: Post states ──
    post_interactions_map: dict[str, list[PostInteraction]] = {}
    for inter in interactions:
        pid = str(inter.post_id)
        uid = str(inter.user_id)
        if pid not in post_interactions_map:
            post_interactions_map[pid] = []
        post_interactions_map[pid].append(PostInteraction(
            user_weight=user_weights.get(uid, 0.0), vote=inter.vote, timestamp=inter.timestamp,
        ))

    post_credibilities: dict[str, float] = {}
    for post in sim.posts:
        pid = str(post.post_id)
        c_ml = ml_cred_scores.get(pid) if cfg.use_ml else None
        c_mem = ml_memory_scores.get(pid) if cfg.use_ml else None
        post_state = compute_post_state(
            interactions=post_interactions_map.get(pid, []),
            t_now=t_now, c_ml=c_ml, c_memory=c_mem,
        )
        post_credibilities[pid] = post_state.c_final

    # ── Step 8: Evaluate ──
    all_creds, all_truths, false_creds = [], [], []
    for post in sim.posts:
        pid = str(post.post_id)
        if pid in post_credibilities and post.label != PostLabel.AMBIGUOUS:
            all_creds.append(post_credibilities[pid])
            all_truths.append(post.label.value)
            if post.label == PostLabel.FALSE:
                false_creds.append(post_credibilities[pid])

    accuracy = compute_accuracy(all_creds, all_truths)
    brier = compute_brier_score(all_creds, all_truths)
    attack_rate = compute_attack_success_rate(false_creds)
    estimated_ws = [user_weights.get(str(u.user_id), 0) for u in sim.users]
    true_rs = [u.p_correct for u in sim.users]
    weight_corr = compute_weight_correlation(estimated_ws, true_rs)

    pred_anoms = [user_states[str(u.user_id)].anomaly_score > 0.3
                  for u in sim.users if str(u.user_id) in user_states]
    actual_anoms = [u.user_type in (UserType.ADVERSARIAL, UserType.BOT)
                    for u in sim.users if str(u.user_id) in user_states]
    anom_p, anom_r = compute_anomaly_detection(pred_anoms, actual_anoms)

    metrics = EvaluationMetrics(
        accuracy=accuracy, brier_score=brier,
        attack_success_rate=attack_rate, weight_correlation=weight_corr,
        anomaly_precision=anom_p, anomaly_recall=anom_r,
        total_posts=len(sim.posts),
        true_posts=cfg.num_true_posts, false_posts=cfg.num_false_posts,
    )

    print(f"  Results: Acc={metrics.accuracy:.3f} | Attack={metrics.attack_success_rate:.3f} "
          f"| Brier={metrics.brier_score:.3f} | WCorr={metrics.weight_correlation:.3f} "
          f"| Anom-P={metrics.anomaly_precision:.3f} | Anom-R={metrics.anomaly_recall:.3f}")
    return metrics


def run_all_experiments() -> dict[str, EvaluationMetrics]:
    """Run all experiments: Phase 1 → 3 → 4 → 5 → 6."""
    results = {}
    attack_cfg = dict(num_honest=40, num_noisy=5, num_adversarial=5,
                      num_bots=20, bot_groups=4)

    results["P1_attack"] = run_experiment(ExperimentConfig(
        name="Phase 1: Attack (Base)", **attack_cfg,
        use_graph=False, use_spatial=False, use_ml=False, use_signals=False,
    ))
    results["P3_attack"] = run_experiment(ExperimentConfig(
        name="Phase 3: Attack (Graph)", **attack_cfg,
        use_graph=True, use_spatial=False, use_ml=False, use_signals=False,
    ))
    results["P4_attack"] = run_experiment(ExperimentConfig(
        name="Phase 4: Attack (Graph+Spatial)", **attack_cfg,
        use_graph=True, use_spatial=True, use_ml=False, use_signals=False,
    ))
    results["P5_attack"] = run_experiment(ExperimentConfig(
        name="Phase 5: Attack (Graph+Spatial+ML)", **attack_cfg,
        use_graph=True, use_spatial=True, use_ml=True, use_signals=False,
    ))
    results["P6_attack"] = run_experiment(ExperimentConfig(
        name="Phase 6: Attack (Full Pipeline)", **attack_cfg,
        use_graph=True, use_spatial=True, use_ml=True, use_signals=True,
    ))
    results["P6_baseline"] = run_experiment(ExperimentConfig(
        name="Phase 6: Baseline (Honest Only)",
        num_honest=70, num_noisy=0, num_adversarial=0, num_bots=0,
        use_graph=True, use_spatial=True, use_ml=True, use_signals=True,
    ))

    # ═══ Summary ═══
    print(f"\n{'='*95}")
    print("FULL PIPELINE EVOLUTION — Phase 1 → Phase 3 → Phase 4 → Phase 5 → Phase 6")
    print(f"{'='*95}")

    keys = ["P1_attack", "P3_attack", "P4_attack", "P5_attack", "P6_attack"]
    labels = ["Phase 1", "Phase 3", "Phase 4", "Phase 5", "Phase 6"]
    if all(k in results for k in keys):
        phases = [results[k] for k in keys]
        print(f"  {'Metric':<25} " + "".join(f"{l:>10}" for l in labels))
        print(f"  {'-'*75}")
        for mname, getter in [
            ("Accuracy", lambda m: m.accuracy),
            ("Attack Success ↓", lambda m: m.attack_success_rate),
            ("Brier Score ↓", lambda m: m.brier_score),
            ("Weight Correlation", lambda m: m.weight_correlation),
            ("Anomaly Precision", lambda m: m.anomaly_precision),
            ("Anomaly Recall", lambda m: m.anomaly_recall),
        ]:
            vals = "".join(f"{getter(p):>10.3f}" for p in phases)
            print(f"  {mname:<25} {vals}")

        p1, p6 = phases[0], phases[4]
        print(f"\n  Phase 1 → Phase 6 Total Improvement:")
        print(f"    Accuracy:        {p1.accuracy:.3f} → {p6.accuracy:.3f}")
        print(f"    Attack Success:  {p1.attack_success_rate:.3f} → {p6.attack_success_rate:.3f}")
        print(f"    Anomaly Recall:  {p1.anomaly_recall:.3f} → {p6.anomaly_recall:.3f}")

    return results


if __name__ == "__main__":
    run_all_experiments()
