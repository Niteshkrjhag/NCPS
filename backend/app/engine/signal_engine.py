"""
Signal Engine — Phase 6: Extended Input Signals (10-14).

Implements the 5 missing signals from input_signal.md:
  - S_nav:     Navigation deviation (Signal 10)
  - S_device:  Device fingerprint consistency (Signal 11)
  - S_ip:      IP consistency (Signal 12)
  - S_session: Session continuity (Signal 13)
  - S_timing:  Vote timing irregularity (Signal 14)

These signals feed into ML anomaly features, NOT rule-based anomaly.
They require data (device, IP) that may not always be available,
so they supplement the ML model rather than gating decisions.
"""

from __future__ import annotations

import math
import logging
from dataclasses import dataclass
from datetime import datetime

import numpy as np

from app.config import config

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────
# Signal 10: Navigation Deviation S_nav
# ──────────────────────────────────────────────────

def compute_navigation_deviation(
    locations: list[tuple[float, float, float]],
) -> float:
    """
    S_nav = 1 - exp(-D_nav / κ)

    Measures how much user movement deviates from typical human patterns
    using step-length and turn-angle distribution comparison.

    Args:
        locations: List of (lat, lon, timestamp_seconds) tuples.

    Returns:
        S_nav ∈ [0, 1]. Higher = more abnormal movement.
    """
    if len(locations) < 3:
        return 0.0  # Not enough data

    # Compute step lengths and turn angles
    steps = []
    angles = []
    for i in range(1, len(locations)):
        dlat = locations[i][0] - locations[i - 1][0]
        dlon = locations[i][1] - locations[i - 1][1]
        step = math.sqrt(dlat * dlat + dlon * dlon) * 111000  # ~meters
        steps.append(step)

        if i >= 2:
            dlat_prev = locations[i - 1][0] - locations[i - 2][0]
            dlon_prev = locations[i - 1][1] - locations[i - 2][1]
            # Angle between consecutive displacement vectors
            dot = dlat * dlat_prev + dlon * dlon_prev
            mag1 = math.sqrt(dlat * dlat + dlon * dlon) + 1e-10
            mag2 = math.sqrt(dlat_prev * dlat_prev + dlon_prev * dlon_prev) + 1e-10
            cos_angle = max(-1.0, min(1.0, dot / (mag1 * mag2)))
            angle = math.acos(cos_angle)
            angles.append(angle)

    if not steps:
        return 0.0

    # Human reference: step lengths follow log-normal, angles are moderate
    # Compute JS-divergence approximation using histogram comparison
    step_arr = np.array(steps)
    human_step_mean = 50.0  # ~50m typical between readings
    human_step_std = 100.0

    # Step deviation: how far from human-like distribution
    step_dev = abs(np.mean(step_arr) - human_step_mean) / (human_step_std + 1e-10)

    # Angle deviation: human angles are varied; bots are either 0 or π
    angle_dev = 0.0
    if angles:
        angle_arr = np.array(angles)
        angle_variance = np.var(angle_arr)
        human_angle_var = 1.0  # ~1 radian² expected variance
        angle_dev = abs(angle_variance - human_angle_var) / (human_angle_var + 1e-10)

    # Combined deviation
    d_nav = (step_dev + angle_dev) / 2.0
    s_nav = 1.0 - math.exp(-d_nav / config.signal_nav_kappa)

    return min(max(s_nav, 0.0), 1.0)


# ──────────────────────────────────────────────────
# Signal 11: Device Fingerprint Consistency S_device
# ──────────────────────────────────────────────────

