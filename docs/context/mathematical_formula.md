mathematical_formula — Formula 1

User Reliability with Confidence Adjustment



Final Formula

R_i^*(t) = \left( \frac{\alpha_i(t)}{\alpha_i(t) + \beta_i(t)} \right) \cdot \left(1 - e^{-k(\alpha_i(t) + \beta_i(t))} \right)



Interpretation

This formula computes the effective reliability of user i at time t, combining:

* correctness history (Bayesian estimate)
* confidence based on amount of evidence



Components Breakdown



1. Bayesian Reliability Estimate

R_i(t) = \frac{\alpha_i(t)}{\alpha_i(t) + \beta_i(t)}

Represents:

Probability that user i provides correct information.



2. Confidence Term

Conf_i(t) = 1 - e^{-k(\alpha_i(t) + \beta_i(t))}

Represents:

How much evidence we have about the user.



3. Final Reliability

R_i^*(t) = R_i(t) \cdot Conf_i(t)

Ensures:

* new users → low influence
* experienced users → higher influence



Variable Definitions



User Evidence Variables

* \alpha_i(t): time-decayed count of correct actions
* \beta_i(t): time-decayed count of incorrect actions



Decay-Based Computation

\alpha_i(t) = \sum_{k} e^{-\lambda_r (t - t_k)} \cdot \mathbb{I}(\text{correct})

\beta_i(t) = \sum_{k} e^{-\lambda_r (t - t_k)} \cdot \mathbb{I}(\text{incorrect})



Other Variables

* k: confidence growth rate (hyperparameter)
* t_k: timestamp of interaction
* \lambda_r: time decay constant



Properties

* R_i^*(t) \in [0,1]
* monotonically increases with correct evidence
* penalizes low sample size
* adapts over time



Why This Formulation Is Correct

This avoids:

* overconfidence from few interactions
* static reputation issues
* dominance of outdated behavior



Usage in System

This value feeds into:

w_i(t) = T_i(t) \cdot (1 - Anom_i(t)) \cdot Exp_i(t)



Pseudo Insight

Reliability = correctness × confidence



mathematical_formula — Formula 2

User Experience Score



Final Formula

Exp_i(t) =
\frac{\log\left(1 + E_i(t)\right)}
{\log\left(1 + E_{\max}\right)}



Interpretation

This formula computes the experience level of user i at time t, representing:

how much meaningful participation the user has accumulated over time.

It ensures:

* diminishing returns (prevents domination by extremely active users)
* bounded output in [0,1]
* robustness to spam or burst activity



Core Quantity

E_i(t) = \sum_{k \in \mathcal{V}_i}
e^{-\lambda_E (t - t_k)} \cdot q_k



Component Breakdown



1. Activity Set

* \mathcal{V}_i: set of all actions performed by user i

Each action k could be:

* vote
* post
* interaction



2. Time Decay Term

e^{-\lambda_E (t - t_k)}

* reduces importance of old actions
* ensures recent activity matters more



3. Quality Weight

* q_k \in [0,1]: quality score of action k

Typical choices:

* q_k = 1 for valid interaction
* or:
    q_k = \mathbb{I}(\text{correct action})



4. Raw Experience

E_i(t)

Represents:

total time-weighted, quality-adjusted activity of user i



5. Log Normalization

Exp_i(t) =
\frac{\log(1 + E_i(t))}{\log(1 + E_{\max})}



Variable Definitions



* E_i(t): raw experience accumulation
* E_{\max}: normalization constant (maximum expected experience)
* \lambda_E: decay rate for experience
* t_k: timestamp of action
* q_k: quality weight



Properties



* Exp_i(t) \in [0,1]
* monotonic with respect to activity
* diminishing returns due to log scaling
* resistant to spam bursts



Why Log Scaling Is Necessary

Without log:

* highly active users dominate
* system becomes biased

With log:

* early experience matters more
* later growth slows



Behavior Summary



User Type	Behavior
New user	Exp_i \approx 0
Moderate user	grows quickly
Heavy user	saturates near 1



Usage in System

Feeds into:

w_i(t) = T_i(t) \cdot (1 - Anom_i(t)) \cdot Exp_i(t)



Pseudo Insight

Experience = time-decayed activity with diminishing returns




mathematical_formula — Formula 3

User Anomaly Score



Final Formula

