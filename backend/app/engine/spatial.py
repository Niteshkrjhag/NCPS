"""
Spatial Engine — Algorithm 5 (Part A) from pseudo_algorithm.md

Computes:
  - Prox(u,j,t) : proximity between user and post

Source: docs/context/mathematical_formula.md (Proximity formula)
        docs/context/phase4_system_design.md §6
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime

from app.config import config


def haversine_distance(
    lat1: float, lon1: float,
    lat2: float, lon2: float,
) -> float:
    """
    Compute the great-circle distance between two points on Earth.

    Args:
        lat1, lon1: Coordinates of point 1 (degrees).
        lat2, lon2: Coordinates of point 2 (degrees).

    Returns:
        Distance in meters.
    """
    R = 6_371_000  # Earth radius in meters

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def compute_proximity(
    user_lat: float,
    user_lon: float,
    post_lat: float,
    post_lon: float,
    location_confidence: float = 1.0,
) -> float:
    """
    Prox(u,j,t) = L_u(t) × exp(-d² / (2 × σ_p²))

    Source: Algorithm 5, Steps 1–3

    Args:
        user_lat, user_lon: User's current location.
        post_lat, post_lon: Post's location.
        location_confidence: L_u(t) — user's location confidence ∈ [0,1].

    Returns:
        Proximity score ∈ [0,1].
    """
    distance = haversine_distance(user_lat, user_lon, post_lat, post_lon)

    sigma_p = config.spatial_sigma_p
    spatial_factor = math.exp(-(distance ** 2) / (2 * sigma_p ** 2))

    proximity = location_confidence * spatial_factor

    return min(max(proximity, 0.0), 1.0)


def compute_spatial_trust(
    contributor_weights: list[float],
    contributor_location_confs: list[float],
    contributor_decays: list[float],
) -> float:
    """
    L̄_j(t) = Σ(w_i × decay × L_i) / Σ(w_i × decay)

    Average location reliability of post contributors.
    Source: phase4_system_design.md §7

    Args:
        contributor_weights: w_i for each contributor.
        contributor_location_confs: L_i for each contributor.
        contributor_decays: exp(-λ(t - t_k)) for each contributor.

    Returns:
        Spatial trust ∈ [0,1].
    """
    numerator = 0.0
    denominator = 0.0

    for w, l, d in zip(
        contributor_weights,
        contributor_location_confs,
        contributor_decays,
    ):
        contribution = w * d
        numerator += contribution * l
        denominator += contribution

    if denominator < config.epsilon:
        return 0.0

    result = numerator / denominator
    return min(max(result, 0.0), 1.0)


# ──────────────────────────────────────────────────────────
# Phase 4: Location Confidence L_i(t)
# Source: phase4_system_design.md §4.2
# ──────────────────────────────────────────────────────────

@dataclass
class LocationRecord:
    """A single location reading for a user."""

    lat: float
    lon: float
    timestamp: datetime
    accuracy_meters: float = 50.0   # GPS accuracy
    source: str = "gps"             # "gps" or "ip"


def compute_location_confidence(
    location_history: list[LocationRecord],
) -> float:
    """
    L_i(t) = w₁·S_gps + w₂·S_speed + w₃·S_source + w₄·S_cont

    Source: phase4_system_design.md §4.2

    Components:
      S_gps:    GPS accuracy score (better accuracy → higher)
      S_speed:  Speed plausibility (no teleportation → higher)
      S_source: Source quality (GPS > IP)
      S_cont:   Location continuity (stable → higher)

    Args:
        location_history: Chronologically ordered location readings.

    Returns:
        Location confidence ∈ [0, 1].
    """
    if not location_history:
        return 0.0

    if len(location_history) == 1:
        # Single reading: can only assess GPS accuracy and source
        rec = location_history[0]
        s_gps = _gps_accuracy_score(rec.accuracy_meters)
        s_source = 1.0 if rec.source == "gps" else 0.3
        # No speed or continuity data with single reading
        weights = config.location_confidence_weights
        return min(max(weights[0] * s_gps + weights[2] * s_source, 0.0), 1.0)

    # Sort by time
    sorted_locs = sorted(location_history, key=lambda r: r.timestamp)

    # S_gps: Average GPS accuracy score
    s_gps = sum(_gps_accuracy_score(r.accuracy_meters) for r in sorted_locs) / len(sorted_locs)

    # S_speed: Fraction of movements with plausible speed
    plausible_count = 0
    total_movements = 0
    for i in range(1, len(sorted_locs)):
        dt = (sorted_locs[i].timestamp - sorted_locs[i - 1].timestamp).total_seconds()
        if dt < 1.0:
            continue  # Skip near-simultaneous readings
        dist = haversine_distance(
            sorted_locs[i - 1].lat, sorted_locs[i - 1].lon,
            sorted_locs[i].lat, sorted_locs[i].lon,
        )
        speed = dist / dt
        total_movements += 1
        if speed <= config.location_speed_max:
            plausible_count += 1
    s_speed = plausible_count / max(total_movements, 1)

    # S_source: Fraction of GPS-sourced readings
    gps_count = sum(1 for r in sorted_locs if r.source == "gps")
    s_source = gps_count / len(sorted_locs)

    # S_cont: Location continuity — how stable is the user's position?
    # Measure: avg distance between consecutive readings within continuity window
    continuity_distances = []
    window = config.location_continuity_window
    for i in range(1, len(sorted_locs)):
        dt = (sorted_locs[i].timestamp - sorted_locs[i - 1].timestamp).total_seconds()
        if dt <= window:
            dist = haversine_distance(
                sorted_locs[i - 1].lat, sorted_locs[i - 1].lon,
                sorted_locs[i].lat, sorted_locs[i].lon,
            )
            continuity_distances.append(dist)
    if continuity_distances:
        avg_drift = sum(continuity_distances) / len(continuity_distances)
        # Normalize: 0m → 1.0, >5000m → 0.0
        s_cont = max(0.0, 1.0 - avg_drift / config.spatial_sigma_p)
    else:
        s_cont = 0.5  # Insufficient data

    # Weighted combination
    weights = config.location_confidence_weights
    l_i = (
        weights[0] * s_gps
        + weights[1] * s_speed
        + weights[2] * s_source
        + weights[3] * s_cont
    )

    return min(max(l_i, 0.0), 1.0)


def _gps_accuracy_score(accuracy_meters: float) -> float:
    """Convert GPS accuracy in meters to a score in [0, 1]."""
    threshold = config.location_gps_accuracy_threshold
    if accuracy_meters <= 0:
        return 1.0
    return min(max(1.0 - accuracy_meters / (threshold * 2), 0.0), 1.0)


def compute_location_inconsistency(
    location_history: list[LocationRecord],
) -> float:
    """
    D_5(i,t) = N_implausible / N_movements

    Fraction of location transitions that are physically implausible
    (speed exceeds maximum plausible speed).

    Source: mathematical_formula.md — Formula 3, component D_5

    Args:
        location_history: Chronologically ordered location readings.

    Returns:
        Location inconsistency ∈ [0, 1]. Higher = more suspicious.
    """
    if len(location_history) < 2:
        return 0.0

    sorted_locs = sorted(location_history, key=lambda r: r.timestamp)

    implausible = 0
    total = 0
    for i in range(1, len(sorted_locs)):
        dt = (sorted_locs[i].timestamp - sorted_locs[i - 1].timestamp).total_seconds()
        if dt < 1.0:
            continue
        dist = haversine_distance(
            sorted_locs[i - 1].lat, sorted_locs[i - 1].lon,
            sorted_locs[i].lat, sorted_locs[i].lon,
        )
        speed = dist / dt
        total += 1
        if speed > config.location_speed_max:
            implausible += 1

    if total == 0:
        return 0.0

    return implausible / total


# ──────────────────────────────────────────────────────────
# Phase 4: Post Location Estimation
# Source: phase4_system_design.md §5
# ──────────────────────────────────────────────────────────

def estimate_post_location(
    voter_lats: list[float],
    voter_lons: list[float],
    voter_weights: list[float],
) -> tuple[float, float]:
    """
    Estimate post location as weighted average of voter locations.

    Fallback strategy from phase4_system_design.md §5:
        l_j = weighted avg of user locations

    Args:
        voter_lats: Latitude of each voter.
        voter_lons: Longitude of each voter.
        voter_weights: w_i for each voter.

    Returns:
        (estimated_lat, estimated_lon)
    """
    if not voter_lats:
        return 0.0, 0.0

    total_weight = sum(voter_weights) + config.epsilon
    est_lat = sum(w * lat for w, lat in zip(voter_weights, voter_lats)) / total_weight
    est_lon = sum(w * lon for w, lon in zip(voter_weights, voter_lons)) / total_weight

    return est_lat, est_lon