def compute_device_consistency(
    device_ids: list[str],
    timestamps: list[float] | None = None,
) -> float:
    """
    S_device = exp(-H_device / log|D_i|)

    Measures how consistent a user's device usage is.
    Single device → high score. Rotating devices → low score.

    Args:
        device_ids: List of device IDs used in interactions.
        timestamps: Optional timestamps for time-decay weighting.

    Returns:
        S_device ∈ [0, 1]. Higher = more consistent.
    """
    if not device_ids:
        return 1.0  # No data → assume consistent

    unique = set(device_ids)
    n_unique = len(unique)

    if n_unique <= 1:
        return 1.0  # Single device

    # Compute device usage distribution
    counts: dict[str, int] = {}
    for d in device_ids:
        counts[d] = counts.get(d, 0) + 1

    total = len(device_ids)
    entropy = 0.0
    for count in counts.values():
        if count > 0:
            p = count / total
            entropy -= p * math.log(p)

    max_entropy = math.log(n_unique)
    if max_entropy < 1e-10:
        return 1.0

    normalized_entropy = entropy / max_entropy
    s_device = math.exp(-normalized_entropy)

    return min(max(s_device, 0.0), 1.0)


# ──────────────────────────────────────────────────
# Signal 12: IP Consistency S_ip
# ──────────────────────────────────────────────────

def compute_ip_consistency(
    ip_addresses: list[str],
    ip_locations: list[tuple[float, float]] | None = None,
) -> float:
    """
    S_ip = exp(-H_ip / log|I_i|) × exp(-σ²_ip_loc / 2σ_ip²)

    Measures IP stability and geographic consistency.

    Args:
        ip_addresses: List of IP addresses used.
        ip_locations: Optional (lat, lon) for each IP.

    Returns:
        S_ip ∈ [0, 1]. Higher = more consistent.
    """
    if not ip_addresses:
        return 1.0

    unique = set(ip_addresses)
    n_unique = len(unique)

    # IP entropy component
    if n_unique <= 1:
        ip_entropy_score = 1.0
    else:
        counts: dict[str, int] = {}
        for ip in ip_addresses:
            counts[ip] = counts.get(ip, 0) + 1
        total = len(ip_addresses)
        entropy = 0.0
        for count in counts.values():
            if count > 0:
                p = count / total
                entropy -= p * math.log(p)
        max_entropy = math.log(n_unique)
        normalized = entropy / max_entropy if max_entropy > 1e-10 else 0.0
        ip_entropy_score = math.exp(-normalized)

    # Geographic consistency component
    geo_score = 1.0
    if ip_locations and len(ip_locations) >= 2:
        lats = [loc[0] for loc in ip_locations]
        lons = [loc[1] for loc in ip_locations]
        mean_lat = sum(lats) / len(lats)
        mean_lon = sum(lons) / len(lons)
        variance = sum(
            (lat - mean_lat) ** 2 + (lon - mean_lon) ** 2
            for lat, lon in ip_locations
        ) / len(ip_locations)
        sigma_ip_sq = 0.01  # ~1 degree normalization
        geo_score = math.exp(-variance / (2 * sigma_ip_sq))

    s_ip = ip_entropy_score * geo_score
    return min(max(s_ip, 0.0), 1.0)


# ──────────────────────────────────────────────────
# Signal 13: Session Continuity S_session
# ──────────────────────────────────────────────────

def compute_session_continuity(
    timestamps: list[float],
) -> float:
    """
    S_session = exp(-D_session / δ)

    Measures how closely session patterns match human behavior.

    Args:
        timestamps: Sorted list of interaction timestamps (seconds).

    Returns:
        S_session ∈ [0, 1]. Higher = more human-like.
    """
    if len(timestamps) < 3:
        return 1.0  # Not enough data

    sorted_ts = sorted(timestamps)
    gap_threshold = config.signal_session_gap

    # Identify sessions
    sessions = []
    session_start = sorted_ts[0]
    for i in range(1, len(sorted_ts)):
        gap = sorted_ts[i] - sorted_ts[i - 1]
        if gap > gap_threshold:
            session_dur = sorted_ts[i - 1] - session_start
            sessions.append(session_dur)
            session_start = sorted_ts[i]
    # Last session
    sessions.append(sorted_ts[-1] - session_start)

    if not sessions:
        return 1.0

    # Session statistics
    mu_sess = sum(sessions) / len(sessions)
    if len(sessions) > 1:
        sigma_sess = math.sqrt(
            sum((d - mu_sess) ** 2 for d in sessions) / len(sessions)
        )
    else:
        sigma_sess = 0.0

    # Deviation from human baseline
    mu_human = config.signal_session_mu_human
    sigma_human = config.signal_session_sigma_human

    d_session = (
        abs(mu_sess - mu_human) / (mu_human + 1e-10)
        + abs(sigma_sess - sigma_human) / (sigma_human + 1e-10)
    )

    s_session = math.exp(-d_session / config.signal_session_delta)
    return min(max(s_session, 0.0), 1.0)