Anom_i(t) =
(1 - \beta)\,Anom_i^{rule}(t)
+
\beta\,Anom_i^{ML}(t)



Rule-Based Core

Anom_i^{rule}(t) =
1 - \exp\left(
- \sum_{m=1}^{5} \alpha_m\, D_m(i,t)
\right)



ML Component

Anom_i^{ML}(t) = \sigma\big(f(x_i(t))\big)



Interpretation

This formula measures:

how much user i’s behavior deviates from expected human behavior

It combines:

* interpretable rule-based deviations
* learned behavioral patterns (ML)



Component Breakdown



1. Aggregation Mechanism

1 - \exp(-x)

Ensures:

* output bounded in [0,1]
* smooth growth
* no hard thresholds



2. Deviation Components D_m(i,t)



(1) Temporal Burst Deviation

D_1(i,t) =
\frac{V_i^{window}(t)}{\mu_i^{baseline}(t) + \epsilon}



Variables

* V_i^{window}(t): activity count in recent window
* \mu_i^{baseline}(t): long-term average activity
* \epsilon: small constant



Meaning

Detects:

sudden spikes in activity



(2) Behavioral Entropy Deviation

H_i(t) =
- \sum_{a \in \mathcal{A}} p_i(a,t)\,\log p_i(a,t)

D_2(i,t) =
1 - \frac{H_i(t)}{\log |\mathcal{A}|}



Variables

* \mathcal{A}: set of possible actions
* p_i(a,t): probability of action a



Meaning

* low entropy → repetitive behavior → suspicious



(3) Consensus Deviation

D_3(i,t) =
1 - \frac{1}{N_i(t)}
\sum_{k}
\mathbb{I}(s_k = y_{j_k})



Variables

* s_k: user vote
* y_{j_k}: final truth of post
* N_i(t): total interactions



Meaning

* persistent disagreement → suspicious



(4) Coordination Similarity

D_4(i,t) =
\max_{j \in \mathcal{N}(i)}
Sim(i,j,t)



Similarity Function

Sim(i,j,t) =
\frac{1}{|\mathcal{P}_{ij}|}
\sum_{k \in \mathcal{P}_{ij}}
\mathbb{I}(s_{i,k} = s_{j,k})
\cdot
\exp\left(-\frac{|t_{i,k} - t_{j,k}|}{\tau}\right)



Meaning

Detects:

coordinated users acting together



(5) Location Inconsistency

D_5(i,t) =
\frac{N_{implausible}}{N_{movements}}



Meaning

* high value → unrealistic movement → spoofing



3. ML Feature Vector

x_i(t) =
[
r_{rate},
r_{timing},
r_{nav},
r_{div},
r_{ip},
r_{fp}
]



ML Output

Anom_i^{ML}(t) = \frac{1}{1 + e^{-f(x_i)}}



4. Variable Definitions



* \alpha_m: importance weights for each deviation
* \beta: blending factor between rule-based and ML
* \tau: time alignment parameter
* \mathcal{N}(i): neighboring users
* \mathcal{P}_{ij}: shared posts
* y_j: ground truth label



5. Properties



* Anom_i(t) \in [0,1]
* smooth and differentiable
* robust to noise
* captures multiple attack patterns



6. Behavior Interpretation



Value	Meaning
~0	normal behavior
~0.5	suspicious
~1	highly anomalous



7. Why This Formulation Is Strong



* no single signal dominates
* resistant to evasion
* interpretable + extensible
* compatible with real-time updates



8. Usage in System



w_i(t) =
T_i(t)
\cdot (1 - Anom_i(t))
\cdot Exp_i(t)



Pseudo Insight

Anomaly = aggregated deviation from human behavior


Proceeding with the next dependent component.



mathematical_formula — Formula 4

Graph-Based Trust Propagation



Final Formula

T^{(k+1)}(t) =
\lambda_g \,\tilde{A}(t)\, T^{(k)}(t)
+
(1 - \lambda_g)\, R^*(t)



Converged Trust

T(t) = \lim_{k \to \infty} T^{(k)}(t)



Interpretation

This formula computes the network-adjusted trust score of users, where:

trust is influenced both by individual reliability and by neighboring users in the interaction graph.



Component Breakdown



1. Trust Vector

T(t) =
\begin{bmatrix}
T_1(t) \\
T_2(t) \\
\vdots \\
T_n(t)
\end{bmatrix}



