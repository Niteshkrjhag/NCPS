"""
Decision Engine — Algorithms 6 & 7 from pseudo_algorithm.md

Computes:
  - Expand(j,t) : propagation decision (Algorithm 6)
  - Alert(u,j,t) : alert decision (Algorithm 7)

Source: docs/context/pseudo_algorithm.md
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone

from app.config import config
from app.engine.spatial import compute_proximity, compute_spatial_trust


@dataclass
class PropagationInput:
    """All data needed for the propagation decision."""

    c_final: float           # Post credibility C_j(t)
    n_effective: float       # Interaction mass N_j(t)
    variance: float          # Variance Var_j(t)
    post_age_seconds: float  # t - t_create
    current_radius: float    # Current propagation radius

    # Spatial trust contributors
    contributor_weights: list[float]
    contributor_location_confs: list[float]
    contributor_decays: list[float]


@dataclass
class PropagationResult:
    """Result of the propagation decision."""

    should_expand: bool
    new_radius: float
    spatial_trust: float

    # Condition breakdown for debugging
    cond_credibility: bool
    cond_evidence: bool
    cond_stability: bool
    cond_time: bool
    cond_location: bool


def decide_propagation(inp: PropagationInput) -> PropagationResult:
    """
    Algorithm 6: Propagation Decision.

    Expand if ALL conditions are met:
      1. C_j ≥ θ
      2. N_j ≥ N_min
      3. Var_j ≤ σ²
      4. age ≥ T_min
      5. L̄_j ≥ L_min

    Source: pseudo_algorithm.md — Algorithm 6
    """
    # Step 1
    cond_credibility = inp.c_final >= config.propagation_theta

    # Step 2
    cond_evidence = inp.n_effective >= config.propagation_n_min

    # Step 3
    cond_stability = inp.variance <= config.propagation_sigma_sq

    # Step 4
    cond_time = inp.post_age_seconds >= config.propagation_t_min

    # Step 5: Compute spatial trust
    spatial_trust = compute_spatial_trust(
        inp.contributor_weights,
        inp.contributor_location_confs,
        inp.contributor_decays,
    )
    cond_location = spatial_trust >= config.propagation_l_min

    # Step 7: Final decision (all must pass)
    should_expand = (
        cond_credibility
        and cond_evidence
        and cond_stability
        and cond_time
        and cond_location
    )

    # Step 8: Apply expansion
    new_radius = inp.current_radius
    if should_expand:
        new_radius = min(
            inp.current_radius * config.propagation_growth_factor,
            config.propagation_r_max,
        )

    return PropagationResult(
        should_expand=should_expand,
        new_radius=new_radius,
        spatial_trust=spatial_trust,
        cond_credibility=cond_credibility,
        cond_evidence=cond_evidence,
        cond_stability=cond_stability,
        cond_time=cond_time,
        cond_location=cond_location,
    )


@dataclass
class AlertInput:
    """All data needed for the alert decision."""

    # User location
    user_lat: float
    user_lon: float
    user_location_confidence: float

    # Post data
    post_lat: float
    post_lon: float
    c_final: float       # C_j(t)
    urgency: float       # U_j(t)
    variance: float      # Var_j(t)

    # Rate limiting
    recent_alert_count: int


@dataclass
class AlertResult:
    """Result of the alert decision."""

    should_alert: bool
    proximity: float
    importance_score: float

    # Condition breakdown
    cond_proximity: bool
    cond_importance: bool
    cond_stability: bool
    cond_rate: bool


def decide_alert(inp: AlertInput) -> AlertResult:
    """
    Algorithm 7: Alert Decision.

    Alert if ALL conditions are met:
      1. Prox(u,j,t) ≥ τ_p
      2. C_j × U_j ≥ θ_alert
      3. Var_j ≤ σ²
      4. Not rate-limited

    Source: pseudo_algorithm.md — Algorithm 7
    """
    # Step 1: Proximity
    proximity = compute_proximity(
        inp.user_lat, inp.user_lon,
        inp.post_lat, inp.post_lon,
        inp.user_location_confidence,
    )
    cond_proximity = proximity >= config.alert_tau_p

    # Step 2: Importance (credibility × urgency)
    importance = inp.c_final * inp.urgency
    cond_importance = importance >= config.alert_theta

    # Step 3: Stability
    cond_stability = inp.variance <= config.propagation_sigma_sq

    # Step 4: Rate limiting
    cond_rate = inp.recent_alert_count < config.alert_rate_max

    # Step 5: Final decision
    should_alert = (
        cond_proximity
        and cond_importance
        and cond_stability
        and cond_rate
    )

    return AlertResult(
        should_alert=should_alert,
        proximity=proximity,
        importance_score=importance,
        cond_proximity=cond_proximity,
        cond_importance=cond_importance,
        cond_stability=cond_stability,
        cond_rate=cond_rate,
    )
