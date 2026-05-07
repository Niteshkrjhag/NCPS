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
1. Reliability      R_i = α / (α + β)           ← time-decayed correct/incorrect actions
2. Confidence       Conf_i = 1 - exp(-k(α + β))  ← evidence strength
3. R*               R_i* = R_i × Conf_i          ← reliability × confidence
4. Experience       Exp_i = E_raw / E_max         ← normalized action count
5. Anomaly          Anom_i = Σ(α_k × D_k)        ← weighted sum of 5 deviation signals
6. Trust            T_i = graph_propagated(R_i*)  ← network-aware trust (Phase 3+)
7. User Weight      w_i = T_i × (1 - Anom_i) × Exp_i
```

```
8. Signal Mass      S_j⁺ = Σ(w_i × vote_i)      ← weighted positive/negative signals
9. Effective Mass   N_j = S_j⁺ + S_j⁻            ← total evidence weight
10. Credibility     C_Bayes = (α₀ + S⁺)/(α₀ + β₀ + N)  ← Bayesian posterior
11. Final           C_final = (1-α-γ)C_Bayes + α·C_ML + γ·C_memory
12. Variance        Var_j = Σ(w_i(v_i - C_j)²)/N  ← disagreement measure
```

### The 14 Input Signals

| # | Signal | Source | What It Detects |
|---|--------|--------|-----------------|
| 1 | R_i* | Voting history | Unreliable voters |
| 2 | Exp_i | Action count | New/inactive accounts |
| 3 | D₁ (burst) | Action rate | Rapid-fire bot behavior |
| 4 | D₂ (entropy) | Vote distribution | Always-agree/disagree patterns |
| 5 | D₃ (consensus) | Vote vs majority | Contrarian manipulation |
| 6 | D₄ (coordination) | Graph similarity | Coordinated bot groups |
| 7 | D₅ (location) | GPS movement | Location spoofing |
| 8 | T_i | Graph propagation | Network reputation |
| 9 | L_i | Location history | Location confidence |
| 10 | S_nav | Page navigation | Non-human browsing |
| 11 | S_device | Device fingerprint | Device switching |
| 12 | S_ip | IP patterns | VPN/proxy usage |
| 13 | S_session | Session duration | Automated session patterns |
| 14 | S_timing | Vote timing | Inhuman timing regularity |

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
| `lambda_r` | 0.0001 | Time decay for evidence. 50% decay in ~2 hours. |
| `confidence_k` | 0.1 | Confidence growth rate. |
| `reliability_prior` | 0.5 | Default reliability for new users. |

### User Experience (Formula 2)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `lambda_e` | 0.00005 | Time decay for experience. |
| `e_max` | 100.0 | Normalization constant. |

### Anomaly Detection (Formula 3)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `anomaly_alpha_weights` | [0.25, 0.20, 0.20, 0.20, 0.15] | Weights for [burst, entropy, consensus, coordination, location] |
| `anomaly_beta` | 0.25 | ML anomaly blend (75% rule + 25% ML) |

### Credibility (Formulas 8-10)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `credibility_alpha0` | 1.0 | Bayesian prior (positive) |
| `credibility_beta0` | 1.0 | Bayesian prior (negative) |
| `credibility_alpha_ml` | 0.15 | ML credibility weight (α) |
| `credibility_gamma_memory` | 0.10 | Memory credibility weight (γ) |

### Graph Trust (Phase 3)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `lambda_g` | 0.5 | Propagation blend (0=local only, 1=network only) |
| `graph_tau` | 60.0 | Time similarity scale (seconds) |
| `graph_edge_weights` | [0.4, 0.3, 0.3] | [agreement, time_sim, frequency] |
| `graph_max_neighbors` | 50 | Top-K neighbors per user |
| `graph_propagation_iterations` | 20 | Max convergence iterations |
| `graph_convergence_epsilon` | 1e-4 | Convergence threshold |
| `graph_coordination_threshold` | 0.7 | Coordination suspicion threshold |

### Spatial Trust (Phase 4)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `location_confidence_weights` | [0.3, 0.25, 0.25, 0.2] | [GPS accuracy, speed, source, continuity] |
| `location_speed_max` | 340.0 | Max plausible speed (m/s) — speed of sound |
| `spatial_sigma_p` | 5000.0 | Proximity decay (meters) |

### ML Augmentation (Phase 5)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `ml_temperature` | 1.5 | Calibration temperature (>1 = softer predictions) |
| `memory_top_k` | 5 | Similar posts to retrieve |

### Extended Signals (Phase 6)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `signal_nav_kappa` | 2.0 | Navigation deviation scale |
| `signal_session_delta` | 1.5 | Session continuity sensitivity |
| `signal_session_gap` | 300.0 | New session threshold (seconds) |
| `signal_timing_sigma_sq` | 100.0 | Vote timing variance normalization |

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
| **Dashboard** | `/` | Main view: metrics, user table, D3 network graph, post list, 4-tab analytics |
| **Map** | `/map.html` | Leaflet.js map with user/post markers and propagation radius circles |
| **Compare** | `/compare.html` | Phase 1→6 comparison table and bar charts |
| **User Detail** | `/user.html` | Signal bars, weight decomposition (T×(1-Anom)×Exp = w), trust propagation |
| **Post Detail** | `/post.html` | Credibility breakdown (C_Bayes + C_ML + C_memory), decision trace |

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
| `NCPS_DATABASE_URL` | `postgresql+asyncpg://...localhost/ncps` | Production only |
| `NCPS_REDIS_URL` | `redis://localhost:6379/0` | Production only |
| `NCPS_KAFKA_BOOTSTRAP_SERVERS` | `localhost:9092` | Production only |

### Simulation Settings

The simulation uses these default parameters (configurable in `simulation/runner.py`):

| Setting | Default |
|---------|---------|
| Honest users | 40 |
| Bot users | 20 (in 4 coordinated groups of 5) |
| Adversarial users | 5 |
| Noisy users | 5 |
| True posts | 30 |
| False posts | 20 |
| Time steps | 10 |
| Interactions per step | 5 |
| Center location | Delhi (28.6139°N, 77.2090°E) |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.11+, FastAPI, Uvicorn |
| **Database** | PostgreSQL (primary), Redis (cache) |
| **Streaming** | Apache Kafka (via aiokafka) |
| **ORM** | SQLAlchemy 2.0 (async) |
| **ML** | scikit-learn (Logistic Regression), scipy, numpy |
| **Frontend** | Vanilla HTML/CSS/JS, D3.js v7, Leaflet.js |
| **Design** | Dark mode, glassmorphism, Inter + JetBrains Mono fonts |

---

## License

This project is developed as part of the NCPS research initiative.