Meaning

* T_i(t): final trust score of user i



2. Base Reliability Vector

R^*(t) =
\begin{bmatrix}
R_1^*(t) \\
R_2^*(t) \\
\vdots \\
R_n^*(t)
\end{bmatrix}



Meaning

* reliability computed from Formula 1



3. Normalized Adjacency Matrix

\tilde{A}_{ij}(t) =
\frac{A_{ij}(t)}{\sum_{k} A_{ik}(t) + \epsilon}



Meaning

* row-normalized matrix
* each row sums to 1



Interpretation

\tilde{A}_{ij}(t)

represents:

fraction of influence user i assigns to user j



4. Iterative Propagation Term

\tilde{A}(t)\,T^{(k)}(t)



Meaning

* aggregates trust from neighbors
* weighted by similarity



5. Damping / Anchor Term

(1 - \lambda_g)\,R^*(t)



Meaning

* prevents drift
* ensures trust remains grounded in observed behavior



6. Mixing Parameter

* \lambda_g \in (0,1)



Interpretation

Value	Behavior
small	trust mostly individual
large	trust heavily network-influenced



Initialization

T^{(0)}(t) = R^*(t)



Convergence Condition

\|T^{(k+1)}(t) - T^{(k)}(t)\| < \epsilon



Properties



* T_i(t) \in [0,1]
* converges under damping
* stable against noise
* incorporates global structure



Why This Formulation Works


This formulation ensures:

* trusted users reinforce each other
* isolated malicious clusters cannot dominate
* reliability is corrected using relational context



Behavior Interpretation



Scenario	Outcome
user connected to trusted users	trust increases
user in suspicious cluster	trust suppressed
isolated user	trust ≈ reliability



Usage in System



w_i(t) =
T_i(t)
\cdot (1 - Anom_i(t))
\cdot Exp_i(t)



Pseudo Insight

Trust = reliability refined by network structure






mathematical_formula — Formula 5

Final User Voting Weight



Final Formula

w_i(t) =
T_i(t)\;\cdot\;\big(1 - Anom_i(t)\big)\;\cdot\;Exp_i(t)



Interpretation

This formula defines the influence weight of user i at time t, which determines:

how strongly the user’s actions affect post credibility, propagation, and system decisions.

It integrates three independent dimensions:

* trustworthiness (graph-adjusted reliability)
* behavioral integrity (absence of anomaly)
* evidence strength (experience level)



Component Breakdown



1. Trust Component

T_i(t)



Meaning

* derived from Formula 4 (graph propagation)
* captures:
    * individual correctness
    * network influence



Role

* amplifies users embedded in trustworthy regions
* suppresses users connected to suspicious clusters



2. Anomaly Suppression

1 - Anom_i(t)



Meaning

* derived from Formula 3 (anomaly score)
* converts anomaly into a penalty factor



Behavior

Anom_i(t)	Effect
0	no penalty
0.5	weight halved
1	weight nullified



Role

* prevents adversarial users from influencing system
* ensures abnormal behavior reduces impact



3. Experience Component

Exp_i(t)



Meaning

* derived from Formula 2 (experience score)
* reflects accumulated activity



Role

* prevents new users from having large influence
* rewards consistent participation



Combined Effect



The product form ensures:

w_i(t) = 0 \quad \text{if any component is zero}



Interpretation

A user contributes meaningfully only if:

* they are trusted
* they behave normally
* they have sufficient experience



Variable Definitions



* T_i(t): graph-based trust score
* Anom_i(t): anomaly score
* Exp_i(t): experience score

All values lie in:

[0,1]



Properties



* w_i(t) \in [0,1]
* multiplicative gating mechanism
* robust to manipulation
* dynamically updates over time



Behavior Summary



User Type	Outcome
trusted + normal + experienced	high weight
anomalous user	strongly suppressed
new user	low weight
isolated unreliable user	low weight



Why Multiplicative Form Is Correct



This avoids:

* additive leakage (where one strong signal dominates)
* partial trust exploitation

Instead enforces:

all conditions must be satisfied simultaneously



Usage in System



This is used in:

Interaction aggregation

N_j(t),\; S_j(t)

Credibility computation

C_{Bayes}(j,t)

Variance

Var_j(t)



Pseudo Insight

Influence = trust × integrity × experience


Proceeding to the next post-level foundation.



