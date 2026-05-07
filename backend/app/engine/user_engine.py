"""
User State Engine — Algorithm 1 from pseudo_algorithm.md

Computes:
  - R_i*(t)  : effective reliability (Formula 1)
  - Exp_i(t) : experience score (Formula 2)
  - Anom_i(t): anomaly score (Formula 3, rule-based only in MVP)
  - w_i(t)   : final user weight (Formula 5)

All formulas sourced from: docs/context/mathematical_formula.md
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone

from app.config import config


@dataclass
class UserStateSnapshot:
    """Immutable snapshot of computed user state values."""

    alpha: float
    beta: float
    r_score: float         # R_i
    confidence: float      # Conf_i
    r_star: float          # R_i*
    exp_raw: float         # E_i
    exp_score: float       # Exp_i
    anomaly_score: float   # Anom_i
    trust_score: float     # T_i (= R_i* in MVP)
    weight: float          # w_i


@dataclass
class InteractionRecord:
    """Minimal interaction data needed for user state computation."""

    timestamp: datetime
    is_correct: bool | None  # None if ground truth not yet available
    quality: float = 1.0     # q_k for experience


def _time_delta_seconds(t_now: datetime, t_event: datetime) -> float:
    """Compute time difference in seconds, always non-negative."""
    delta = (t_now - t_event).total_seconds()
    return max(delta, 0.0)


# ──────────────────────────────────────────────────────────
# Formula 1: User Reliability R_i*(t)
# ──────────────────────────────────────────────────────────

def compute_reliability(
    interactions: list[InteractionRecord],
    t_now: datetime,
) -> tuple[float, float, float, float, float]:
    """
    Compute time-decayed reliability using Formula 1.

    Returns:
        (alpha, beta, R_i, Conf_i, R_i*)
    """
    alpha = 0.0
    beta = 0.0

    for interaction in interactions:
        if interaction.is_correct is None:
            continue  # Ground truth not yet available — skip
        dt = _time_delta_seconds(t_now, interaction.timestamp)
        decay = math.exp(-config.lambda_r * dt)

        if interaction.is_correct:
            alpha += decay
        else:
            beta += decay

    total = alpha + beta + config.epsilon

    # R_i = α / (α + β)
    r_score = alpha / total if total > config.epsilon else config.reliability_prior

    # Conf_i = 1 - exp(-k * (α + β))
    confidence = 1.0 - math.exp(-config.confidence_k * (alpha + beta))

    # R_i* = R_i × Conf_i
    r_star = r_score * confidence

    return alpha, beta, r_score, confidence, r_star


# ──────────────────────────────────────────────────────────
# Formula 2: User Experience Exp_i(t)
# ──────────────────────────────────────────────────────────

def compute_experience(
    interactions: list[InteractionRecord],
    t_now: datetime,
) -> tuple[float, float]:
    """
    Compute experience score using Formula 2.

    Returns:
        (E_i raw, Exp_i normalized)
    """
    e_raw = 0.0

    for interaction in interactions:
        dt = _time_delta_seconds(t_now, interaction.timestamp)
        decay = math.exp(-config.lambda_e * dt)
        e_raw += decay * interaction.quality

    # Exp_i = log(1 + E_i) / log(1 + E_max)
    exp_score = math.log1p(e_raw) / math.log1p(config.e_max)

    # Clamp to [0, 1]
    exp_score = min(max(exp_score, 0.0), 1.0)

    return e_raw, exp_score


# ──────────────────────────────────────────────────────────
# Formula 3: User Anomaly (Rule-Based MVP)
# ──────────────────────────────────────────────────────────

@dataclass
class AnomalySignals:
    """Individual anomaly deviation components D_1..D_5."""

    burst_deviation: float = 0.0      # D_1: temporal burst
    entropy_deviation: float = 0.0    # D_2: behavioral entropy
    consensus_deviation: float = 0.0  # D_3: consensus deviation
    coordination_score: float = 0.0   # D_4: coordination similarity
    location_inconsistency: float = 0.0  # D_5: location inconsistency


def compute_burst_deviation(
    interactions: list[InteractionRecord],
    t_now: datetime,
) -> float:
    """
    D_1: Temporal burst deviation.
    Compares recent activity count vs long-term baseline.

    Formula: D_1 = V_window / (μ_baseline + ε)
    Bounded: 1 - exp(-D_1)
    """
    window = config.burst_window  # seconds
    recent_count = 0
    total_decayed = 0.0

    for interaction in interactions:
        dt = _time_delta_seconds(t_now, interaction.timestamp)
        if dt <= window:
            recent_count += 1
        total_decayed += math.exp(-config.lambda_r * dt)

    # Baseline: average rate over decayed history
    baseline = total_decayed / max(len(interactions), 1)

    ratio = recent_count / (baseline + config.burst_epsilon)

    # Bounded form
    return 1.0 - math.exp(-ratio)


def compute_entropy_deviation(
    action_counts: dict[str, int],
) -> float:
    """
    D_2: Behavioral entropy deviation.
    Low entropy = repetitive = suspicious.

    Formula: D_2 = 1 - H_i / log(|A|)
    """
    total = sum(action_counts.values())
    if total == 0:
        return 0.0

    num_actions = len(action_counts)
    if num_actions <= 1:
        return 1.0  # Only one action type — maximally suspicious

    entropy = 0.0
    for count in action_counts.values():
        if count > 0:
            p = count / total
            entropy -= p * math.log(p)

    max_entropy = math.log(num_actions)
    if max_entropy < config.epsilon:
        return 0.0

    normalized = entropy / max_entropy
    return 1.0 - normalized  # Low entropy → high deviation


def compute_consensus_deviation(
    interactions: list[InteractionRecord],
) -> float:
    """
    D_3: Consensus deviation.
    How often user disagrees with ground truth.

    Formula: D_3 = 1 - (correct_count / total_count)
    """
    total = 0
    correct = 0

    for interaction in interactions:
        if interaction.is_correct is not None:
            total += 1
            if interaction.is_correct:
                correct += 1

    if total == 0:
        return 0.0

    return 1.0 - (correct / total)


def compute_anomaly(
    signals: AnomalySignals,
    anom_ml: float = 0.0,
) -> float:
    """
    Final anomaly score (rule-based + ML blend).
    Formula 3: Anom_rule = 1 - exp(- Σ α_m × D_m)
    Phase 5:   Anom_i = (1 - β) × Anom_rule + β × Anom_ML
    """
    weights = config.anomaly_alpha_weights
    deviations = [
        signals.burst_deviation,
        signals.entropy_deviation,
        signals.consensus_deviation,
        signals.coordination_score,
        signals.location_inconsistency,
    ]

    weighted_sum = sum(w * d for w, d in zip(weights, deviations))
    anom_rule = 1.0 - math.exp(-weighted_sum)

    # Phase 5: blend rule-based with ML anomaly
    anom_final = (1.0 - config.anomaly_beta) * anom_rule + config.anomaly_beta * anom_ml

    return min(max(anom_final, 0.0), 1.0)


# ──────────────────────────────────────────────────────────
# Formula 5: Final User Weight w_i(t)
# ──────────────────────────────────────────────────────────

def compute_user_weight(
    trust: float,
    anomaly: float,
    experience: float,
) -> float:
    """
    w_i(t) = T_i × (1 - Anom_i) × Exp_i

    Multiplicative gating: all three must be non-zero for influence.
    """
    weight = trust * (1.0 - anomaly) * experience
    return min(max(weight, 0.0), 1.0)


# ──────────────────────────────────────────────────────────
# Full user state update (Algorithm 1)
# ──────────────────────────────────────────────────────────

def compute_user_state(
    interactions: list[InteractionRecord],
    action_counts: dict[str, int],
    t_now: datetime | None = None,
    coordination_score: float = 0.0,
    location_inconsistency: float = 0.0,
    trust_override: float | None = None,
    anom_ml: float = 0.0,
) -> UserStateSnapshot:
    """
    Full user state computation (Algorithm 1 from pseudo_algorithm.md).

    Args:
        interactions: All interactions by this user.
        action_counts: Distribution of action types {"vote_up": 10, "vote_down": 3, ...}.
        t_now: Current time (defaults to now).
        coordination_score: D_4 from graph module (0.0 in MVP, computed in Phase 3).
        location_inconsistency: D_5 from spatial module (0.0 in MVP).
        trust_override: T_i from graph trust propagation (Phase 3).
            If None, falls back to R_i* (Phase 1 behavior).
        anom_ml: ML anomaly score from Phase 5 AnomalyMLModel (0.0 if unavailable).

    Returns:
        UserStateSnapshot with all computed values.
    """
    if t_now is None:
        t_now = datetime.now(timezone.utc)

    # Step 1–4: Reliability
    alpha, beta, r_score, confidence, r_star = compute_reliability(interactions, t_now)

    # Step 5–6: Experience
    exp_raw, exp_score = compute_experience(interactions, t_now)

    # Step 7–9: Anomaly
    signals = AnomalySignals(
        burst_deviation=compute_burst_deviation(interactions, t_now),
        entropy_deviation=compute_entropy_deviation(action_counts),
        consensus_deviation=compute_consensus_deviation(interactions),
        coordination_score=coordination_score,
        location_inconsistency=location_inconsistency,
    )
    anomaly_score = compute_anomaly(signals, anom_ml=anom_ml)

    # Phase 3: Use graph-propagated trust if available, else fall back to R_i*
    trust_score = trust_override if trust_override is not None else r_star

    # Formula 5: Final weight
    weight = compute_user_weight(trust_score, anomaly_score, exp_score)

    return UserStateSnapshot(
        alpha=alpha,
        beta=beta,
        r_score=r_score,
        confidence=confidence,
        r_star=r_star,
        exp_raw=exp_raw,
        exp_score=exp_score,
        anomaly_score=anomaly_score,
        trust_score=trust_score,
        weight=weight,
    )

