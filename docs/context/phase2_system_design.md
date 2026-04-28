
1. Objective of Phase 2

Upgrade system from:

“all users equal (or simple reliability)”

to:

user-aware credibility using behavior + history



2. What Phase 2 Adds



Core Additions

Time-decayed reliability
Experience score (Exp_i)
Basic anomaly detection (multi-signal, but lightweight)
Improved user weight w_i



Still NOT included

Graph trust (T_i)
ML models
Location system
Memory similarity



3. Updated User Model



3.1 Time-Decayed Reliability



Formula

R_i(t) =
\frac{\alpha_i(t)}{\alpha_i(t) + \beta_i(t)}



With Decay

alpha_i ← alpha_i * exp(-lambda_r * delta_t)
beta_i  ← beta_i  * exp(-lambda_r * delta_t)



Then update:

if vote correct:
    alpha_i += 1
else:
    beta_i += 1





3.2 Experience Score



Formula

Exp_i(t) =
\frac{\log(1 + E_i(t))}{\log(1 + E_{max})}



Simplified Computation

E_i += 1 per interaction
Exp_i = log(1 + E_i) / log(1 + E_max)





3.3 Basic Anomaly (Lightweight)

Use only 2 signals initially:



(1) Rate Deviation

rate = interactions_last_10min
baseline = avg interactions per hour
D_rate = rate / baseline





(2) Entropy (Simplified)

p_up = (#upvotes / total)
p_down = (#downvotes / total)
H = - (p_up log p_up + p_down log p_down)
D_entropy = 1 - (H / log(2))





3.4 Final Anomaly

Anom_i =
1 - \exp\left(- (\alpha_1 D_{rate} + \alpha_2 D_{entropy})\right)





4. Updated User Weight



Phase 2 Weight

w_i =
R_i(t)
\cdot
Exp_i(t)
\cdot
(1 - Anom_i)



Interpretation

Reliable × Experienced × Non-suspicious





5. Updated Post Computation



Same as MVP but using new w_i:



Interaction Mass

N_j(t) = \sum w_i \cdot e^{-\lambda (t - t_k)}





Credibility

C_j(t) =
\frac{S_j^+ + \alpha_0}{S_j^+ + S_j^- + \alpha_0 + \beta_0}





Variance

Use same simplified version.





6. Updated Alert Condition



Phase 2 Alert

Alert(j) =
\mathbb{I}\Big(
C_j > 0.75
\;\wedge\;
N_j > N_{min}
\;\wedge\;
Var_j < \sigma^2
\Big)





7. Backend Changes Required



User Table (Updated)

users (
    user_id TEXT PRIMARY KEY,
    alpha FLOAT,
    beta FLOAT,
    experience FLOAT,
    anomaly FLOAT,
    last_active TIMESTAMP
)





New Computation Step

After each vote:

update_user(i)
update_post(j)





8. Pipeline (Phase 2)



Vote received
    ↓
Update user:
    reliability
    experience
    anomaly
    ↓
Compute user weight w_i
    ↓
Update post:
    N_j, S_j+, S_j-
    ↓
Compute:
    C_j, Var_j
    ↓
Check alert





9. What Phase 2 Achieves



Compared to MVP:

Feature	MVP	Phase 2
user equality	yes	no
spam resistance	low	medium
new user influence	high	controlled
anomaly detection	none	basic





10. What You Should Test



Critical Experiments



1. Spam Burst

Many fake users vote quickly

Expect:

Anomaly ↑ → weight ↓ → credibility stable





2. New User Attack

new accounts voting

Expect:

low Exp_i → low influence





3. Honest Users

consistent correct votes

Expect:

R_i ↑ → credibility improves





11. Hyperparameters (Phase 2 Minimal Set)



lambda_r  → reliability decay
lambda    → interaction decay
alpha1    → anomaly weight (rate)
alpha2    → anomaly weight (entropy)
E_max     → experience normalization
theta     → credibility threshold





12. What NOT to Overcomplicate



Avoid:

too many anomaly signals
complex ML
perfect tuning





13. Phase 2 Summary



MVP: “what users say”
Phase 2: “who is saying it matters”





Next Phase (Phase 3 Preview)



You will add:

Graph trust propagation (T_i)
Coordination detection
Advanced anomaly signals

This is where system becomes attack-resistant at scale.





Final Insight

You now transition from:

basic system → adaptive system