mathematical_formula — Formula 6

Effective Interaction Mass



Final Formula

N_j(t) =
\sum_{k \in \mathcal{V}_j}
w_{i_k}(t_k)\;
e^{-\lambda (t - t_k)}



Interpretation

This formula computes the effective amount of evidence supporting post j at time t.

It represents:

the total trust-weighted, time-decayed interaction mass accumulated for the post.



Component Breakdown



1. Interaction Set

\mathcal{V}_j



Meaning

* set of all interactions associated with post j
* each interaction indexed by k



2. User Weight

w_{i_k}(t_k)



Meaning

* influence of the user who performed interaction k
* computed from Formula 5



Role

* trusted users contribute more
* anomalous or inexperienced users contribute less



3. Time Decay Factor

e^{-\lambda (t - t_k)}



Variables

* t_k: time of interaction k
* t: current time
* \lambda > 0: decay rate



Meaning

* reduces influence of older interactions
* ensures system reacts to recent evidence



4. Summation

\sum_{k \in \mathcal{V}_j}



Meaning

* aggregates contributions from all interactions



Variable Definitions



* N_j(t): effective interaction mass
* w_{i_k}(t_k): user weight
* \lambda: temporal decay parameter
* t_k: timestamp of interaction
* \mathcal{V}_j: interaction set



Properties



* N_j(t) \ge 0
* increases with more interactions
* decreases over time if no new activity
* sensitive to both quantity and quality



Behavior Interpretation



Scenario	Effect on N_j(t)
many trusted users	high value
many low-trust users	limited growth
old interactions	decay over time
recent burst	sharp increase



Why This Formulation Is Necessary



Without weighting:

* all users equal → vulnerable to spam

Without decay:

* old data dominates → stale system

With both:

system remains adaptive and robust



Usage in System



Used in:

* credibility estimation
* propagation threshold:
    N_j(t) \ge N_{min}
* urgency computation (via rate)



Pseudo Insight

Evidence = sum of trusted, recent interactions


Proceeding to the next core post-level quantity.



mathematical_formula — Formula 7

Weighted Signal Aggregation



Final Formula

S_j(t) =
\sum_{k \in \mathcal{V}_j}
w_{i_k}(t_k)\;
s_k\;
e^{-\lambda (t - t_k)}



Positive and Negative Decomposition

S_j^+(t) =
\sum_{k: s_k = +1}
w_{i_k}(t_k)\;
e^{-\lambda (t - t_k)}

S_j^-(t) =
\sum_{k: s_k = -1}
w_{i_k}(t_k)\;
e^{-\lambda (t - t_k)}

S_j(t) = S_j^+(t) - S_j^-(t)



Interpretation

This formula computes the net directional evidence for post j at time t.

It represents:

the balance between trusted positive support and trusted negative opposition, weighted by recency.



Component Breakdown



1. Interaction Set

\mathcal{V}_j

* all interactions associated with post j



2. User Weight

w_{i_k}(t_k)

* from Formula 5
* encodes:
    * trust
    * anomaly penalty
    * experience



3. Vote Signal

s_k \in \{-1, +1\}



Meaning

* +1: supports the claim
* -1: opposes the claim



4. Time Decay

e^{-\lambda (t - t_k)}

* reduces influence of older interactions
* aligns with Formula 6



Variable Definitions



* S_j(t): net signal
* S_j^+(t): positive support mass
* S_j^-(t): negative support mass
* s_k: vote value
* w_{i_k}(t_k): user weight
* \lambda: decay rate



Properties



* S_j(t) \in \mathbb{R}
* sign indicates direction of consensus
* magnitude indicates strength of agreement



Behavior Interpretation



Scenario	Outcome
strong agreement (+)	S_j \gg 0
strong disagreement (-)	S_j \ll 0
mixed opinions	S_j \approx 0



Why Decomposition Matters



Separating:

S_j^+(t), \; S_j^-(t)

is essential for:

* Bayesian credibility computation
* variance calculation
* understanding polarization



Relation to Interaction Mass



From Formula 6:

N_j(t) = S_j^+(t) + S_j^-(t)



Usage in System



Feeds into:

C_{Bayes}(j,t)

and

Var_j(t)



Pseudo Insight

Signal = trusted, time-weighted direction of opinion






mathematical_formula — Formula 8

Bayesian Credibility Estimation



