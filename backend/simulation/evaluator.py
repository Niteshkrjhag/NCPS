"""
Evaluation Engine — Metrics from simulation_evaluation_framework.md §6

Computes:
  - Credibility Accuracy
  - Brier Score (Calibration)
  - Attack Success Rate
  - User Weight Quality
  - Anomaly Detection Quality
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class EvaluationMetrics:
    """All evaluation metrics for one experiment run."""

    # §6.1 Credibility Accuracy
    accuracy: float = 0.0

    # §6.2 Brier Score
    brier_score: float = 0.0

    # §6.4 Attack Success Rate
    attack_success_rate: float = 0.0

    # §6.5 User Weight Quality
    weight_correlation: float = 0.0

    # §6.6 Anomaly Detection
    anomaly_precision: float = 0.0
    anomaly_recall: float = 0.0

    # Post counts
    total_posts: int = 0
    true_posts: int = 0
    false_posts: int = 0


def compute_accuracy(
    credibilities: list[float],
    ground_truths: list[int],
    threshold: float = 0.5,
) -> float:
    """
    §6.1 Credibility Accuracy

    Accuracy = (1/|P|) × Σ I(sign(C_j) = y_j)

    Args:
        credibilities: C_j values for each post.
        ground_truths: y_j values (+1 or -1).
        threshold: Decision boundary.

    Returns:
        Accuracy ∈ [0, 1].
    """
    if not credibilities:
        return 0.0

    correct = 0
    for c, y in zip(credibilities, ground_truths):
        predicted = 1 if c >= threshold else -1
        if predicted == y:
            correct += 1

    return correct / len(credibilities)


def compute_brier_score(
    credibilities: list[float],
    ground_truths: list[int],
) -> float:
    """
    §6.2 Brier Score (Calibration)

    Brier = (1/|P|) × Σ (C_j - y_j_binary)²

    Lower is better.
    """
    if not credibilities:
        return 0.0

    total = 0.0
    for c, y in zip(credibilities, ground_truths):
        # Convert y from {-1, +1} to {0, 1}
        y_binary = (y + 1) / 2.0
        total += (c - y_binary) ** 2

    return total / len(credibilities)


def compute_attack_success_rate(
    false_post_credibilities: list[float],
    threshold: float = 0.5,
) -> float:
    """
    §6.4 Attack Success Rate

    Fraction of false posts incorrectly classified as true.
    """
    if not false_post_credibilities:
        return 0.0

    fooled = sum(1 for c in false_post_credibilities if c >= threshold)
    return fooled / len(false_post_credibilities)


def compute_weight_correlation(
    estimated_weights: list[float],
    true_reliabilities: list[float],
) -> float:
    """
    §6.5 User Weight Quality

    Pearson correlation between w_i and true reliability.
    """
    n = len(estimated_weights)
    if n < 2:
        return 0.0

    mean_w = sum(estimated_weights) / n
    mean_r = sum(true_reliabilities) / n

    cov = sum((w - mean_w) * (r - mean_r) for w, r in zip(estimated_weights, true_reliabilities))
    std_w = math.sqrt(sum((w - mean_w) ** 2 for w in estimated_weights))
    std_r = math.sqrt(sum((r - mean_r) ** 2 for r in true_reliabilities))

    if std_w < 1e-10 or std_r < 1e-10:
        return 0.0

    return cov / (std_w * std_r)


def compute_anomaly_detection(
    predicted_anomalies: list[bool],
    actual_anomalies: list[bool],
) -> tuple[float, float]:
    """
    §6.6 Anomaly Detection Quality

    Returns (precision, recall) for adversarial user detection.
    """
    tp = sum(1 for p, a in zip(predicted_anomalies, actual_anomalies) if p and a)
    fp = sum(1 for p, a in zip(predicted_anomalies, actual_anomalies) if p and not a)
    fn = sum(1 for p, a in zip(predicted_anomalies, actual_anomalies) if not p and a)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0

    return precision, recall
