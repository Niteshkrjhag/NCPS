"""
Urgency Engine — Algorithm 5 (Part B) from pseudo_algorithm.md

Computes:
  - K_j : keyword score
  - Cat_j : category score
  - V_j : velocity (interaction rate)
  - U_j : final urgency score

Source: docs/context/mathematical_formula.md (Formula for U_j)
        docs/context/data_collection_protocol.md §4.3–4.4
"""

from __future__ import annotations

import math
from datetime import datetime, timezone

from app.config import config
from app.engine.post_engine import PostInteraction


def _time_delta_seconds(t_now: datetime, t_event: datetime) -> float:
    """Compute time difference in seconds, always non-negative."""
    delta = (t_now - t_event).total_seconds()
    return max(delta, 0.0)


def compute_keyword_score(text: str) -> float:
    """
    K_j = Σ φ(word) / total_words

    Uses the urgency keyword dictionary from config.
    Source: data_collection_protocol.md §4.3
    """
    words = text.lower().split()
    if not words:
        return 0.0

    total_score = 0.0
    for word in words:
        # Strip punctuation for matching
        clean_word = word.strip(".,!?;:\"'()[]{}").lower()
        total_score += config.urgency_keywords.get(clean_word, 0.0)

    return total_score / len(words)


def compute_category_score(text: str) -> float:
    """
    Cat_j — simplified category classification.
    Source: data_collection_protocol.md §4.4

    Demo rule:
      if keyword_score > threshold: Cat = 1.0
      else: Cat = 0.3
    """
    k_score = compute_keyword_score(text)
    threshold = 0.1  # If > 10% of words are urgency keywords
    return 1.0 if k_score > threshold else 0.3


def compute_velocity(
    interactions: list[PostInteraction],
    t_now: datetime | None = None,
) -> float:
    """
    V_j = 1 - exp(-rate / rate_baseline)

    Where rate = Σ w_i (for interactions in [t - Δt, t]) / Δt

    Source: Algorithm 5, Step 6–7
    """
    if t_now is None:
        t_now = datetime.now(timezone.utc)

    delta_t = config.urgency_delta_t
    mass_recent = 0.0

    for interaction in interactions:
        dt = _time_delta_seconds(t_now, interaction.timestamp)
        if dt <= delta_t:
            mass_recent += interaction.user_weight

    rate = mass_recent / delta_t if delta_t > 0 else 0.0
    velocity = 1.0 - math.exp(-rate / config.urgency_rate_baseline)

    return velocity


def compute_urgency(
    text: str,
    interactions: list[PostInteraction],
    t_now: datetime | None = None,
) -> float:
    """
    Final urgency score (Algorithm 5, Step 8–9).

    U_j = 1 - exp(-(β₁ × K + β₂ × Cat + β₃ × V))

    All values bounded in [0, 1].
    """
    if t_now is None:
        t_now = datetime.now(timezone.utc)

    k_score = compute_keyword_score(text)
    cat_score = compute_category_score(text)
    velocity = compute_velocity(interactions, t_now)

    beta1, beta2, beta3 = config.urgency_beta_weights

    urgency_input = beta1 * k_score + beta2 * cat_score + beta3 * velocity
    urgency = 1.0 - math.exp(-urgency_input)

    return min(max(urgency, 0.0), 1.0)
