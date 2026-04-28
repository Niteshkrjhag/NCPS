"""
Post State Engine — Algorithm 3 from pseudo_algorithm.md

Computes:
  - N_j(t)     : effective interaction mass (Formula 6)
  - S_j⁺, S_j⁻ : positive/negative signal mass (Formula 7)
  - C_Bayes    : Bayesian credibility (Formula 8)
  - Var_j(t)   : credibility variance (Formula 9)

All formulas sourced from: docs/context/mathematical_formula.md
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone

from app.config import config


@dataclass
class PostInteraction:
    """Minimal interaction data needed for post computation."""

    user_weight: float       # w_i(t_k) at time of interaction
    vote: int                # +1 or -1
    timestamp: datetime      # t_k


@dataclass
class PostStateSnapshot:
    """Immutable snapshot of computed post state values."""

    n_effective: float   # N_j(t) — effective interaction mass
    s_plus: float        # S_j⁺ — positive signal mass
    s_minus: float       # S_j⁻ — negative signal mass
    s_net: float         # S_j = S⁺ - S⁻
    c_bayes: float       # C_Bayes ∈ [0,1]
    c_final: float       # C_final ∈ [0,1] (= C_Bayes in MVP)
    variance: float      # Var_j ≥ 0


def _time_delta_seconds(t_now: datetime, t_event: datetime) -> float:
    """Compute time difference in seconds, always non-negative."""
    delta = (t_now - t_event).total_seconds()
    return max(delta, 0.0)


# ──────────────────────────────────────────────────────────
# Formulas 6, 7, 8, 9: Full post state computation
# ──────────────────────────────────────────────────────────

def compute_post_state(
    interactions: list[PostInteraction],
    t_now: datetime | None = None,
    c_ml: float | None = None,
    c_memory: float | None = None,
) -> PostStateSnapshot:
    """
    Full post state computation (Algorithm 3 from pseudo_algorithm.md).

    Args:
        interactions: All interactions for this post.
        t_now: Current time (defaults to now).
        c_ml: ML credibility score (Phase 5, None in MVP).
        c_memory: Memory-based credibility (Phase 5, None in MVP).

    Returns:
        PostStateSnapshot with all computed values.
    """
    if t_now is None:
        t_now = datetime.now(timezone.utc)

    # ── Step 1-4: Accumulate signals ──
    s_plus = 0.0
    s_minus = 0.0
    n_eff = 0.0

    for interaction in interactions:
        dt = _time_delta_seconds(t_now, interaction.timestamp)
        decay = math.exp(-config.lambda_interaction * dt)
        contribution = interaction.user_weight * decay

        if interaction.vote == 1:
            s_plus += contribution
        else:
            s_minus += contribution

        n_eff += contribution

    # ── Step 5: Net signal ──
    s_net = s_plus - s_minus

    # ── Step 6: Bayesian Credibility (Formula 8) ──
    # C_Bayes = (S⁺ + α₀) / (S⁺ + S⁻ + α₀ + β₀)
    alpha0 = config.credibility_alpha0
    beta0 = config.credibility_beta0
    denominator = s_plus + s_minus + alpha0 + beta0

    c_bayes = (s_plus + alpha0) / denominator

    # ── Step 7: Final Credibility (Formula 10) ──
    # C_final = (1 - α - γ) × C_Bayes + α × C_ML + γ × C_memory
    alpha_ml = config.credibility_alpha_ml
    gamma_mem = config.credibility_gamma_memory

    # Fallback: if ML or memory unavailable, redistribute weight
    effective_alpha = alpha_ml if c_ml is not None else 0.0
    effective_gamma = gamma_mem if c_memory is not None else 0.0
    effective_bayes_weight = 1.0 - effective_alpha - effective_gamma

    c_final = effective_bayes_weight * c_bayes
    if c_ml is not None:
        c_final += effective_alpha * c_ml
    if c_memory is not None:
        c_final += effective_gamma * c_memory

    # Clamp to [0, 1]
    c_final = min(max(c_final, 0.0), 1.0)

    # ── Step 8: Variance (Formula 9) ──
    # Var_j = Σ w_i × (s_k - C_final)² × decay / N_j
    variance = 0.0
    if n_eff > config.epsilon:
        for interaction in interactions:
            dt = _time_delta_seconds(t_now, interaction.timestamp)
            decay = math.exp(-config.lambda_interaction * dt)
            weighted = interaction.user_weight * decay
            deviation = interaction.vote - c_final
            variance += weighted * deviation * deviation
        variance /= n_eff

    return PostStateSnapshot(
        n_effective=n_eff,
        s_plus=s_plus,
        s_minus=s_minus,
        s_net=s_net,
        c_bayes=c_bayes,
        c_final=c_final,
        variance=variance,
    )


# ──────────────────────────────────────────────────────────
# Incremental update (optimization for streaming)
# ──────────────────────────────────────────────────────────

def incremental_post_update(
    current_s_plus: float,
    current_s_minus: float,
    current_n: float,
    new_vote: int,
    new_weight: float,
    dt_since_last_update: float = 0.0,
) -> tuple[float, float, float, float]:
    """
    Incremental update for a single new interaction.
    Instead of recomputing from all interactions, this applies
    a decay to existing values and adds the new contribution.

    Returns:
        (new_s_plus, new_s_minus, new_n, new_c_bayes)
    """
    # Decay existing values
    decay = math.exp(-config.lambda_interaction * dt_since_last_update)
    s_plus = current_s_plus * decay
    s_minus = current_s_minus * decay
    n_eff = current_n * decay

    # Add new contribution (no time decay for a just-arrived interaction)
    if new_vote == 1:
        s_plus += new_weight
    else:
        s_minus += new_weight
    n_eff += new_weight

    # Recompute C_Bayes
    alpha0 = config.credibility_alpha0
    beta0 = config.credibility_beta0
    c_bayes = (s_plus + alpha0) / (s_plus + s_minus + alpha0 + beta0)

    return s_plus, s_minus, n_eff, c_bayes
