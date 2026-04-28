"""
Experiment Runner — Phase 3 Upgraded.

Runs simulation end-to-end with graph trust propagation and evaluates results.

Source: simulation_evaluation_framework.md §11
        phase3_system_design.md §9

Pipeline:
  1. Generate synthetic users/posts/interactions
  2. Compute initial user states (R_i*, Exp_i, Anom_i)
  3. Run graph pipeline → T_i, S_coord
  4. Recompute user states with graph trust + coordination
  5. Compute post credibility with updated weights
  6. Evaluate metrics
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from dataclasses import dataclass

from simulation.simulator import (
    Simulator,
    SimulatedUser,
    SimulatedPost,
    SimulatedInteraction,
    UserType,
    PostLabel,
)
from simulation.evaluator import (
    EvaluationMetrics,
    compute_accuracy,
    compute_brier_score,
    compute_attack_success_rate,
    compute_weight_correlation,
    compute_anomaly_detection,
)
from app.engine.user_engine import (
    InteractionRecord,
    compute_user_state,
    compute_reliability,
)
from app.engine.post_engine import (
    PostInteraction,
    compute_post_state,
)
from app.engine.urgency import compute_urgency
from app.engine.graph_engine import (
    VoteRecord,
    run_graph_pipeline,
)


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
    use_graph: bool = True  # Phase 3: enable graph trust propagation


def run_experiment(cfg: ExperimentConfig) -> EvaluationMetrics:
    """
    Run a complete simulation experiment.

    Phase 3 pipeline (phase3_system_design.md §9):
      1. Generate data
      2. Compute initial R_i* for all users
      3. Run graph pipeline → T_i, S_coord
      4. Recompute user states with T_i and S_coord
      5. Compute post credibility
      6. Evaluate
    """
    print(f"\n{'='*60}")
    print(f"Running experiment: {cfg.name}")
    print(f"  Graph engine: {'ON' if cfg.use_graph else 'OFF'}")
    print(f"{'='*60}")

    # ── Step 1: Generate synthetic data ──
    sim = Simulator(
        num_honest=cfg.num_honest,
        num_noisy=cfg.num_noisy,
        num_adversarial=cfg.num_adversarial,
        num_bots=cfg.num_bots,
        bot_groups=cfg.bot_groups,
        num_true_posts=cfg.num_true_posts,
        num_false_posts=cfg.num_false_posts,
        seed=cfg.seed,
    )

    print(f"  Users: {len(sim.users)} "
          f"(honest={cfg.num_honest}, noisy={cfg.num_noisy}, "
          f"adversarial={cfg.num_adversarial}, bots={cfg.num_bots})")
    print(f"  Posts: {len(sim.posts)} "
          f"(true={cfg.num_true_posts}, false={cfg.num_false_posts})")

    # ── Step 2: Generate interactions ──
    interactions = sim.generate_interactions(
        time_steps=cfg.time_steps,
        interactions_per_step=cfg.interactions_per_step,
    )
    print(f"  Interactions: {len(interactions)}")

    # ── Step 3: Process through engine ──
    t_now = datetime.now(timezone.utc)

    # Build user interaction maps
    user_interactions: dict[str, list[InteractionRecord]] = {}
    user_action_counts: dict[str, dict[str, int]] = {}

    for inter in interactions:
        uid = str(inter.user_id)
        if uid not in user_interactions:
            user_interactions[uid] = []
            user_action_counts[uid] = {"vote_up": 0, "vote_down": 0}

        user_interactions[uid].append(InteractionRecord(
            timestamp=inter.timestamp,
            is_correct=inter.is_correct,
            quality=1.0,
        ))

        if inter.vote == 1:
            user_action_counts[uid]["vote_up"] += 1
        else:
            user_action_counts[uid]["vote_down"] += 1

    # ── Step 3a: Compute initial R_i* (needed as input for graph) ──
    r_star_scores: dict[str, float] = {}
    for user in sim.users:
        uid = str(user.user_id)
        ints = user_interactions.get(uid, [])
        _, _, _, _, r_star = compute_reliability(ints, t_now)
        r_star_scores[uid] = r_star

    # ── Step 3b: Graph pipeline (Phase 3) ──
    graph_trust: dict[str, float] = {}
    coord_scores: dict[str, float] = {}

    if cfg.use_graph:
        # Convert interactions to VoteRecords for graph engine
        vote_records = [
            VoteRecord(
                user_id=str(inter.user_id),
                post_id=str(inter.post_id),
                vote=inter.vote,
                timestamp=inter.timestamp,
            )
            for inter in interactions
        ]

        graph_state = run_graph_pipeline(vote_records, r_star_scores)
        graph_trust = graph_state.trust_scores
        coord_scores = graph_state.coordination_scores

        print(f"  Graph: {len(graph_state.edges)} nodes with edges, "
              f"converged in {graph_state.iterations_converged} iterations")

        # Print coordination stats
        high_coord = sum(1 for s in coord_scores.values() if s > 0.5)
        print(f"  Coordination: {high_coord} users with S_coord > 0.5")

    # ── Step 3c: Compute user states with graph trust + coordination ──
    user_weights: dict[str, float] = {}
    user_states = {}

    for user in sim.users:
        uid = str(user.user_id)
        ints = user_interactions.get(uid, [])
        acts = user_action_counts.get(uid, {"vote_up": 0, "vote_down": 0})

        # Phase 3: pass graph-propagated trust and coordination score
        trust_override = graph_trust.get(uid) if cfg.use_graph else None
        coordination = coord_scores.get(uid, 0.0) if cfg.use_graph else 0.0

        state = compute_user_state(
            interactions=ints,
            action_counts=acts,
            t_now=t_now,
            coordination_score=coordination,
            trust_override=trust_override,
        )

        user_weights[uid] = state.weight
        user_states[uid] = state

    # ── Step 4: Compute post states with updated weights ──
    post_interactions_map: dict[str, list[PostInteraction]] = {}
    post_content: dict[str, str] = {}

    for post in sim.posts:
        post_content[str(post.post_id)] = post.content

    for inter in interactions:
        pid = str(inter.post_id)
        uid = str(inter.user_id)
        if pid not in post_interactions_map:
            post_interactions_map[pid] = []

        w = user_weights.get(uid, 0.0)
        post_interactions_map[pid].append(PostInteraction(
            user_weight=w,
            vote=inter.vote,
            timestamp=inter.timestamp,
        ))

    # Compute post states
    post_credibilities: dict[str, float] = {}
    for post in sim.posts:
        pid = str(post.post_id)
        ints = post_interactions_map.get(pid, [])

        post_state = compute_post_state(
            interactions=ints,
            t_now=t_now,
        )
        post_credibilities[pid] = post_state.c_final

    # ── Step 5: Evaluate ──
    all_creds = []
    all_truths = []
    false_post_creds = []

    for post in sim.posts:
        pid = str(post.post_id)
        if pid in post_credibilities and post.label != PostLabel.AMBIGUOUS:
            all_creds.append(post_credibilities[pid])
            all_truths.append(post.label.value)

            if post.label == PostLabel.FALSE:
                false_post_creds.append(post_credibilities[pid])

    accuracy = compute_accuracy(all_creds, all_truths)
    brier = compute_brier_score(all_creds, all_truths)
    attack_rate = compute_attack_success_rate(false_post_creds)

    # Weight quality
    estimated_ws = []
    true_rs = []
    for user in sim.users:
        uid = str(user.user_id)
        if uid in user_weights:
            estimated_ws.append(user_weights[uid])
            true_rs.append(user.p_correct)

    weight_corr = compute_weight_correlation(estimated_ws, true_rs)

    # Anomaly detection
    anomaly_threshold = 0.3
    predicted_anoms = []
    actual_anoms = []
    for user in sim.users:
        uid = str(user.user_id)
        if uid in user_states:
            predicted_anoms.append(user_states[uid].anomaly_score > anomaly_threshold)
            actual_anoms.append(user.user_type in (UserType.ADVERSARIAL, UserType.BOT))

    anom_precision, anom_recall = compute_anomaly_detection(predicted_anoms, actual_anoms)

    metrics = EvaluationMetrics(
        accuracy=accuracy,
        brier_score=brier,
        attack_success_rate=attack_rate,
        weight_correlation=weight_corr,
        anomaly_precision=anom_precision,
        anomaly_recall=anom_recall,
        total_posts=len(sim.posts),
        true_posts=cfg.num_true_posts,
        false_posts=cfg.num_false_posts,
    )

    # Print results
    print(f"\n  Results:")
    print(f"    Accuracy:           {metrics.accuracy:.3f}")
    print(f"    Brier Score:        {metrics.brier_score:.3f}")
    print(f"    Attack Success:     {metrics.attack_success_rate:.3f}")
    print(f"    Weight Correlation: {metrics.weight_correlation:.3f}")
    print(f"    Anomaly Precision:  {metrics.anomaly_precision:.3f}")
    print(f"    Anomaly Recall:     {metrics.anomaly_recall:.3f}")

    return metrics


def run_all_experiments() -> dict[str, EvaluationMetrics]:
    """
    Run all experiments from simulation_evaluation_framework.md §7,
    with Phase 3 graph engine enabled.
    """
    results = {}

    # ════════════════════════════════════════════════════════
    # Phase 3 experiments (graph ON)
    # ════════════════════════════════════════════════════════

    # Experiment 1: Baseline (honest users only)
    results["baseline"] = run_experiment(ExperimentConfig(
        name="Exp 1: Baseline (Honest Only)",
        num_honest=70,
        num_noisy=0,
        num_adversarial=0,
        num_bots=0,
        num_true_posts=30,
        num_false_posts=20,
        use_graph=True,
    ))

    # Experiment 2: Random Noise
    results["noisy"] = run_experiment(ExperimentConfig(
        name="Exp 2: Random Noise",
        num_honest=50,
        num_noisy=20,
        num_adversarial=0,
        num_bots=0,
        num_true_posts=30,
        num_false_posts=20,
        use_graph=True,
    ))

    # Experiment 3: Coordinated Attack (KEY test for Phase 3)
    results["attack"] = run_experiment(ExperimentConfig(
        name="Exp 3: Coordinated Attack (Graph ON)",
        num_honest=40,
        num_noisy=5,
        num_adversarial=5,
        num_bots=20,
        bot_groups=4,
        num_true_posts=30,
        num_false_posts=20,
        use_graph=True,
    ))

    # Experiment 3b: Same attack WITHOUT graph (Phase 1 baseline for comparison)
    results["attack_no_graph"] = run_experiment(ExperimentConfig(
        name="Exp 3b: Coordinated Attack (Graph OFF)",
        num_honest=40,
        num_noisy=5,
        num_adversarial=5,
        num_bots=20,
        bot_groups=4,
        num_true_posts=30,
        num_false_posts=20,
        use_graph=False,
    ))

    # ════════════════════════════════════════════════════════
    # Summary
    # ════════════════════════════════════════════════════════
    print(f"\n{'='*70}")
    print("EXPERIMENT SUMMARY — Phase 3 (Graph Trust)")
    print(f"{'='*70}")
    print(f"{'Experiment':<35} {'Accuracy':>10} {'Attack':>10} {'Brier':>10} {'Anom-P':>8} {'Anom-R':>8}")
    print(f"{'-'*70}")
    for name, m in results.items():
        print(f"{name:<35} {m.accuracy:>10.3f} {m.attack_success_rate:>10.3f} "
              f"{m.brier_score:>10.3f} {m.anomaly_precision:>8.3f} {m.anomaly_recall:>8.3f}")

    # Phase 3 comparison
    if "attack" in results and "attack_no_graph" in results:
        a_on = results["attack"]
        a_off = results["attack_no_graph"]
        print(f"\n  Phase 3 Impact (Coordinated Attack):")
        print(f"    Attack Success:  {a_off.attack_success_rate:.3f} → {a_on.attack_success_rate:.3f} "
              f"({'↓ IMPROVED' if a_on.attack_success_rate < a_off.attack_success_rate else '→ same'})")
        print(f"    Accuracy:        {a_off.accuracy:.3f} → {a_on.accuracy:.3f}")
        print(f"    Anomaly Prec:    {a_off.anomaly_precision:.3f} → {a_on.anomaly_precision:.3f}")
        print(f"    Anomaly Recall:  {a_off.anomaly_recall:.3f} → {a_on.anomaly_recall:.3f}")

    return results


if __name__ == "__main__":
    run_all_experiments()
