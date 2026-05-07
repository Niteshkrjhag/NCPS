"""
ML Engine -- Phase 5+6

Implements:
  - C_ML:     Content-based credibility prediction
  - C_memory: Similarity-based historical credibility
  - Anom_ML:  Learned anomaly detection

Phase 6 expansion: AnomalyMLModel uses 11 features (6 original + 5 signals).

All models use scikit-learn LogisticRegression for simplicity,
interpretability, and no overfitting risk with small feature sets.
"""

from __future__ import annotations

import math
import logging
from dataclasses import dataclass, field
from datetime import datetime

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler

from app.config import config

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────
# Data structures
# ──────────────────────────────────────────────────────────

@dataclass
class PostFeatures:
    """Features for ML credibility prediction."""

    keyword_score: float = 0.0       # Urgency keyword density
    word_count: int = 0              # Post length
    urgent_word_ratio: float = 0.0   # Fraction of urgent words
    early_vote_ratio: float = 0.5    # Positive ratio in first votes
    interaction_velocity: float = 0.0  # How fast votes arrive


@dataclass
class UserBehaviorFeatures:
    """Features for ML anomaly detection (Phase 5+6 signals 10-14)."""

    # Phase 5 original features (6)
    activity_rate: float = 0.0       # Normalized interaction frequency
    vote_entropy: float = 0.5        # Action diversity
    consensus_deviation: float = 0.0  # Disagreement with truth
    coordination_score: float = 0.0  # From graph engine
    location_inconsistency: float = 0.0  # From spatial engine
    avg_vote_value: float = 0.0      # Average vote direction
    # Phase 6 extended signals (5)
    navigation_deviation: float = 0.0   # Signal 10: S_nav
    device_consistency: float = 1.0     # Signal 11: S_device
    ip_consistency: float = 1.0         # Signal 12: S_ip
    session_continuity: float = 1.0     # Signal 13: S_session
    timing_irregularity: float = 1.0    # Signal 14: S_timing


@dataclass
class MemoryEntry:
    """A stored post for memory-based credibility lookup."""

    post_id: str
    content: str
    credibility: float  # Final known credibility


# ──────────────────────────────────────────────────────────
# Part 4: ML Credibility Model (C_ML)
# ──────────────────────────────────────────────────────────

class CredibilityMLModel:
    """
    Predicts post credibility from content features.

    C_ML(j,t) = σ(f(x_j) / T)

    Uses LogisticRegression on post features.
    Temperature T > 1 softens predictions to avoid overconfidence.
    """

    def __init__(self) -> None:
        self._model: LogisticRegression | None = None
        self._scaler: StandardScaler | None = None
        self._trained = False

    def train(
        self,
        features_list: list[PostFeatures],
        labels: list[int],
    ) -> None:
        """
        Train the credibility model.

        Args:
            features_list: Feature vectors for each post.
            labels: Ground truth labels (1 = true, 0 = false).
        """
        if len(features_list) < 10:
            logger.warning("Too few training samples for C_ML, skipping")
            return

        X = self._features_to_matrix(features_list)
        y = np.array(labels)

        self._scaler = StandardScaler()
        X_scaled = self._scaler.fit_transform(X)

        self._model = LogisticRegression(
            C=1.0,            # Standard regularization
            max_iter=200,
            random_state=42,
        )
        self._model.fit(X_scaled, y)
        self._trained = True

        train_acc = self._model.score(X_scaled, y)
        logger.info(f"C_ML trained: accuracy={train_acc:.3f}, samples={len(labels)}")

    def predict(self, features: PostFeatures) -> float:
        """
        Predict credibility for a single post.

        Returns:
            C_ML ∈ [0, 1], temperature-calibrated.
        """
        if not self._trained:
            return 0.5  # No training data → uninformative prior

        X = self._features_to_matrix([features])
        X_scaled = self._scaler.transform(X)

        # Get raw probability
        prob = self._model.predict_proba(X_scaled)[0]

        # prob[1] = P(true), apply temperature scaling
        # σ(logit / T) where T > 1 softens toward 0.5
        logit = np.log(prob[1] / (prob[0] + 1e-10) + 1e-10)
        scaled_logit = logit / config.ml_temperature
        c_ml = 1.0 / (1.0 + math.exp(-scaled_logit))

        return min(max(c_ml, 0.0), 1.0)

    def _features_to_matrix(self, features_list: list[PostFeatures]) -> np.ndarray:
        """Convert PostFeatures list to numpy matrix."""
        return np.array([
            [
                f.keyword_score,
                f.word_count,
                f.urgent_word_ratio,
                f.early_vote_ratio,
                f.interaction_velocity,
            ]
            for f in features_list
        ])


