
1. Objective of Phase 3

Upgrade system from:

“evaluate users individually”

to:

evaluate users in context of the network they form



2. What Phase 3 Adds



Core Additions

Graph construction (A_ij)
Trust propagation (T_i)
Coordination detection (group behavior)
Graph-aware anomaly amplification



Still NOT included

ML models
Full location system
Memory similarity



3. Core Idea

A user is not judged only by:

their own behavior

but also by:

who they behave like



4. Graph Construction



4.1 Nodes

Each user = node i



4.2 Edge Definition

Create edge between users if:

they interact with same posts



4.3 Edge Weight

A_{ij} =
w_1 \cdot Agree_{ij}
+
w_2 \cdot TimeSim_{ij}
+
w_3 \cdot Freq_{ij}



Agreement

Agree_{ij} =
\frac{1}{|\mathcal{P}_{ij}|}
\sum \mathbb{I}(s_i = s_j)



Time Similarity

TimeSim_{ij} =
\frac{1}{|\mathcal{P}_{ij}|}
\sum e^{-\frac{|t_i - t_j|}{\tau}}



Frequency

Freq_{ij} =
\frac{|\mathcal{P}_{ij}|}{P_{max}}





5. Normalization

\tilde{A}_{ij} =
\frac{A_{ij}}{\sum_k A_{ik} + \epsilon}





6. Trust Propagation



6.1 Formula

T_i =
\lambda_g \sum_j \tilde{A}_{ij} T_j
+
(1 - \lambda_g) R_i



6.2 Iterative Solution

T = R
repeat:
    T_new = lambda_g * A_norm * T + (1 - lambda_g) * R
until convergence





7. Updated User Weight



Phase 3 Weight

w_i =
T_i
\cdot
Exp_i
\cdot
(1 - Anom_i)



Key Change

R_i → replaced by T_i





8. Coordination Detection (Critical)



8.1 Pairwise Similarity

Sim(i,j) =
\frac{
\sum \mathbb{I}(s_i = s_j) \cdot e^{-|t_i - t_j|/\tau}
}{
|\mathcal{P}_{ij}|
}





8.2 Coordination Score

S_{coord}(i) =
\max_j Sim(i,j)





8.3 Group Detection (Optional Upgrade)

clusters = connected_components(A_ij where weight > threshold)





8.4 Coordination Penalty

Anom_i^{coord} = S_{coord}(i)



Update anomaly:

Anom_i =
1 - \exp\left(- (\alpha_1 D_{rate} + \alpha_2 D_{entropy} + \alpha_3 S_{coord})\right)





9. Pipeline (Phase 3)



Vote received
    ↓
Update user:
    R_i, Exp_i, Anom_i
    ↓
Update graph edges A_ij
    ↓
Run trust propagation → T_i
    ↓
Compute weight w_i
    ↓
Update post:
    N_j, S_j+, S_j-
    ↓
Compute:
    C_j, Var_j
    ↓
Alert decision





10. What Phase 3 Solves



Problem 1: Coordinated Bots

Many fake users voting same way

Before:

System fooled

Now:

High similarity → high anomaly → low weight





Problem 2: Trust Farming

Users behave well, then attack

Now:

Trust tied to neighbors → corrupted cluster collapses





Problem 3: Echo Chambers

Group reinforces itself

Now:

Graph normalization limits amplification





11. Backend Changes



New Table: Graph Edges

graph_edges (
    user_i TEXT,
    user_j TEXT,
    weight FLOAT,
    updated_at TIMESTAMP
)





New Computation Job

every N seconds:
    run trust propagation





12. Optimization Strategy



Sparse Graph

keep only top-K neighbors per user





Incremental Update

update edges only for users involved in new interaction





Batch Propagation

run T_i computation every 30–60 seconds





13. Hyperparameters (Phase 3)



lambda_g  → trust propagation strength
tau       → time similarity scale
alpha3    → coordination anomaly weight
K         → max neighbors per node





14. What to Test



Test 1: Coordinated Attack

10 users vote same thing simultaneously

Expect:

S_coord ↑ → Anom ↑ → w_i ↓ → attack suppressed





Test 2: Honest Cluster

real users agreeing naturally

Expect:

moderate similarity → no heavy penalty





Test 3: Mixed Network

good + bad users connected

Expect:

bad users dragged down by anomaly
good users maintain trust





15. Phase 3 Summary



Phase 2: “who you are matters”
Phase 3: “who you behave like matters”





16. System Evolution



Phase	Capability
MVP	basic credibility
Phase 2	user-aware
Phase 3	network-aware (robust)





17. Final Insight

This is the stage where your system becomes:

resistant to coordinated manipulation

Without Phase 3, any large-scale attack can still break the system.





Next Phase (Phase 4 Preview)

You will add:

Location + proximity
Spatial trust
Localized alerts

This introduces real-world context awareness.

