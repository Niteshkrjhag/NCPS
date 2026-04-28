"""
Spatial Engine — Algorithm 5 (Part A) from pseudo_algorithm.md

Computes:
  - Prox(u,j,t) : proximity between user and post

Source: docs/context/mathematical_formula.md (Proximity formula)
        docs/context/phase4_system_design.md §6
"""

from __future__ import annotations

import math


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