Final Formula

C_{Bayes}(j,t) =
\frac{
S_j^+(t) + \alpha_0
}{
S_j^+(t) + S_j^-(t) + \alpha_0 + \beta_0
}



Interpretation

This formula computes the probabilistic credibility of post j at time t, based on:

trusted positive and negative evidence, adjusted with prior belief.

It represents:

P(\text{post is credible} \mid \text{observed interactions})



Component Breakdown



1. Positive Evidence

S_j^+(t)

* from Formula 7
* represents trusted support for the post



2. Negative Evidence

S_j^-(t)

* from Formula 7
* represents trusted opposition



3. Prior Parameters

\alpha_0,\; \beta_0 > 0



Meaning

* \alpha_0: prior positive belief
* \beta_0: prior negative belief



Role

* stabilizes early-stage estimates
* prevents extreme values with low data



4. Denominator

S_j^+(t) + S_j^-(t) + \alpha_0 + \beta_0



Meaning

* total effective evidence
* ensures normalization



Variable Definitions



* C_{Bayes}(j,t) \in [0,1]: credibility estimate
* S_j^+(t): weighted positive signal
* S_j^-(t): weighted negative signal
* \alpha_0, \beta_0: prior constants



Properties



* bounded in [0,1]
* smooth update as evidence accumulates
* robust in low-data regimes
* interpretable as probability



Behavior Interpretation



Scenario	Outcome
strong positive evidence	C_{Bayes} \to 1
strong negative evidence	C_{Bayes} \to 0
balanced evidence	C_{Bayes} \approx 0.5
no evidence	C_{Bayes} = \frac{\alpha_0}{\alpha_0 + \beta_0}



Why Priors Are Necessary



Without priors:

* early votes dominate
* instability in low interaction phase

With priors:

system starts with controlled uncertainty



Relation to Interaction Mass



S_j^+(t) + S_j^-(t) = N_j(t)



Usage in System



Feeds into final credibility:

C_j(t) =
(1-\alpha-\gamma)C_{Bayes}
+ \alpha C_{ML}
+ \gamma C_{memory}



Pseudo Insight

Credibility = ratio of trusted positive evidence to total evidence






mathematical_formula — Formula 9

Credibility Variance (Stability Measure)



Final Formula

Var_j(t) =
\frac{
\sum_{k \in \mathcal{V}_j}
w_{i_k}(t_k)\;
\big(s_k - C_j(t)\big)^2\;
e^{-\lambda (t - t_k)}
}{
\sum_{k \in \mathcal{V}_j}
w_{i_k}(t_k)\;
e^{-\lambda (t - t_k)}
}



Interpretation

This formula measures the degree of disagreement among users regarding post j at time t.

It represents:

how much individual opinions deviate from the current credibility estimate.



Component Breakdown



1. Interaction Set

\mathcal{V}_j

* all interactions associated with post j



2. User Weight

w_{i_k}(t_k)

* from Formula 5
* ensures trusted users influence variance more



3. Vote Signal

s_k \in \{-1, +1\}



4. Credibility Mean

C_j(t)

* final credibility of post
* (can be C_{Bayes} or full combined C_j)



5. Squared Deviation

(s_k - C_j(t))^2



Meaning

* measures how far a vote deviates from consensus



6. Time Decay

e^{-\lambda (t - t_k)}

* reduces influence of older interactions



7. Normalization

\sum w_{i_k}(t_k)\; e^{-\lambda (t - t_k)} = N_j(t)



Variable Definitions



* Var_j(t): variance of credibility
* C_j(t): current credibility estimate
* s_k: vote value
* w_{i_k}(t_k): user weight
* \lambda: decay parameter



Properties



* Var_j(t) \ge 0
* bounded (typically within a finite range due to s_k \in \{-1,1\})
* decreases as consensus increases



Behavior Interpretation



Scenario	Outcome
strong agreement	low variance
mixed opinions	high variance
polarized votes	high variance



Why This Formulation Is Necessary



Credibility alone is insufficient.

Two cases:

* C_j = 0.8 with strong agreement → reliable
* C_j = 0.8 with disagreement → unstable

Variance distinguishes these.



System Role



Used in:

Propagation condition

Var_j(t) \le \sigma^2

Alert condition

Var_j(t) \le \sigma^2



Key Insight



\text{Credibility} \neq \text{Confidence}

