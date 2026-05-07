"""
NCPS Central Configuration — All hyperparameters in one place.
No magic numbers anywhere else in the codebase.

Source of truth: docs/context/mathematical_formula.md, pseudo_algorithm.md
"""

from pydantic_settings import BaseSettings
from pydantic import Field


class NCPSConfig(BaseSettings):
    """Central configuration for all NCPS system parameters."""

    # ──────────────────────────────────────────────
    # Database
    # ──────────────────────────────────────────────
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/ncps",
        description="PostgreSQL connection string",
    )
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection string",
    )
    kafka_bootstrap_servers: str = Field(
        default="localhost:9092",
        description="Kafka broker address",
    )

    # ──────────────────────────────────────────────
    # Formula 1: User Reliability R_i*(t)
    # ──────────────────────────────────────────────
    lambda_r: float = Field(
        default=0.0001,
        description="Time decay constant for reliability (λ_r). "
        "Controls how fast old correct/incorrect actions lose influence. "
        "Calibrated: 0.0001 → 50% decay over ~2 hours.",
    )
    confidence_k: float = Field(
        default=0.1,
        description="Confidence growth rate (k). "
        "Controls how quickly confidence rises with more evidence.",
    )
    reliability_prior: float = Field(
        default=0.5,
        description="Default reliability for users with no history.",
    )

    # ──────────────────────────────────────────────
    # Formula 2: User Experience Exp_i(t)
    # ──────────────────────────────────────────────
    lambda_e: float = Field(
        default=0.00005,
        description="Time decay constant for experience (λ_E). "
        "Calibrated: experience decays slowly — recent actions matter but old ones still count.",
    )
    e_max: float = Field(
        default=100.0,
        description="Normalization constant for experience (E_max). "
        "Expected maximum raw experience value.",
    )

    # ──────────────────────────────────────────────
    # Formula 3: User Anomaly Anom_i(t)
    # ──────────────────────────────────────────────
    anomaly_alpha_weights: list[float] = Field(
        default=[0.25, 0.20, 0.20, 0.20, 0.15],
        description="Weights [α₁..α₅] for anomaly deviation components: "
        "[burst, entropy, consensus, coordination, location].",
    )
    anomaly_beta: float = Field(
        default=0.25,
        description="Blend factor between rule-based and ML anomaly (β). "
        "0.25 = 75% rule-based + 25% ML (Phase 5).",
    )

    # ──────────────────────────────────────────────
    # Formula 5: User Weight w_i(t)
    # (Multiplicative: T_i × (1 - Anom_i) × Exp_i)
    # No additional params — composed from above.
    # ──────────────────────────────────────────────

    # ──────────────────────────────────────────────
    # Formula 6–7: Interaction Mass & Signal
    # ──────────────────────────────────────────────
    lambda_interaction: float = Field(
        default=0.0001,
        description="Time decay for interaction contributions (λ). "
        "Calibrated: 0.0001 → votes from 2 hours ago retain ~50% weight.",
    )

    # ──────────────────────────────────────────────
    # Formula 8: Bayesian Credibility C_Bayes
    # ──────────────────────────────────────────────
    credibility_alpha0: float = Field(
        default=1.0,
        description="Prior positive belief (α₀) for Bayesian credibility.",
    )
    credibility_beta0: float = Field(
        default=1.0,
        description="Prior negative belief (β₀) for Bayesian credibility.",
    )

    # ──────────────────────────────────────────────
    # Formula 10 (Phase 1 simplified):
    # Final Credibility C_final
    # ──────────────────────────────────────────────
    credibility_alpha_ml: float = Field(
        default=0.15,
        description="Weight for ML credibility (α). "
        "0.15 in Phase 5: ML supplements but does not replace crowd evidence.",
    )
    credibility_gamma_memory: float = Field(
        default=0.10,
        description="Weight for memory credibility (γ). "
        "0.10 in Phase 5: mild nudge from historical similarity.",
    )

    # ──────────────────────────────────────────────
    # Algorithm 5: Urgency
    # ──────────────────────────────────────────────
    urgency_beta_weights: list[float] = Field(
        default=[0.4, 0.3, 0.3],
        description="Weights [β₁, β₂, β₃] for urgency: [keyword, category, velocity].",
    )
    urgency_rate_baseline: float = Field(
        default=5.0,
        description="Baseline interaction rate for velocity normalization.",
    )
    urgency_delta_t: float = Field(
        default=300.0,
        description="Time window (seconds) for velocity computation.",
    )
    urgency_keywords: dict[str, float] = Field(
        default={
            "fire": 1.0,
            "accident": 0.9,
            "urgent": 0.8,
            "help": 0.7,
            "emergency": 1.0,
            "danger": 0.9,
            "flood": 0.95,
            "earthquake": 1.0,
            "shooting": 1.0,
            "explosion": 1.0,
        },
        description="Keyword → urgency score dictionary (φ function).",
    )

    # ──────────────────────────────────────────────
    # Algorithm 6: Propagation Decision
    # ──────────────────────────────────────────────
    propagation_theta: float = Field(
        default=0.6,
        description="Minimum credibility threshold (θ) for propagation.",
    )
    propagation_n_min: float = Field(
        default=3.0,
        description="Minimum interaction mass (N_min) for propagation.",
    )
    propagation_sigma_sq: float = Field(
        default=0.25,
        description="Maximum variance (σ²) for propagation.",
    )
    propagation_t_min: float = Field(
        default=60.0,
        description="Minimum post age (seconds) before propagation.",
    )
    propagation_l_min: float = Field(
        default=0.3,
        description="Minimum spatial trust (L̄_min) for propagation.",
    )
    propagation_growth_factor: float = Field(
        default=1.5,
        description="Radius multiplier when propagation is approved.",
    )
    propagation_r_max: float = Field(
        default=50000.0,
        description="Maximum propagation radius (meters).",
    )
    propagation_r_initial: float = Field(
        default=1000.0,
        description="Initial propagation radius (meters) for new posts.",
    )

    # ──────────────────────────────────────────────
    # Algorithm 7: Alert Decision
    # ──────────────────────────────────────────────
    alert_tau_p: float = Field(
        default=0.3,
        description="Minimum proximity threshold (τ_p) for alerts.",
    )
    alert_theta: float = Field(
        default=0.5,
        description="Minimum credibility × urgency threshold (θ_alert).",
    )
    alert_rate_max: int = Field(
        default=5,
        description="Maximum alerts per user per time window (R_max).",
    )
    alert_rate_window: float = Field(
        default=3600.0,
        description="Alert rate-limiting window (seconds).",
    )

    # ──────────────────────────────────────────────
    # Spatial (simplified for MVP — full in Phase 4)
    # ──────────────────────────────────────────────
    spatial_sigma_p: float = Field(
        default=5000.0,
        description="Spatial decay parameter σ_p (meters). "
        "Controls how fast proximity drops with distance.",
    )

    # ──────────────────────────────────────────────
    # Anomaly sub-signals (MVP simplified)
    # ──────────────────────────────────────────────
    burst_window: float = Field(
        default=300.0,
        description="Time window (seconds) for burst detection (Δt).",
    )
    burst_epsilon: float = Field(
        default=0.001,
        description="Numerical stability constant (ε) for burst ratio.",
    )

    # ──────────────────────────────────────────────
    # General numerical stability
    # ──────────────────────────────────────────────
    epsilon: float = Field(
        default=1e-8,
        description="Global epsilon for numerical stability in divisions.",
    )

    # ──────────────────────────────────────────────
    # Phase 3: Graph Trust Propagation
    # Source: docs/context/phase3_system_design.md
    # ──────────────────────────────────────────────
    lambda_g: float = Field(
        default=0.5,
        description="Trust propagation strength (λ_g). "
        "0 = pure local reliability, 1 = pure network trust.",
    )
    graph_tau: float = Field(
        default=60.0,
        description="Time similarity scale (τ) in seconds for TimeSim_ij.",
    )
    graph_edge_weights: list[float] = Field(
        default=[0.4, 0.3, 0.3],
        description="Weights [w₁, w₂, w₃] for edge: [agreement, time_similarity, frequency].",
    )
    graph_max_neighbors: int = Field(
        default=50,
        description="Top-K neighbors to keep per user (sparse graph).",
    )
    graph_propagation_iterations: int = Field(
        default=20,
        description="Maximum iterations for trust propagation convergence.",
    )
    graph_convergence_epsilon: float = Field(
        default=1e-4,
        description="Convergence threshold for trust propagation.",
    )
    graph_coordination_threshold: float = Field(
        default=0.7,
        description="Similarity threshold above which coordination is suspected.",
    )

    # ──────────────────────────────────────────────
    # Phase 5: ML Augmentation
    # Source: docs/context/phase5_system_design.md
    # ──────────────────────────────────────────────
    memory_top_k: int = Field(
        default=5,
        description="Number of similar past posts to retrieve for C_memory. "
        "5 is standard for nearest-neighbor — enough signal without noise.",
    )
    ml_temperature: float = Field(
        default=1.5,
        description="Temperature for ML credibility calibration. "
        ">1 softens predictions toward 0.5, preventing overconfident ML. "
        "1.5 is conservative for potentially miscalibrated models.",
    )

    # ──────────────────────────────────────────────
    # Phase 4: Spatial-Aware Trust
    # Source: docs/context/phase4_system_design.md
    # ──────────────────────────────────────────────
    location_confidence_weights: list[float] = Field(
        default=[0.3, 0.25, 0.25, 0.2],
        description="Weights [w₁, w₂, w₃, w₄] for location confidence: "
        "[gps_accuracy, speed_plausibility, source_quality, continuity].",
    )
    location_speed_max: float = Field(
        default=340.0,
        description="Maximum plausible speed (m/s). ~340 m/s ≈ speed of sound. "
        "Movements faster than this are flagged as implausible.",
    )
    location_continuity_window: float = Field(
        default=600.0,
        description="Time window (seconds) for location continuity check. "
        "Locations within this window are expected to be consistent.",
    )
    location_gps_accuracy_threshold: float = Field(
        default=100.0,
        description="GPS accuracy threshold (meters). "
        "Readings with accuracy worse than this get reduced confidence.",
    )

    # ──────────────────────────────────────────────
    # Phase 6: Extended Signal Computation
    # Source: docs/context/input_signal.md signals 10-14
    # ──────────────────────────────────────────────
    signal_nav_kappa: float = Field(
        default=2.0,
        description="Navigation deviation scale (κ). JS-divergence mapped through exp(-D/κ).",
    )
    signal_session_delta: float = Field(
        default=1.5,
        description="Session continuity sensitivity (δ). Controls penalty for deviation from human baseline.",
    )
    signal_session_gap: float = Field(
        default=300.0,
        description="Session gap threshold (seconds). Gaps > this start a new session.",
    )
    signal_session_mu_human: float = Field(
        default=600.0,
        description="Expected human session duration (seconds). 10 minutes.",
    )
    signal_session_sigma_human: float = Field(
        default=300.0,
        description="Expected human session std (seconds). 5 minutes.",
    )
    signal_timing_sigma_sq: float = Field(
        default=100.0,
        description="Vote timing variance normalization (σ_t²). Seconds².",
    )
    signal_timing_b0: float = Field(
        default=5.0,
        description="Burstiness normalization (B_0). Burst ratio > 5× is suspicious.",
    )

    # ──────────────────────────────────────────────
    # Kafka topics
    # ──────────────────────────────────────────────
    kafka_events_topic: str = Field(
        default="ncps-events",
        description="Kafka topic for incoming events.",
    )

    class Config:
        env_prefix = "NCPS_"
        env_file = ".env"


# Singleton instance
config = NCPSConfig()