# ──────────────────────────────────────────────────────────
# Part 5: Memory-Based Credibility (C_memory)
# ──────────────────────────────────────────────────────────

class MemoryEngine:
    """
    Similarity-based credibility from past posts.

    C_memory(j,t) = Σ Sim(j,k) × C_k / Σ Sim(j,k)

    Uses TF-IDF vectors and cosine similarity.
    Detects repeated misinformation patterns.
    """

    def __init__(self) -> None:
        self._vectorizer: TfidfVectorizer | None = None
        self._memory: list[MemoryEntry] = []
        self._tfidf_matrix = None
        self._built = False

    def build_memory(self, entries: list[MemoryEntry]) -> None:
        """
        Build the memory index from past posts.

        Args:
            entries: Historical posts with known credibility.
        """
        if len(entries) < 3:
            logger.warning("Too few memory entries, skipping")
            return

        self._memory = entries
        texts = [e.content for e in entries]

        self._vectorizer = TfidfVectorizer(
            max_features=500,     # Reasonable for short posts
            stop_words="english",
            ngram_range=(1, 2),   # Unigrams and bigrams
        )
        self._tfidf_matrix = self._vectorizer.fit_transform(texts)
        self._built = True

        logger.info(f"Memory built: {len(entries)} posts, "
                     f"{self._tfidf_matrix.shape[1]} TF-IDF features")

    def query(self, content: str) -> float | None:
        """
        Query memory for content-similar past posts.

        C_memory = Σ Sim(j,k) × C_k / Σ Sim(j,k)

        Args:
            content: Text content of the query post.

        Returns:
            C_memory ∈ [0, 1] or None if memory is empty.
        """
        if not self._built or not self._memory:
            return None

        # Embed query
        query_vec = self._vectorizer.transform([content])

        # Compute similarities to all stored posts
        similarities = cosine_similarity(query_vec, self._tfidf_matrix)[0]

        # Get top-K most similar
        top_k = config.memory_top_k
        if len(similarities) <= top_k:
            top_indices = list(range(len(similarities)))
        else:
            top_indices = np.argsort(similarities)[-top_k:]

        # Weighted average credibility
        numerator = 0.0
        denominator = 0.0
        for idx in top_indices:
            sim = float(similarities[idx])
            if sim > 0.01:  # Ignore near-zero similarity
                cred = self._memory[idx].credibility
                numerator += sim * cred
                denominator += sim

        if denominator < 1e-8:
            return None  # No meaningful similarity found

        c_memory = numerator / denominator
        return min(max(c_memory, 0.0), 1.0)


# ──────────────────────────────────────────────────────────
# Part 6: ML Anomaly Detection (Anom_ML)
# ──────────────────────────────────────────────────────────

class AnomalyMLModel:
    """
    Learned anomaly detection from user behavior features.

    Anom_ML = σ(f(x_i))

    Uses LogisticRegression on behavioral features.
    Final anomaly = (1-β) × Anom_rule + β × Anom_ML
    """

    def __init__(self) -> None:
        self._model: LogisticRegression | None = None
        self._scaler: StandardScaler | None = None
        self._trained = False

    def train(
        self,
        features_list: list[UserBehaviorFeatures],
        labels: list[int],
    ) -> None:
        """
        Train the anomaly model.

        Args:
            features_list: Behavioral features for each user.
            labels: 1 = adversarial/bot, 0 = honest/noisy.
        """
        if len(features_list) < 10:
            logger.warning("Too few training samples for Anom_ML, skipping")
            return

        X = self._features_to_matrix(features_list)
        y = np.array(labels)

        # Check if we have both classes
        if len(set(y)) < 2:
            logger.warning("Only one class in training data, skipping Anom_ML")
            return

        self._scaler = StandardScaler()
        X_scaled = self._scaler.fit_transform(X)

        self._model = LogisticRegression(
            C=0.5,            # Slightly stronger regularization
            max_iter=200,
            random_state=42,
        )
        self._model.fit(X_scaled, y)
        self._trained = True

        train_acc = self._model.score(X_scaled, y)
        logger.info(f"Anom_ML trained: accuracy={train_acc:.3f}, samples={len(labels)}")

    def predict(self, features: UserBehaviorFeatures) -> float:
        """
        Predict anomaly score for a single user.

        Returns:
            Anom_ML ∈ [0, 1]. Higher = more anomalous.
        """
        if not self._trained:
            return 0.0  # No training → don't penalize anyone

        X = self._features_to_matrix([features])
        X_scaled = self._scaler.transform(X)

        # P(anomalous)
        prob = self._model.predict_proba(X_scaled)[0]
        # prob[1] = P(is_adversarial)
        return float(prob[1])

    def _features_to_matrix(
        self, features_list: list[UserBehaviorFeatures],
    ) -> np.ndarray:
        """Convert UserBehaviorFeatures list to numpy matrix (11 features)."""
        return np.array([
            [
                f.activity_rate,
                f.vote_entropy,
                f.consensus_deviation,
                f.coordination_score,
                f.location_inconsistency,
                f.avg_vote_value,
                f.navigation_deviation,
                1.0 - f.device_consistency,   # Invert: low consistency = high anomaly
                1.0 - f.ip_consistency,       # Invert: low consistency = high anomaly
                1.0 - f.session_continuity,   # Invert: low continuity = high anomaly
                1.0 - f.timing_irregularity,  # Invert: low regularity = high anomaly
            ]
            for f in features_list
        ])