Variance captures confidence in credibility.



Pseudo Insight

Variance = disagreement weighted by trust and recency





mathematical_formula — Formula 10

Final Post Credibility (Multi-Signal Integration)



Final Formula

C_j(t) =
(1 - \alpha - \gamma)\, C_{Bayes}(j,t)
+
\alpha\, C_{ML}(j,t)
+
\gamma\, C_{memory}(j,t)



Interpretation

This formula computes the final credibility of post j at time t, by combining:

* community-based evidence
* machine learning prediction
* historical knowledge (memory)

It represents:

the system’s best estimate of whether the post is credible.



Component Breakdown



1. Bayesian Credibility

C_{Bayes}(j,t)



Source

* from Formula 8



Role

* primary signal
* derived from trusted user interactions





2. ML-Based Credibility

C_{ML}(j,t)



Meaning

* probability from content model
* based on text semantics



Role

* early-stage signal (before many votes)
* captures linguistic cues





3. Memory-Based Credibility

C_{memory}(j,t)



Definition

C_{memory}(j,t) =
\frac{
\sum_{k \in \mathcal{N}(j)}
Sim(j,k)\; C_k(t)
}{
\sum_{k \in \mathcal{N}(j)} Sim(j,k)
}



Variables

* \mathcal{N}(j): set of similar past posts
* Sim(j,k): similarity between posts



Role

* leverages historical patterns
* reinforces known truths or misinformation



4. Weight Parameters



* \alpha \in [0,1]: ML contribution weight
* \gamma \in [0,1]: memory contribution weight



Constraint

0 \le \alpha + \gamma \le 1



Meaning

* remaining weight:
    1 - \alpha - \gamma
    assigned to Bayesian signal



Variable Definitions



* C_j(t) \in [0,1]: final credibility
* C_{Bayes}: interaction-based credibility
* C_{ML}: content-based probability
* C_{memory}: similarity-based estimate



Properties



* bounded in [0,1]
* interpretable linear combination
* stable under noisy signals
* extensible (new terms can be added)



Behavior Interpretation



Scenario	Dominant Signal
early stage	ML
many interactions	Bayesian
repeated claim	memory



Why This Formulation Is Correct



Avoids:

* ML-only decisions
* crowd-only bias
* ignoring historical knowledge

Instead ensures:

balanced multi-source credibility estimation



Usage in System



Used in:

* propagation condition
* alert decision
* variance computation (as mean)



Pseudo Insight

Credibility = evidence (users) + semantics (ML) + history (memory)






mathematical_formula — Formula 11

User–Post Proximity Function


Final Formula

Prox(u,j,t) =
L_u(t)\;
\cdot\;
\exp\left(
-\frac{d(u,j)^2}{2\sigma_p^2}
\right)


Interpretation

This formula computes the relevance of post j to user u at time t, based on:

* geographic distance
* confidence in user’s location

It represents:

how appropriate it is to show or alert this post to a specific user.


Component Breakdown


1. Location Confidence

L_u(t)


Meaning

* trust in the user’s reported location
* derived from spatial consistency signals


Role

* reduces influence of unreliable or spoofed locations



2. Distance Function

d(u,j) = d(l_u(t), l_j)


Variables

* l_u(t): location of user u
* l_j: location of post j


Meaning

* geographic distance (e.g., haversine distance)



3. Gaussian Distance Decay

\exp\left(
-\frac{d(u,j)^2}{2\sigma_p^2}
\right)


Variables

* \sigma_p > 0: spatial decay parameter


Meaning

* nearby posts → high relevance
* distant posts → rapidly decreasing relevance



Variable Definitions


* Prox(u,j,t) \in [0,1]: proximity score
* L_u(t) \in [0,1]: location confidence
* d(u,j): geographic distance
* \sigma_p: spatial scale


Properties


* bounded in [0,1]
* smooth decay with distance
* penalizes unreliable locations
* symmetric with respect to distance


Behavior Interpretation


Distance	Prox
very close	near 1
moderate	decreases smoothly
far away	near 0


Effect of Location Confidence


L_u(t)	Effect
1	full proximity
0.5	reduced relevance
0	no relevance


Why Gaussian Decay Is Used


Compared to linear decay:

* smoother transition
* avoids sharp cutoffs
* better reflects real-world spatial relevance


System Role


Used in:

Alert decision

