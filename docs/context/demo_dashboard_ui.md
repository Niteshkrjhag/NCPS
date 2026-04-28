1. Objective

The dashboard must allow a viewer to:

* observe system behavior over time
* compare phases (Phase 1 → Phase 5)
* understand why a decision was made
* evaluate robustness under attack


2. Layout Overview


Main Structure

------------------------------------------
| Header (controls + scenario selector)  |
------------------------------------------
| Left Panel | Center Panel | Right Panel|
------------------------------------------
| Bottom Panel (metrics + charts)        |
------------------------------------------


3. Header (Global Controls)


Controls

Scenario Selector:
    - Clean
    - Noisy
    - Coordinated Attack
    - Sybil Attack
    - Location Spoofing
Phase Selector:
    - M1 → M5
Simulation Controls:
    - Play / Pause
    - Speed slider
    - Reset
Filters:
    - show only suspicious users
    - show only high-impact posts


4. Left Panel — User Intelligence


User Table

Columns:
    user_id
    R_i (reliability)
    Exp_i
    Anom_i
    T_i (if Phase 3+)
    weight w_i


Visual Encoding

color:
    green → trusted
    red → suspicious
size:
    activity level


Interaction

click user → show:
    - activity timeline
    - anomaly breakdown
    - coordination links



5. Center Panel — Network Graph (Core Visual)


Graph View

Nodes = users
Edges = similarity (A_ij)


Node Encoding

size → weight w_i
color → anomaly score
border → trusted (T_i high)


Edge Encoding

thickness → similarity strength


Dynamic Behavior

* graph evolves over time
* clusters form during attacks


Key Demo Moment

Switch Phase 2 → Phase 3
Observe:
    coordinated cluster becomes visible
    trust redistribution happens



6. Right Panel — Post Intelligence


Post List

Columns:
    post_id
    C_j(t)
    Var_j(t)
    N_j(t)
    status (trusted / uncertain / rejected)


Selected Post Detail

When clicked:

show:
Credibility Breakdown:
    C_Bayes
    (C_ML, C_memory if Phase 5)
Signal Breakdown:
    S_j+, S_j-
    contributing users
Temporal Graph:
    C_j(t) over time
Alert Status:
    triggered / not triggered



7. Bottom Panel — Metrics & Evaluation


Tabs


Tab 1: Accuracy Metrics

Accuracy over time
Brier score



Tab 2: Attack Analysis

attack success rate
false positives
false negatives



Tab 3: Alert Quality

precision
recall
alerts triggered over time



Tab 4: System Comparison

bar chart:
M1 vs M2 vs M3 vs M4 vs M5



8. Key Visualizations


1. Credibility Timeline

x-axis → time
y-axis → C_j(t)
plot:
    true posts (green)
    false posts (red)



2. Anomaly Distribution

histogram of Anom_i



3. Trust Propagation Effect

before vs after T_i update



4. Coordination Detection

cluster highlight:
    bot group visually grouped



9. Demo Scenarios (Scripted Flow)


Demo 1: Clean System

show:
    stable credibility
    no anomalies



Demo 2: Coordinated Attack

Phase 2:
    system fooled
Phase 3:
    cluster detected
    weights drop
    credibility corrected



Demo 3: Location Relevance

Phase 4:
    alerts only to nearby users



Demo 4: Early Detection

Phase 5:
    ML predicts credibility early



10. Tech Stack Recommendation


Frontend

React + Next.js


Visualization

D3.js (graph)
Recharts / Chart.js (plots)


State Management

Redux


Backend (for demo)

FastAPI 
WebSocket for real-time updates



11. Data API Contract


Fetch State

GET /simulation/state


Response

{
  "users": [...],
  "posts": [...],
  "edges": [...],
  "metrics": {...}
}



Control Simulation

POST /simulation/control
{
  "action": "play | pause | reset",
  "scenario": "attack",
  "phase": "M3"
}



12. UX Principles (Critical)


1. Show Cause, Not Just Output

Bad:

C_j = 0.82

Good:

C_j = 0.82 because:
    trusted users ↑
    anomaly ↓



2. Make Phase Differences Obvious

toggle M2 vs M3 → instant visual change



3. Highlight Failures

show where system fails in early phases



Fix: Phase-Specific Dashboard Extensions

Phase 3 — Network Intelligence Panel (Required Additions)

Add: Trust Propagation View

Panel: Trust Flow
Show:
    R_i (base reliability)
    → T_i (after propagation)
Visualization:
    bar or node overlay:
        before vs after trust

Add: Coordination Cluster Detection

Highlight:
    clusters where S_coord > threshold
UI:
    draw bounding box or color cluster

Add: Coordination Inspector (on click)

Selected user i:
Show:
    top similar users j
    Sim(i,j)
    time alignment

Critical Toggle

Toggle:
    "Show coordination influence"
Effect:
    remove coordination term → observe failure

Phase 4 — Spatial Intelligence Panel (Required Additions)

Add: Map Visualization (Mandatory)

Map:
    users → points
    posts → markers

Encoding

User:
    color → L_i (location confidence)
    radius → influence
Post:
    circle radius → propagation radius r_j

Add: Proximity Visualization

For selected user u:
draw:
    heatmap of Prox(u,j,t)

Add: Location Confidence Breakdown

For user i:
show:
    S_gps
    S_speed
    S_source
    S_cont
    → L_i

Add: Alert Filtering Explanation

For each alert:
show:
    Prox(u,j,t)
    threshold τ_p
    decision = pass/fail

Phase 5 — ML Intelligence Panel (Required Additions)

Add: Credibility Decomposition

C_j = 
    X% C_Bayes
    Y% C_ML
    Z% C_memory

Add: ML Feature Importance

For post j:
Top features:
    keyword_score
    velocity
    early_votes

(Use simple feature weights or SHAP-style bars)

Add: Memory Neighbors View

Show:
    similar posts k
Display:
    similarity score
    their credibility

Add: ML vs Rule Comparison Toggle

Toggle:
    "Disable ML"
Observe:
    early-stage failure vs success

Add: Anomaly ML vs Rule Split

For user i:
Anom_rule
Anom_ML
Final Anom_i

Global Enhancement (All Phases)

Phase Comparison Mode (Very Important)

Split screen:
Left → Phase N
Right → Phase N+1
Compare:
    credibility
    alerts
    anomalies

Decision Trace Panel (Core Requirement)

For ANY decision:

Why was this alert triggered?
Show chain:
User signals → w_i
→ Post signals → C_j
→ Proximity → Prox
→ Final decision

What This Fix Achieves

Before

Dashboard shows results

After

Dashboard explains WHY results differ across phases