# ──────────────────────────────────────────────────
# Signal 14: Vote Timing Irregularity S_timing
# ──────────────────────────────────────────────────

def compute_timing_irregularity(
    timestamps: list[float],
) -> float:
    """
    S_timing = exp(-σ²_Δt / σ_t²) × exp(-B_i / B_0)

    Low variance = too regular (bot-like).
    High burstiness = coordinated/spam.
    Both penalize the score.

    Args:
        timestamps: Sorted list of interaction timestamps (seconds).

    Returns:
        S_timing ∈ [0, 1]. Higher = more natural timing.
    """
    if len(timestamps) < 3:
        return 1.0  # Not enough data

    sorted_ts = sorted(timestamps)

    # Compute inter-event time gaps
    gaps = [sorted_ts[i] - sorted_ts[i - 1] for i in range(1, len(sorted_ts))]
    if not gaps:
        return 1.0

    # Variance of time gaps
    mean_gap = sum(gaps) / len(gaps)
    variance = sum((g - mean_gap) ** 2 for g in gaps) / len(gaps)

    # Low variance penalty (bots have perfectly regular timing)
    # NOTE: We penalize LOW variance, so formula is exp(-σ²/σ_t²)
    # which gives HIGH score for HIGH variance (human) and LOW for LOW variance (bot)
    sigma_t_sq = config.signal_timing_sigma_sq
    regularity_score = 1.0 - math.exp(-variance / sigma_t_sq)

    # Burstiness: max actions in any 60s window / average
    window = 60.0
    bin_counts: dict[int, int] = {}
    for t in sorted_ts:
        bin_idx = int(t / window)
        bin_counts[bin_idx] = bin_counts.get(bin_idx, 0) + 1

    if bin_counts:
        max_bin = max(bin_counts.values())
        avg_bin = sum(bin_counts.values()) / len(bin_counts)
        burstiness = max_bin / (avg_bin + 1e-10)
    else:
        burstiness = 0.0

    burstiness_score = math.exp(-burstiness / config.signal_timing_b0)

    s_timing = regularity_score * burstiness_score
    return min(max(s_timing, 0.0), 1.0)


# ──────────────────────────────────────────────────
# Convenience: Compute all extended signals
# ──────────────────────────────────────────────────

@dataclass
class ExtendedSignals:
    """All 5 extended signals for a user."""
    navigation_deviation: float = 0.0
    device_consistency: float = 1.0
    ip_consistency: float = 1.0
    session_continuity: float = 1.0
    timing_irregularity: float = 1.0


def compute_all_extended_signals(
    locations: list[tuple[float, float, float]] | None = None,
    device_ids: list[str] | None = None,
    ip_addresses: list[str] | None = None,
    ip_locations: list[tuple[float, float]] | None = None,
    timestamps: list[float] | None = None,
) -> ExtendedSignals:
    """Compute all 5 extended signals for a user."""
    return ExtendedSignals(
        navigation_deviation=compute_navigation_deviation(locations or []),
        device_consistency=compute_device_consistency(device_ids or []),
        ip_consistency=compute_ip_consistency(ip_addresses or [], ip_locations),
        session_continuity=compute_session_continuity(timestamps or []),
        timing_irregularity=compute_timing_irregularity(timestamps or []),
    )