Prox(u,j,t) \ge \tau_p

Feed ranking

* higher proximity → higher priority


Key Insight


\text{Relevance} = \text{distance effect} \times \text{location trust}


Pseudo Insight

Proximity = trusted closeness in space


mathematical_formula — Formula 12

Post Urgency Score



Final Formula

U_j(t) =
1 - \exp\left(
- \big(
\beta_1 K_j
+
\beta_2 Cat_j
+
\beta_3 V_j(t)
\big)
\right)



Interpretation

This formula computes the urgency level of post j at time t, representing:

how time-sensitive and action-relevant the information is.

It combines:

* textual urgency signals
* semantic category importance
* real-time activity velocity



Component Breakdown



1. Keyword-Based Signal

K_j =
\frac{1}{|p_j|}
\sum_{w \in p_j} \phi(w)



Variables

* p_j: set of words in post j
* \phi(w) \in [0,1]: importance score of word w



Meaning

* captures urgency-related terms (e.g., emergency indicators)





2. Category-Based Signal

Cat_j \in [0,1]



Meaning

* output of content classification
* represents importance level of category



Example

Category	Value
emergency	high
general	low





3. Velocity-Based Signal



Step 1: Interaction Rate

rate_j(t) =
\frac{
\sum_{k: t_k \in [t-\Delta t, t]}
w_{i_k}(t_k)
}{
\Delta t
}



Step 2: Normalization

V_j(t) =
1 - \exp\left(
-\frac{rate_j(t)}{rate_{baseline}}
\right)



Meaning

* detects rapidly evolving events
* captures bursts of activity





4. Weighted Aggregation

\beta_1 K_j + \beta_2 Cat_j + \beta_3 V_j(t)



Constraints

\beta_1 + \beta_2 + \beta_3 = 1



Meaning

* balances different urgency signals





5. Final Bounding Function

1 - \exp(-x)



Purpose

* ensures output in [0,1]
* smooth response to input



Variable Definitions



* U_j(t) \in [0,1]: urgency score
* K_j: keyword urgency
* Cat_j: category importance
* V_j(t): activity velocity
* \beta_1, \beta_2, \beta_3: weights
* \Delta t: time window
* rate_{baseline}: normalization constant



Properties



* bounded in [0,1]
* increases with urgency signals
* robust to single-signal manipulation
* responsive to real-time changes



Behavior Interpretation



Scenario	U_j(t)
urgent keywords + burst	high
normal content	low
high activity spike	increases



Why Multi-Signal Is Necessary



Single signals can be manipulated:

* keywords → spammed
* velocity → bot attack

Combined:

system becomes robust



System Role



Used in:

Alert condition

C_j(t) \cdot U_j(t) \ge \theta_{alert}



Key Insight



\text{Urgency} = \text{importance} + \text{activity dynamics}



Pseudo Insight

Urgency = how important and how fast the situation is evolving




mathematical_formula — Formula 13

Propagation Condition (Controlled Expansion)


Final Formula

Expand(j,t) =
\mathbb{I}\Big(
C_j(t) \ge \theta
\;\wedge\;
N_j(t) \ge N_{min}
\;\wedge\;
Var_j(t) \le \sigma^2
\;\wedge\;
(t - t_{create,j}) \ge T_{min}
\;\wedge\;
\bar{L}_j(t) \ge L_{min}
\Big)


Interpretation

This formula determines whether post j is allowed to expand its visibility at time t.

It represents:

a strict multi-condition gate ensuring that content spreads only when sufficiently credible, supported, stable, and trustworthy.


Component Breakdown


1. Indicator Function

\mathbb{I}(\cdot)


Meaning

* returns:
    * 1 → expand
    * 0 → do not expand



2. Credibility Constraint

C_j(t) \ge \theta


Meaning

* ensures post has sufficient credibility


Variable

* \theta: credibility threshold



3. Evidence Constraint

N_j(t) \ge N_{min}


Meaning

* ensures enough interaction evidence


Variable

* N_{min}: minimum required interaction mass



4. Stability Constraint

Var_j(t) \le \sigma^2


Meaning

* ensures consensus among users


Variable

* \sigma^2: variance threshold



5. Temporal Stability Constraint

(t - t_{create,j}) \ge T_{min}


Meaning

* ensures post has existed long enough for evaluation


Variable

* T_{min}: minimum stabilization time