# ──────────────────────────────────────────────────────────
# Feature extraction helpers
# ──────────────────────────────────────────────────────────

URGENT_WORDS = set(config.urgency_keywords.keys())


def extract_post_features(
    content: str,
    early_votes: list[int] | None = None,
    interaction_count: int = 0,
    time_span_seconds: float = 1.0,
) -> PostFeatures:
    """
    Extract features for ML credibility prediction.

    All features are available at post creation or early stage.
    No ground truth leakage.
    """
    words = content.lower().split()
    word_count = len(words)

    # Keyword score
    urgent_count = sum(1 for w in words if w.strip(".,!?;:\"'()[]{}") in URGENT_WORDS)
    keyword_score = urgent_count / max(word_count, 1)
    urgent_word_ratio = urgent_count / max(word_count, 1)

    # Early vote ratio
    early_vote_ratio = 0.5  # Default: uninformative
    if early_votes and len(early_votes) > 0:
        positive = sum(1 for v in early_votes if v == 1)
        early_vote_ratio = positive / len(early_votes)

    # Interaction velocity
    velocity = interaction_count / max(time_span_seconds, 1.0)

    return PostFeatures(
        keyword_score=keyword_score,
        word_count=word_count,
        urgent_word_ratio=urgent_word_ratio,
        early_vote_ratio=early_vote_ratio,
        interaction_velocity=velocity,
    )


def extract_user_behavior_features(
    interactions_count: int,
    total_time_seconds: float,
    action_counts: dict[str, int],
    consensus_deviation: float,
    coordination_score: float,
    location_inconsistency: float,
    votes: list[int],
    navigation_deviation: float = 0.0,
    device_consistency: float = 1.0,
    ip_consistency: float = 1.0,
    session_continuity: float = 1.0,
    timing_irregularity: float = 1.0,
) -> UserBehaviorFeatures:
    """
    Extract features for ML anomaly detection.

    Phase 5: 6 rule-based signals.
    Phase 6: + 5 extended signals (navigation, device, IP, session, timing).
    """
    # Activity rate (normalized)
    activity_rate = interactions_count / max(total_time_seconds / 60.0, 1.0)

    # Vote entropy (reuse existing computation concept)
    total_actions = sum(action_counts.values())
    if total_actions > 0 and len(action_counts) > 1:
        entropy = 0.0
        for count in action_counts.values():
            if count > 0:
                p = count / total_actions
                entropy -= p * math.log(p)
        max_entropy = math.log(len(action_counts))
        vote_entropy = entropy / max_entropy if max_entropy > 0 else 0.5
    else:
        vote_entropy = 0.0 if total_actions > 0 else 0.5

    # Average vote value
    avg_vote = sum(votes) / max(len(votes), 1) if votes else 0.0

    return UserBehaviorFeatures(
        activity_rate=min(activity_rate, 20.0),
        vote_entropy=vote_entropy,
        consensus_deviation=consensus_deviation,
        coordination_score=coordination_score,
        location_inconsistency=location_inconsistency,
        avg_vote_value=avg_vote,
        navigation_deviation=navigation_deviation,
        device_consistency=device_consistency,
        ip_consistency=ip_consistency,
        session_continuity=session_continuity,
        timing_irregularity=timing_irregularity,
    )
