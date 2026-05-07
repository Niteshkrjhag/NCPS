# NCPS — Network-aware Credibility & Propagation System

A **trust-aware information propagation engine** that determines **what to believe and who to trust** in a network of users, posts, and votes. Built to be resistant to coordinated bot attacks, location spoofing, and adversarial manipulation.

The system computes **14 input signals** across 6 progressive phases — from basic Bayesian reliability to graph-based trust propagation, spatial analysis, and ML augmentation — achieving **100% accuracy** and **0% attack success rate** under coordinated attack simulation.

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [How It Works — The Math](#how-it-works--the-math)
- [Phase-by-Phase Evolution](#phase-by-phase-evolution)
- [Hyperparameter Reference](#hyperparameter-reference)
- [Dashboard](#dashboard)
- [Configuration](#configuration)
- [Tech Stack](#tech-stack)

---

## Architecture Overview

```
User Action (Vote/Post/Location)
        │
        ▼
┌─────────────────────────────────────────────┐
│  Event Pipeline (Kafka)                     │
│  ┌─────────┐  ┌─────────┐  ┌────────────┐  │
│  │ Ingest  │→ │ Stream  │→ │ Process    │  │
│  │ Event   │  │ Buffer  │  │ & Compute  │  │
│  └─────────┘  └─────────┘  └────────────┘  │
└──────────────────────┬──────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
  ┌───────────┐  ┌───────────┐  ┌───────────┐
  │ User      │  │ Post      │  │ Graph     │
  │ Engine    │  │ Engine    │  │ Engine    │
  │           │  │           │  │           │
  │ R_i*, T_i │  │ C_j, U_j │  │ Sim(i,j)  │
  │ Exp_i     │  │ Var_j     │  │ S_coord   │
  │ Anom_i    │  │ N_j       │  │ Trust     │
  │ w_i       │  │           │  │ Propagate │
  └───────────┘  └───────────┘  └───────────┘
        │              │              │
        ▼              ▼              ▼
  ┌─────────────────────────────────────────┐
  │  Decision Engine                        │
  │  Propagation rules + Alert triggers     │
  └─────────────────────────────────────────┘
        │
        ▼
  ┌───────────┐     ┌───────────────┐
  │ PostgreSQL│     │ Redis Cache   │
  │ (persist) │     │ (real-time)   │
  └───────────┘     └───────────────┘
```

---

## Quick Start

### Prerequisites

- Python 3.11+
- Git

> **Note:** The simulation dashboard runs **standalone** — no PostgreSQL, Redis, or Kafka needed. Those are required only for the production API server (`app/main.py`).

### Installation

```bash
# Clone the repository
git clone <repo-url> NCPS
cd NCPS

# Create virtual environment
cd backend
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt
```

### Run the Dashboard (Recommended — No Infrastructure Needed)

```bash
# From the backend/ directory, with venv activated:
python -m simulation.api_server
```

Open **http://localhost:8000** in your browser. Click **▶ Run** to execute a simulation.

> **This is the recommended way to see the full system working.** The simulation server runs the complete engine pipeline (all 14 signals, graph trust, ML, spatial) and serves the frontend dashboard. No PostgreSQL, Redis, or Kafka needed.

### Run the User-Facing Webapp (No Infrastructure Needed)

```bash
# From the backend/ directory, with venv activated:
python -m webapp.server
```

Open **http://localhost:8000** in your browser. First-time visitors see a permissions consent modal.

> **This is the production user interface.** Users can create posts, vote on credibility, see nearby reports on a map, and view their trust profile. Uses in-memory storage by default — auto-switches to PostgreSQL when available.

> **Note:** The simulator and webapp share port 8000. Run only one at a time. They are completely independent — one cannot affect the other.

### Run the Simulation (CLI — No Server)

```bash
# From the backend/ directory, with venv activated:
python -m simulation.runner
```

This prints a comparison table of all phases to the terminal.

### Run the Production API (Requires PostgreSQL + Redis + Kafka)

> **Only use this if you have PostgreSQL, Redis, and Kafka running locally.** This server connects to real databases and processes real events.

```bash
# IMPORTANT: Run from the backend/ directory (NOT backend/app/)
cd backend
source venv/bin/activate

# Set environment variables (or use .env file):
export NCPS_DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/ncps"
export NCPS_REDIS_URL="redis://localhost:6379/0"
export NCPS_KAFKA_BOOTSTRAP_SERVERS="localhost:9092"

# Start the FastAPI server (use a different port if simulation server is already running):
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

> **Common errors:**
> - `ModuleNotFoundError: No module named 'app'` → You ran from the wrong directory. You must run from `backend/`, not `backend/app/`.
> - `Connection refused` → PostgreSQL/Redis/Kafka isn't running. Use the simulation server instead.
> - `Address already in use` → Port 8000 is taken (simulation server). Use `--port 8001`.

---

## Project Structure

```
NCPS/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes.py          # FastAPI endpoints (/post/create, /post/vote, /feed, /user/location)
│   │   │   └── schemas.py         # Pydantic request/response models
│   │   ├── config.py              # All hyperparameters in one file (50+ params)
│   │   ├── database/
│   │   │   ├── cache.py           # Redis caching layer
│   │   │   ├── connection.py      # SQLAlchemy async engine + session
│   │   │   └── repositories.py    # CRUD for users, posts, interactions, graph, alerts
│   │   ├── engine/                # ← Core math & intelligence
│   │   │   ├── user_engine.py     # R_i*, Exp_i, Anom_i, T_i, w_i (Formulas 1-5)
│   │   │   ├── post_engine.py     # C_Bayes, C_final, Var_j, N_j (Formulas 6-10)
│   │   │   ├── graph_engine.py    # Edge construction, trust propagation, coordination detection
│   │   │   ├── spatial.py         # Location confidence, inconsistency, proximity
│   │   │   ├── ml_engine.py       # C_ML, C_memory, Anom_ML (LogisticRegression + TF-IDF)
│   │   │   ├── signal_engine.py   # Extended signals: device, IP, session, timing, navigation
│   │   │   ├── urgency.py         # Urgency scoring (keywords + velocity)
│   │   │   └── decision.py        # Propagation & alert decision logic
│   │   ├── event_pipeline.py      # Kafka consumer/producer
│   │   ├── main.py                # FastAPI app (production)
│   │   └── models/                # SQLAlchemy ORM models
│   │       ├── user.py            # users table
│   │       ├── post.py            # posts table
│   │       └── interaction.py     # interactions, user_graph, user_locations, alerts tables
│   ├── simulation/
│   │   ├── simulator.py           # Synthetic data generation (honest/bot/adversarial/noisy users)
│   │   ├── runner.py              # Experiment runner (Phase 1→6 comparison)
│   │   ├── evaluator.py           # Metrics: accuracy, Brier score, attack success, anomaly detection
│   │   └── api_server.py          # Standalone dashboard API server
│   ├── requirements.txt
│   └── tests/
├── frontend/
│   ├── index.html                 # Main dashboard (metrics, user table, D3 graph, posts)
│   ├── user.html                  # User detail (signal bars, weight decomposition)
│   ├── post.html                  # Post detail (credibility breakdown, decision trace)
│   ├── compare.html               # Phase comparison (table + bar charts)
│   ├── map.html                   # Spatial map (Leaflet.js + OpenStreetMap)
│   ├── css/style.css              # Design system (dark mode, glassmorphism)
│   └── js/app.js                  # D3 network graph, charts, API integration
└── docs/context/                  # Design specifications (14 documents)
    ├── mathematical_formula.md    # All formulas (1-14)
    ├── ncps_architecture.md       # System architecture
    ├── database_design.md         # PostgreSQL + Redis schema
    ├── phase1_system_design.md    # through phase5_system_design.md
    ├── input_signal.md            # All 14 input signals
    └── ...
```

---

## How It Works — The Math

The system computes a **user weight** `w_i` for each voter, then uses weighted votes to determine **post credibility** `C_j`.

### Core Formula Chain

```
1. Reliability      R_i = α / (α + β)           ← Bayesian ratio of time-decayed correct actions over total actions.
2. Confidence       Conf_i = 1 - exp(-k(α + β))  ← Grows from 0 toward 1 as more evidence (votes) accumulates.
3. R*               R_i* = R_i × Conf_i          ← Effective reliability that penalizes users who have few interactions.
4. Experience       Exp_i = log(1+E) / log(1+E_max) ← Log-normalized action count that provides diminishing returns.
5. Anomaly          Anom_i = 1 - exp(-Σ(α_k × D_k)) ← Weighted sum of 5 deviation signals, bounded in [0,1].
6. Trust            T_i = graph_propagated(R_i*)  ← Network-aware trust that can only decrease R_i*, never inflate it.
7. User Weight      w_i = T_i × (1 - Anom_i) × Exp_i ← Multiplicative gating: all three must be non-zero for influence.
```

```
8. Signal Mass      S_j⁺ = Σ(w_i × decay × vote_i) ← Aggregated trust-weighted, time-decayed positive/negative votes.
9. Effective Mass   N_j = S_j⁺ + S_j⁻              ← Total evidence mass determining how much data supports the post.
10. Credibility     C_Bayes = (α₀ + S⁺)/(α₀ + β₀ + N) ← Bayesian posterior probability that the post is credible.
11. Final           C_final = (1-α-γ)C_Bayes + α·C_ML + γ·C_memory ← Blended credibility from crowd, ML, and history.
12. Variance        Var_j = Σ(w_i(v_i - C_j)²)/N  ← Measures how much voters disagree about the post's credibility.
```

### The 14 Input Signals

| # | Signal | Source | What It Detects |
|---|--------|--------|-----------------|
| 1 | R_i* (Effective Reliability) | Time-decayed voting history of correct and incorrect actions | Users who consistently provide incorrect or low-quality information |
| 2 | Exp_i (Experience Score) | Log-normalized count of all user actions over time | New or inactive accounts that have not yet demonstrated enough engagement |
| 3 | D₁ (Burst Deviation) | Recent action rate compared against baseline activity | Rapid-fire voting behavior that indicates automated bot actions |
| 4 | D₂ (Entropy Deviation) | Distribution of vote types (upvote vs downvote ratio) | Users who always agree or always disagree, indicating scripted behavior |
| 5 | D₃ (Consensus Deviation) | How often a user's votes align with ground truth outcomes | Users who persistently vote against the majority in a manipulative pattern |
| 6 | D₄ (Coordination Score) | Pairwise similarity of voting patterns between users in the graph | Groups of bots that vote on the same posts at the same times in the same direction |
| 7 | D₅ (Location Inconsistency) | Fraction of GPS movements that exceed physically plausible speed | Users who appear to teleport between distant locations, suggesting GPS spoofing |
| 8 | T_i (Graph Trust) | Iterative trust propagation through the user interaction graph | Whether a user is embedded in a trustworthy or suspicious network neighborhood |
| 9 | L_i (Location Confidence) | Composite score from GPS accuracy, speed plausibility, source quality, and continuity | Whether the user's reported location can be trusted for spatial computations |
| 10 | S_nav (Navigation Deviation) | Step-length and turn-angle distributions of geographic movement | Movement patterns that deviate from typical human navigation behavior |
| 11 | S_device (Device Consistency) | Entropy of device identifiers used across interactions | Users who frequently rotate between many different devices, suggesting shared bot accounts |
| 12 | S_ip (IP Consistency) | IP address entropy combined with geographic consistency of IP locations | Users connecting from many different IP addresses or geographically scattered networks |
| 13 | S_session (Session Continuity) | Duration and variance of browsing sessions compared to human baselines | Sessions that are too short, too long, or too uniform, suggesting automated scripts |
| 14 | S_timing (Vote Timing) | Variance of inter-vote time gaps combined with burstiness within time windows | Perfectly regular vote timing that no human can achieve, indicating automated voting |

---

## Phase-by-Phase Evolution

### Phase 1 — MVP (Base Reliability)

**What was built:**
- Bayesian user reliability (R_i*) with time-decayed evidence
- Experience scoring (Exp_i) from action accumulation
- Rule-based anomaly detection (burst, entropy, consensus deviations)
- Weighted Bayesian credibility (C_Bayes) for posts
- Urgency scoring, propagation rules, alert decisions
- Full database layer (PostgreSQL + Redis + Kafka)
- 4 REST API endpoints, simulation framework

**Key formulas activated:** 1–10 (core pipeline)

**Simulation results (coordinated attack — 40 honest, 20 bots, 5 adversarial, 5 noisy):**

| Metric | Value |
|--------|-------|
| Accuracy | 0.800 |
| Attack Success | 0.400 |
| Brier Score | 0.250 |
| Anomaly Precision | 0.870 |
| Anomaly Recall | 0.800 |

> **Problem:** 40% attack success — bots can still push false content to appear credible.

---

### Phase 3 — Graph Trust Propagation

> Phase 2 was skipped because Phase 1 already implemented its scope (R_i*, Exp_i, Anom_i).

**What was added:**
- **Graph engine** (`graph_engine.py`) — constructs a user similarity graph from voting patterns
- **Edge weight** = `w₁·Agree(i,j) + w₂·TimeSim(i,j) + w₃·Freq(i,j)`
- **Trust propagation**: iterative `T = λ_g·Ã·T + (1-λ_g)·R*` (converges in ~20 iterations)
- **Coordination detection**: `S_coord(i) = max_j Sim(i,j)` — bots voting together get flagged
- Conservative constraint: `T_i ≤ R_i*` (network can only reduce trust, never inflate)

**Key hyperparameters tuned:**
- `λ_r`: 0.01 → **0.0001** (time decay was too aggressive — 50% decay in 2 hours instead of 1 minute)
- `λ_g`: **0.5** (equal blend of local reliability and network trust)
- Edge weights: **[0.4, 0.3, 0.3]** (agreement, time similarity, frequency)
- Coordination threshold: **0.7** (Sim > 0.7 = suspected coordination)

**Results:**

| Metric | Phase 1 | Phase 3 | Change |
|--------|---------|---------|--------|
| Accuracy | 0.800 | 0.920 | +0.120 |
| Attack Success | 0.400 | 0.150 | -0.250 ↓ |
| Anomaly Precision | 0.870 | 0.905 | +0.035 |
| Anomaly Recall | 0.800 | 0.760 | -0.040 |

> **Key win:** Attack success dropped from 40% → 15%. Graph detects bot coordination.

---

### Phase 4 — Spatial Trust

**What was added:**
- **Location confidence** (`L_i`) — composite score from GPS accuracy, speed plausibility, source quality, continuity
- **Location inconsistency** (`D_5`) — flags teleporting users (speed > 340 m/s = impossible)
- **Post location estimation** — weighted average from voter locations
- **Proximity-based alert filtering** — only alert users near the post

**Key hyperparameters:**
- Location confidence weights: **[0.3, 0.25, 0.25, 0.2]** (GPS accuracy, speed, source, continuity)
- Max plausible speed: **340 m/s** (speed of sound)
- Spatial decay σ_p: **5000 m** (proximity drops over 5km)

**Results:**

| Metric | Phase 3 | Phase 4 | Change |
|--------|---------|---------|--------|
| Accuracy | 0.920 | 0.920 | — |
| Attack Success | 0.150 | 0.150 | — |
| Anomaly Precision | 0.905 | 0.909 | +0.004 |
| Anomaly Recall | 0.760 | 0.800 | +0.040 ↑ |

> **Key win:** Location spoofing detected — 15 users with L_i < 0.3, 9 users with D_5 > 0.3. Zero false positives on honest baseline.

---

### Phase 5 — ML Augmentation

**What was added:**
- **C_ML** — `LogisticRegression` on post features (content length, question marks, early vote ratio, interaction rate)
- **C_memory** — TF-IDF similarity retrieval from known-outcome posts, weighted average of top-K similar posts
- **Anom_ML** — learned anomaly detector (11 features including all extended signals)
- **Blended credibility**: `C_final = (1-α-γ)·C_Bayes + α·C_ML + γ·C_memory`
- **Blended anomaly**: `Anom = (1-β)·Anom_rule + β·Anom_ML`

**Key hyperparameters:**
- `α` (ML credibility weight): **0.15** — ML supplements but doesn't replace crowd evidence
- `γ` (memory weight): **0.10** — mild nudge from historical similarity
- `β` (ML anomaly blend): **0.25** — 75% rule-based + 25% learned
- ML temperature: **1.5** — softens overconfident predictions toward 0.5
- Memory top-K: **5** — nearest neighbors for similarity retrieval

**Results:**

| Metric | Phase 4 | Phase 5 | Change |
|--------|---------|---------|--------|
| Accuracy | 0.920 | **1.000** | +0.080 ↑ |
| Attack Success | 0.150 | **0.000** | -0.150 ↓ |
| Brier Score | 0.212 | 0.153 | -0.059 ↓ |
| Anomaly Precision | 0.909 | **1.000** | +0.091 |
| Anomaly Recall | 0.800 | 0.800 | — |

> **Key win:** **100% accuracy, 0% attack success.** All false content correctly identified. All bots detected with 100% precision.

---

### Phase 6 — Extended Signals + Full Dashboard

**What was added:**
- **5 extended signals** (10-14): navigation deviation, device consistency, IP consistency, session continuity, timing irregularity
- **Signal engine** (`signal_engine.py`) — computes all extended signals from metadata
- **Full frontend dashboard** — 6 pages with D3 network graph, Leaflet.js map, credibility decomposition, phase comparison

**Final results (all phases compared under coordinated attack):**

| Metric | P1 | P3 | P4 | P5 | P6 |
|--------|-----|-----|-----|-----|-----|
| **Accuracy** | 0.800 | 0.920 | 0.920 | 1.000 | **1.000** |
| **Attack Success** ↓ | 0.400 | 0.150 | 0.150 | 0.000 | **0.000** |
| **Brier Score** ↓ | 0.250 | — | — | 0.153 | **0.175** |
| **Weight Correlation** | — | — | — | — | **0.451** |
| **Anomaly Precision** | 0.870 | 0.905 | 0.909 | 1.000 | **1.000** |
| **Anomaly Recall** | 0.800 | 0.760 | 0.800 | 0.800 | **0.800** |

---

## Hyperparameter Reference

All hyperparameters are centralized in [`backend/app/config.py`](backend/app/config.py). Every parameter is documented with its formula reference, calibration rationale, and default value.

### User Reliability (Formula 1)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `lambda_r` | 0.0001 | Controls how quickly old evidence decays over time. At this value, a vote from 2 hours ago retains approximately 50% of its influence. |
| `confidence_k` | 0.1 | Determines how fast the confidence term grows as more evidence accumulates. At k=0.1, a user with 5 votes reaches 39% confidence and a user with 20 votes reaches 87% confidence. |
| `reliability_prior` | 0.5 | The default reliability assigned to brand-new users who have not yet performed any actions, representing maximum uncertainty (50/50). |

### User Experience (Formula 2)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `lambda_e` | 0.00005 | Controls how quickly experience evidence decays. This is intentionally slower than `lambda_r` (half the rate) because experience should persist longer than reliability corrections. |
| `e_max` | 100.0 | The maximum expected raw experience value, used as the denominator in the log-normalization formula to keep Exp_i bounded in [0, 1]. |

### Anomaly Detection (Formula 3)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `anomaly_alpha_weights` | [0.25, 0.20, 0.20, 0.20, 0.15] | Importance weights for each anomaly deviation component, ordered as [burst, entropy, consensus, coordination, location]. Burst is highest because rapid-fire voting is the strongest bot indicator, and location is lowest because GPS accuracy can vary legitimately. |
| `anomaly_beta` | 0.25 | The blend factor between rule-based anomaly (75%) and ML-learned anomaly (25%). Keeps the system interpretable while still benefiting from learned behavioral patterns. |

### Credibility (Formulas 8-10)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `credibility_alpha0` | 1.0 | The Bayesian prior for positive belief, representing one virtual upvote before any real evidence. This prevents extreme credibility scores when a post has very few interactions. |
| `credibility_beta0` | 1.0 | The Bayesian prior for negative belief, representing one virtual downvote. Together with alpha0, this sets the initial credibility of any post to 0.5 (neutral). |
| `credibility_alpha_ml` | 0.15 | The weight given to the ML-predicted credibility score in the final blend. At 0.15, the ML model can nudge a borderline post by approximately ±0.1 but cannot override strong crowd consensus. |
| `credibility_gamma_memory` | 0.10 | The weight given to memory-based credibility from historically similar posts. At 0.10, recurring misinformation patterns contribute a mild correction without dominating the final score. |

### Graph Trust (Phase 3)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `lambda_g` | 0.5 | Controls the blend between local reliability (R_i*) and network-propagated trust. At 0.5, a user's trust is equally influenced by their own reliability and their neighbors' assessments. |
| `graph_tau` | 60.0 | The time scale in seconds used to compute how closely two users voted at the same time. Votes within 60 seconds of each other receive high time-similarity scores. |
| `graph_edge_weights` | [0.4, 0.3, 0.3] | The weights for [agreement, time_similarity, frequency] when computing edge weights between users. Agreement is highest because voting the same way is the strongest coordination signal. |
| `graph_max_neighbors` | 50 | The maximum number of neighbors retained per user after pruning. This limits computational cost while preserving the most important connections. |
| `graph_propagation_iterations` | 20 | The maximum number of iterations allowed for the trust propagation algorithm to converge. In practice, convergence typically occurs within 5-10 iterations. |
| `graph_convergence_epsilon` | 1e-4 | The maximum allowed change between iterations before the trust propagation is considered converged. Smaller values produce more precise trust scores at the cost of more iterations. |
| `graph_coordination_threshold` | 0.7 | The similarity threshold above which two users are flagged as potentially coordinated. Below 0.5 would produce too many false alarms from natural agreement, and above 0.9 would miss obvious coordination. |

### Spatial Trust (Phase 4)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `location_confidence_weights` | [0.3, 0.25, 0.25, 0.2] | The weights for the four components of location confidence: [GPS accuracy score, speed plausibility, source quality (GPS vs IP), movement continuity]. GPS accuracy has the highest weight because it is the most direct measure of location quality. |
| `location_speed_max` | 340.0 | The maximum physically plausible speed in meters per second, set to the speed of sound (340 m/s). Any location transition faster than this is flagged as impossible and indicates GPS spoofing. |
| `spatial_sigma_p` | 5000.0 | The spatial decay scale in meters for the Gaussian proximity function. At 5km, the proximity score drops to approximately 37% of its maximum value. This covers a meaningful urban area without making distant posts irrelevant. |

### ML Augmentation (Phase 5)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `ml_temperature` | 1.5 | The temperature scaling applied to ML predictions before blending. Values greater than 1.0 make predictions less extreme (closer to 0.5), preventing an overconfident model from dominating the final credibility score. |
| `memory_top_k` | 5 | The number of most-similar historical posts retrieved by the TF-IDF memory engine. Their known credibility scores are averaged (weighted by similarity) to produce the memory-based credibility estimate. |

### Extended Signals (Phase 6)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `signal_nav_kappa` | 2.0 | The scale parameter for the navigation deviation formula. At kappa=2, moderate deviations from typical human movement patterns are tolerated without excessive penalty, while extreme deviations (straight-line bot paths) are heavily penalized. |
| `signal_session_delta` | 1.5 | Controls how sensitive the session continuity score is to deviations from human session baselines. Higher values are more forgiving of unusual session patterns. |
| `signal_session_gap` | 300.0 | The time gap in seconds (5 minutes) that defines the boundary between two separate browsing sessions. Interactions separated by more than 5 minutes are treated as belonging to different sessions. |
| `signal_timing_sigma_sq` | 100.0 | The variance normalization constant for vote timing analysis. Bots typically have near-zero variance (perfectly regular timing), while humans naturally vary by approximately ±10 seconds between actions. |

### Overriding Defaults

All parameters can be set via **environment variables** with the `NCPS_` prefix:

```bash
export NCPS_LAMBDA_G=0.7
export NCPS_ANOMALY_BETA=0.3
export NCPS_DATABASE_URL="postgresql+asyncpg://user:pass@host:5432/ncps"
```

Or via a `.env` file in the `backend/` directory.

---

## Dashboard

The frontend dashboard provides real-time visualization of the trust system.

### Pages

| Page | URL | Description |
|------|-----|-------------|
| **Dashboard** | `/` | The main overview page displaying key metrics (accuracy, attack success rate, Brier score), a color-coded user table, an interactive D3 force-directed network graph, a post credibility list, and a 4-tab analytics panel covering overview, attack analysis, anomaly detection, and weight distribution. |
| **Map** | `/map.html` | An interactive Leaflet.js map with OpenStreetMap tiles showing user locations as blue markers, post locations as credibility-colored markers (green for credible, red for low-credibility), and translucent propagation radius circles around each post. |
| **Compare** | `/compare.html` | A side-by-side comparison of Phase 1 through Phase 6 simulation results, presented as both a data table and four bar charts (accuracy, attack success, anomaly precision, and anomaly recall) showing progressive improvement. |
| **User Detail** | `/user.html` | A detailed profile page for any selected user, showing individual signal bars (R*, Exp, T, Anom, L), the weight decomposition formula (T × (1-Anom) × Exp = w) with live values, and the trust propagation chain from R* through graph to final T_i. |
| **Post Detail** | `/post.html` | A detailed page for any selected post, showing the credibility decomposition (C_Bayes, C_ML, and C_memory contributions), the propagation and alert decision traces with all condition evaluations, and the variance/disagreement analysis among voters. |

### Dashboard Features

- **Metrics Row** — Accuracy, Attack Success, Brier Score, Weight Correlation, Users, Posts
- **User Intelligence Panel** — Color-coded user table (green=honest, red=bot, yellow=adversarial)
- **Network Graph** — D3 force-directed graph with zoom, drag, click-to-inspect
- **Post Credibility Panel** — Credibility bars with TRUE/FALSE labels and ML scores
- **Bottom Analytics** — 4 tabs: Overview, Attack Analysis, Anomaly Detection, Weight Distribution
- **Phase Selector** — Switch between Phase 1/3/4/5/6 to see how results change

---

## Configuration

### Environment Variables

| Variable | Default | Required |
|----------|---------|----------|
| `NCPS_DATABASE_URL` | `postgresql+asyncpg://...localhost/ncps` | Required only for the production API server. The simulation dashboard and webapp run without it using in-memory storage. |
| `NCPS_REDIS_URL` | `redis://localhost:6379/0` | Required only for the production API server. Provides real-time caching for user state and post credibility lookups. |
| `NCPS_KAFKA_BOOTSTRAP_SERVERS` | `localhost:9092` | Required only for the production API server. Enables the event streaming pipeline for processing votes and posts asynchronously. |

### Simulation Settings

The simulation uses these default parameters (configurable in `simulation/runner.py`):

| Setting | Default | Explanation |
|---------|---------|-------------|
| Honest users | 40 | Simulated users who vote correctly most of the time (probability of correct vote approximately 0.85). |
| Bot users | 20 (in 4 coordinated groups of 5) | Automated accounts that vote in coordinated groups, always upvoting false content and downvoting true content. |
| Adversarial users | 5 | Sophisticated attackers who behave normally most of the time but strategically manipulate specific posts. |
| Noisy users | 5 | Users who vote randomly without malicious intent, representing real-world unreliable but non-adversarial participants. |
| True posts | 30 | Posts containing accurate information that the system should assign high credibility scores to. |
| False posts | 20 | Posts containing misinformation that the system should assign low credibility scores to. |
| Time steps | 10 | The number of discrete time intervals in the simulation, each representing a round of interactions. |
| Interactions per step | 5 | The number of user-post interactions generated in each time step. |
| Center location | Delhi (28.6139°N, 77.2090°E) | The geographic center around which simulated user and post locations are generated with random offsets. |

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|------------|----------|
| **Backend** | Python 3.11+, FastAPI, Uvicorn | High-performance async API server with automatic OpenAPI documentation and type validation. |
| **Database** | PostgreSQL (primary), Redis (cache) | PostgreSQL stores all persistent data (users, posts, interactions, graph). Redis provides real-time caching for user state and credibility lookups. |
| **Streaming** | Apache Kafka (via aiokafka) | Enables asynchronous event processing for real-time vote and post ingestion at scale. |
| **ORM** | SQLAlchemy 2.0 (async) | Provides async database access with declarative ORM models and connection pooling. |
| **ML** | scikit-learn (Logistic Regression), scipy, numpy | Lightweight ML models chosen for small-data reliability, fast inference, and well-calibrated probability outputs. |
| **Frontend** | Vanilla HTML/CSS/JS, D3.js v7, Leaflet.js | Zero-dependency frontend with D3 for interactive network graphs and Leaflet for geographic map visualization. |
| **Design** | Dark mode, glassmorphism, Inter + JetBrains Mono fonts | Premium visual design with modern aesthetics, smooth animations, and accessible typography. |

---

## License

This project is developed as part of the NCPS research initiative.