6. Spatial Trust Constraint

\bar{L}_j(t) \ge L_{min}


Definition

\bar{L}_j(t) =
\frac{
\sum_{k \in \mathcal{V}_j}
w_{i_k}(t_k)\;
L_{i_k}(t_k)\;
e^{-\lambda (t - t_k)}
}{
\sum_{k \in \mathcal{V}_j}
w_{i_k}(t_k)\;
e^{-\lambda (t - t_k)}
}


Meaning

* average location trust of contributing users


Variable

* L_{min}: minimum spatial trust


Variable Definitions


* C_j(t): final credibility
* N_j(t): interaction mass
* Var_j(t): credibility variance
* t_{create,j}: post creation time
* \bar{L}_j(t): aggregated location confidence


Properties


* binary decision
* multi-dimensional constraint
* prevents premature propagation
* robust to manipulation


Behavior Interpretation


Condition Fails	Result
low credibility	blocked
insufficient data	blocked
disagreement	blocked
too early	delayed
unreliable location	blocked


Why Multi-Constraint Is Necessary


Single-condition systems fail because:

* high votes ≠ truth
* high activity ≠ reliability

This formulation ensures:

propagation requires consistent agreement across all dimensions


System Role


Used to:

* control propagation radius
* determine expansion step


Key Insight


\text{Propagation} \neq \text{existence of content}

\text{Propagation} = \text{satisfaction of trust conditions}


Pseudo Insight

Content spreads only when it earns the right to spread





mathematical_formula — Formula 14

Alert Decision Function


Final Formula

Alert(u,j,t) =
\mathbb{I}\Big(
Prox(u,j,t) \ge \tau_p
\;\wedge\;
C_j(t)\cdot U_j(t) \ge \theta_{alert}
\;\wedge\;
Var_j(t) \le \sigma^2
\;\wedge\;
\neg RateLimited(u,t)
\Big)


Interpretation

This formula determines whether user u should receive an alert for post j at time t.

It represents:

a strict, user-specific decision that ensures alerts are relevant, credible, urgent, stable, and not excessive.


Component Breakdown


1. Indicator Function

\mathbb{I}(\cdot)


Meaning

* returns:
    * 1 → send alert
    * 0 → do not send



2. Proximity Constraint

Prox(u,j,t) \ge \tau_p


Meaning

* ensures the post is geographically relevant


Variables

* Prox(u,j,t): from Formula 11
* \tau_p: proximity threshold



3. Credibility–Urgency Constraint

C_j(t)\cdot U_j(t) \ge \theta_{alert}


Meaning

* ensures the post is both:
    * credible
    * urgent


Variables

* C_j(t): from Formula 10
* U_j(t): from Formula 12
* \theta_{alert}: alert threshold



4. Stability Constraint

Var_j(t) \le \sigma^2


Meaning

* ensures the information is not controversial or unstable



5. Rate Limiting Constraint

\neg RateLimited(u,t)


Definition

RateLimited(u,t) =
\mathbb{I}\left(
N_{alerts}(u, t-\Delta t, t) \ge R_{max}
\right)


Variables

* N_{alerts}(u, t-\Delta t, t): alerts received in window
* R_{max}: maximum allowed alerts


Meaning

* prevents alert fatigue


Variable Definitions


* Prox(u,j,t): spatial relevance
* C_j(t): credibility
* U_j(t): urgency
* Var_j(t): variance
* \tau_p: proximity threshold
* \theta_{alert}: alert threshold
* R_{max}: rate limit


Properties


* binary decision
* user-specific
* multi-dimensional gating
* robust against spam and noise


Behavior Interpretation


Condition Fails	Result
far away	no alert
low credibility	no alert
low urgency	no alert
high disagreement	no alert
too many alerts	suppressed


Why Multiplicative Credibility–Urgency


C_j(t)\cdot U_j(t)

ensures:

* urgent but false → blocked
* true but non-urgent → no alert
* only credible AND urgent → allowed


System Role


* triggers notifications
* defines real-time system output
* directly affects user experience


Key Insight


\text{Alert} \neq \text{important content}

\text{Alert} = \text{important} \;\cap\; \text{credible} \;\cap\; \text{relevant}


Pseudo Insight

Alert only when it matters, is true, and affects the user


Status

At this point:

* all major formulas in your system are defined
* dependencies are complete
* no variable remains undefined

