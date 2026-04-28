input_signal — Signal 1

GPS Consistency Score (Location Stability Signal)


Final Formula

S_{\text{gps}}(i,t) =
\exp\left(
- \frac{\sigma^2_{\text{spatial}}(i,t)}{2 \sigma_0^2}
\right)


Interpretation

This signal measures:

how stable and physically consistent a user’s location history is over time.

It is used in:

L_i(t) \quad \text{(location confidence)}


Component Breakdown


1. Spatial Variance

\sigma^2_{\text{spatial}}(i,t) =
\frac{
\sum_{k \in \mathcal{L}_i}
\| l_i(t_k) - \bar{l}_i(t) \|^2
\cdot
e^{-\lambda_L (t - t_k)}
}{
\sum_{k \in \mathcal{L}_i}
e^{-\lambda_L (t - t_k)}
}


Variables

* \mathcal{L}_i: set of location samples for user i
* l_i(t_k): location at time t_k
* \bar{l}_i(t): weighted mean location



2. Mean Location

\bar{l}_i(t) =
\frac{
\sum_{k} l_i(t_k)\; e^{-\lambda_L (t - t_k)}
}{
\sum_{k} e^{-\lambda_L (t - t_k)}
}


3. Distance Metric

\| l_i(t_k) - \bar{l}_i(t) \|


Meaning

* geographic distance (e.g., haversine)



4. Normalization Parameter

* \sigma_0: expected spatial deviation scale


Variable Definitions


* S_{\text{gps}}(i,t) \in [0,1]: GPS consistency score
* \sigma^2_{\text{spatial}}: location variance
* \lambda_L: temporal decay
* \sigma_0: normalization constant


Properties


* bounded in [0,1]
* high when movement is realistic
* low when movement is erratic


Behavior Interpretation


Behavior	Score
stable movement	high
gradual movement	high
teleportation	low
random jumps	very low


Why This Signal Matters


Detects:

* GPS spoofing
* bot movement patterns
* unrealistic travel


Usage in System


Feeds into:

L_i(t) =
w_1 S_{\text{gps}} + \cdots


Pseudo Insight

Real humans move smoothly, attackers jump




input_signal — Signal 2

Speed Plausibility Score (Physical Movement Constraint)


Final Formula

S_{\text{speed}}(i,t) =
\exp\left(
- \frac{v_{\max}(i,t)^2}{2 v_0^2}
\right)


Interpretation

This signal measures:

whether the user’s movement speed is physically plausible over time.

It directly detects:

* teleportation
* GPS spoofing
* impossible travel speeds


Component Breakdown


1. Instantaneous Speed Between Consecutive Points

v_k =
\frac{
d\big(l_i(t_k),\, l_i(t_{k-1})\big)
}{
t_k - t_{k-1}
}


Variables

* l_i(t_k): location at time t_k
* d(\cdot,\cdot): geographic distance (e.g., haversine)
* t_k - t_{k-1}: time difference



2. Maximum Observed Speed

v_{\max}(i,t) =
\max_{k \in \mathcal{L}_i} v_k


Meaning

* worst-case movement speed
* captures extreme anomalies



3. Normalization Parameter

* v_0: maximum plausible speed


Typical Values

Walking → ~1.5 m/s
Vehicle → ~30 m/s
Airplane → ~250 m/s

Choose v_0 based on your system assumption.



4. Exponential Decay Mapping

\exp\left(-\frac{v_{\max}^2}{2 v_0^2}\right)


Meaning

* small speeds → near 1
* large speeds → rapidly decreases


Variable Definitions


* S_{\text{speed}}(i,t) \in [0,1]: speed plausibility score
* v_k: instantaneous speed
* v_{\max}: maximum observed speed
* v_0: speed threshold


Properties


* bounded in [0,1]
* sensitive to extreme values
* robust to small noise


Behavior Interpretation


Behavior	Score
normal movement	high
fast but realistic	moderate
teleportation	near 0
extreme jumps	0


Why Max Speed Is Used


Using:

v_{\max}

instead of average ensures:

even a single impossible jump is detected


Usage in System


Feeds into:

L_i(t) =
w_1 S_{\text{gps}} + w_2 S_{\text{speed}} + \cdots


Pseudo Insight

One impossible jump is enough to lose trust




input_signal — Signal 3

Location Source Reliability Score (Sensor Trustworthiness)


Final Formula

S_{\text{source}}(i,t) =
\sum_{s \in \mathcal{S}}
\omega_s \cdot q_s(i,t)


Constraint

\sum_{s \in \mathcal{S}} \omega_s = 1


Interpretation

This signal measures:

how trustworthy the source of location data is for user i at time t.

It captures:

* sensor type reliability
* signal integrity
* spoofing likelihood


Component Breakdown


1. Set of Location Sources

\mathcal{S} = \{\text{GPS},\; \text{WiFi},\; \text{IP},\; \text{Cellular}\}


2. Source Quality Score

q_s(i,t) \in [0,1]


Meaning

Represents reliability of source s for user i


Typical Values

Source	q_s
GPS (high accuracy)	high
WiFi triangulation	medium
Cellular	lower
IP-based	lowest



3. Source Weight

\omega_s


Meaning

* importance assigned to each source
* system-level configuration


Example

GPS      → 0.5
WiFi     → 0.3
Cellular → 0.15
IP       → 0.05



4. Combined Score

S_{\text{source}}(i,t)


Meaning

* weighted average of all active sources


Enhancement: Consistency Across Sources

Optional refinement:

q_s(i,t) =
\exp\left(
- \frac{d(l_s, \bar{l}_i)^2}{2\sigma_s^2}
\right)


Meaning

* penalizes disagreement between sources


Variable Definitions


* S_{\text{source}}(i,t) \in [0,1]: source reliability
* q_s(i,t): quality of source s
* \omega_s: weight of source
* l_s: location from source s


Properties


* bounded in [0,1]
* increases with high-quality sensors
* decreases with inconsistent signals


Behavior Interpretation


Scenario	Score
GPS + WiFi consistent	high
only IP	low
conflicting sources	reduced
spoofed GPS	reduced


Why This Signal Matters


Detects:

* fake GPS apps
* IP masking
* inconsistent sensor data


Usage in System


Feeds into:

L_i(t) =
w_1 S_{\text{gps}}
+ w_2 S_{\text{speed}}
+ w_3 S_{\text{source}}
+ \cdots


Pseudo Insight

Not all location signals are equal



input_signal — Signal 4

Movement Continuity Score (Trajectory Smoothness)


Final Formula

S_{\text{cont}}(i,t) =
\exp\left(
- \frac{A_i(t)}{2 A_0}
\right)


Interpretation

This signal measures:

how smooth and physically continuous a user’s movement trajectory is over time.

It captures:

* abrupt direction changes
* zig-zag or random movement
* non-human trajectory patterns


Component Breakdown


1. Direction Vectors

\vec{v}_k =
l_i(t_k) - l_i(t_{k-1})


Meaning

* displacement vector between consecutive positions



2. Angle Between Consecutive Movements

\theta_k =
\arccos\left(
\frac{
\vec{v}_k \cdot \vec{v}_{k-1}
}{
\|\vec{v}_k\|\;\|\vec{v}_{k-1}\|
+ \epsilon
}
\right)


Meaning

* change in direction between steps



3. Trajectory Angular Variance

A_i(t) =
\frac{
\sum_{k} \theta_k^2 \cdot e^{-\lambda_L (t - t_k)}
}{
\sum_{k} e^{-\lambda_L (t - t_k)}
}


Meaning

* weighted measure of direction instability



4. Normalization Parameter

* A_0: expected angular variation for normal movement



5. Final Score

S_{\text{cont}}(i,t)


Meaning

* smooth trajectory → high score
* erratic movement → low score


Variable Definitions


* S_{\text{cont}}(i,t) \in [0,1]: continuity score
* \theta_k: angle between movements
* A_i(t): angular variance
* \lambda_L: time decay
* A_0: normalization constant


Properties


* bounded in [0,1]
* sensitive to rapid direction changes
* robust to small noise


Behavior Interpretation


Movement Type	Score
straight path	high
gradual turns	high
zig-zag	low
random jumps	very low


Why This Signal Matters


Detects:

* scripted/bot movement
* GPS spoofing patterns
* non-physical trajectories


Usage in System


Feeds into:

L_i(t) =
w_1 S_{\text{gps}}
+ w_2 S_{\text{speed}}
+ w_3 S_{\text{source}}
+ w_4 S_{\text{cont}}
+ \cdots


Pseudo Insight

Humans move smoothly, bots move erratically



input_signal — Signal 5

Interaction Rate Deviation (Burst Detection Signal)


Final Formula

S_{\text{rate}}(i,t) =
\frac{
V_i^{window}(t)
}{
\mu_i^{baseline}(t) + \epsilon
}


Optional Bounded Form (Recommended for Stability)

\tilde{S}_{\text{rate}}(i,t) =
1 - \exp\left(
- \frac{V_i^{window}(t)}{\mu_i^{baseline}(t) + \epsilon}
\right)


Interpretation

This signal measures:

how much a user’s current activity deviates from their normal behavior.

It detects:

* sudden bursts
* spam activity
* coordinated attack behavior


Component Breakdown


1. Short-Term Activity

V_i^{window}(t) =
\sum_{k: t_k \in [t - \Delta t,\, t]} 1


Meaning

* number of actions in recent time window



2. Baseline Activity Rate

\mu_i^{baseline}(t) =
\frac{
\sum_{k} e^{-\lambda_r (t - t_k)}
}{
\sum_{k} e^{-\lambda_r (t - t_k)} \cdot (t_k - t_{k-1})
}


Simplified Practical Form

baseline = average interactions per unit time (historical)



3. Ratio

\frac{V_i^{window}(t)}{\mu_i^{baseline}(t)}


Meaning

* compares current activity vs normal behavior



4. Exponential Bounding

1 - \exp(-x)


Purpose

* prevents unbounded growth
* stabilizes anomaly contribution


Variable Definitions


* S_{\text{rate}}(i,t): burst signal
* V_i^{window}(t): recent activity count
* \mu_i^{baseline}(t): long-term average rate
* \Delta t: time window
* \lambda_r: decay rate
* \epsilon: small constant


Properties


* S_{\text{rate}} \ge 0 (unbounded raw form)
* bounded version \tilde{S}_{\text{rate}} \in [0,1]
* sensitive to sudden spikes


Behavior Interpretation


Behavior	Signal
normal activity	≈ 1
mild increase	> 1
strong burst	≫ 1
no activity	≈ 0


Why This Signal Matters


Detects:

* bot spamming
* coordinated voting bursts
* artificial amplification


Usage in System


Feeds into anomaly component:

D_1(i,t) = \tilde{S}_{\text{rate}}(i,t)


Pseudo Insight

Humans are consistent, attackers spike



input_signal — Signal 6

Action Entropy Score (Behavioral Diversity Signal)


Final Formula

S_{\text{entropy}}(i,t) =
\frac{
H_i(t)
}{
\log |\mathcal{A}|
}


Where

H_i(t) =
- \sum_{a \in \mathcal{A}}
p_i(a,t)\,\log p_i(a,t)


Interpretation

This signal measures:

how diverse and natural a user’s actions are over time.

It captures:

* repetitive behavior
* scripted actions
* lack of variability


Component Breakdown


1. Action Set

\mathcal{A}


Meaning

Set of possible user actions, for example:

{vote_up, vote_down, post, scroll, view, share}



2. Action Probability Distribution

p_i(a,t) =
\frac{
\sum_{k: a_k = a}
e^{-\lambda_r (t - t_k)}
}{
\sum_{k}
e^{-\lambda_r (t - t_k)}
}


Meaning

* probability that user performs action a
* time-decayed frequency



3. Entropy Calculation

H_i(t)


Meaning

* measures randomness/diversity
* higher → more varied behavior



4. Normalization

\log |\mathcal{A}|


Meaning

* maximum possible entropy
* ensures output is bounded



5. Final Score

S_{\text{entropy}}(i,t) \in [0,1]


Variable Definitions


* S_{\text{entropy}}(i,t): entropy score
* H_i(t): action entropy
* p_i(a,t): probability of action
* \lambda_r: decay parameter
* |\mathcal{A}|: number of actions


Properties


* bounded in [0,1]
* high for diverse behavior
* low for repetitive behavior


Behavior Interpretation


Behavior	Score
varied actions	high
moderate diversity	medium
repetitive voting only	low
identical actions	near 0


Why This Signal Matters


Detects:

* bots repeating same action
* coordinated scripts
* non-human interaction patterns


Usage in System


Feeds into anomaly:

D_2(i,t) = 1 - S_{\text{entropy}}(i,t)


Key Insight


\text{Low entropy} \Rightarrow \text{high anomaly}


Pseudo Insight

Humans behave variably, bots repeat




input_signal — Signal 7

Consensus Alignment Score (Correctness Consistency Signal)


Final Formula

S_{\text{cons}}(i,t) =
\frac{
\sum_{k \in \mathcal{V}_i}
\mathbb{I}(s_k = y_{j_k}) \cdot e^{-\lambda_r (t - t_k)}
}{
\sum_{k \in \mathcal{V}_i}
e^{-\lambda_r (t - t_k)} + \epsilon
}


Interpretation

This signal measures:

how consistently user i’s actions align with the final verified outcomes over time.

It captures:

* correctness of behavior
* long-term alignment with truth
* deviation from consensus


Component Breakdown


1. Interaction Set

\mathcal{V}_i


Meaning

* all interactions performed by user i



2. Indicator Function

\mathbb{I}(s_k = y_{j_k})


Meaning

* equals 1 if:
    * user vote s_k matches final truth y_{j_k}
* equals 0 otherwise



3. Time Decay

e^{-\lambda_r (t - t_k)}


Meaning

* recent correctness is more important
* older actions fade



4. Normalization

\sum_{k} e^{-\lambda_r (t - t_k)}


Meaning

* total weighted interactions



5. Final Score

S_{\text{cons}}(i,t) \in [0,1]


Variable Definitions


* S_{\text{cons}}(i,t): consensus alignment score
* s_k: user vote
* y_{j_k}: ground truth label of post
* \lambda_r: decay parameter
* t_k: interaction timestamp
* \epsilon: numerical stability constant


Properties


* bounded in [0,1]
* increases with correct behavior
* decreases with incorrect behavior


Behavior Interpretation


Behavior	Score
mostly correct	high
mixed accuracy	medium
mostly incorrect	low
adversarial	near 0


Why This Signal Matters


Captures:

* long-term correctness
* deviation from truth
* reliability consistency


Usage in System


Feeds into:

Reliability (implicitly)

\alpha_i,\; \beta_i

Anomaly

D_3(i,t) = 1 - S_{\text{cons}}(i,t)


Important Note


This signal requires:

ground truth y_j available (delayed)

So it is:

* retrospective
* not available immediately


Pseudo Insight

Consistently wrong behavior is a strong anomaly signal




input_signal — Signal 8

Coordination Similarity Score (User–User Behavioral Correlation)


Final Formula

S_{\text{coord}}(i,t) =
\max_{j \in \mathcal{N}(i)}
Sim(i,j,t)


Where

Sim(i,j,t) =
\frac{
\sum_{k \in \mathcal{P}_{ij}}
\mathbb{I}(s_{i,k} = s_{j,k})
\cdot
\exp\left(-\frac{|t_{i,k} - t_{j,k}|}{\tau}\right)
}{
|\mathcal{P}_{ij}| + \epsilon
}


Interpretation

This signal measures:

how strongly user i behaves in coordination with other users.

It detects:

* synchronized voting
* coordinated attacks
* bot clusters


Component Breakdown


1. Neighbor Set

\mathcal{N}(i)


Meaning

* users who have interacted with the same posts as user i



2. Shared Interaction Set

\mathcal{P}_{ij}


Meaning

* set of posts where both users i and j interacted



3. Vote Agreement Indicator

\mathbb{I}(s_{i,k} = s_{j,k})


Meaning

* 1 if both users gave same vote
* 0 otherwise



4. Temporal Alignment Factor

\exp\left(-\frac{|t_{i,k} - t_{j,k}|}{\tau}\right)


Meaning

* high when actions occur close in time
* low when actions are far apart



5. Averaging

\frac{\sum (\cdot)}{|\mathcal{P}_{ij}|}


Meaning

* normalizes similarity across shared interactions



6. Maximum Selection

\max_{j \in \mathcal{N}(i)}


Meaning

* focuses on strongest coordination partner
* captures worst-case coordination


Variable Definitions


* S_{\text{coord}}(i,t) \in [0,1]: coordination score
* Sim(i,j,t): similarity between users
* s_{i,k}, s_{j,k}: votes
* t_{i,k}, t_{j,k}: timestamps
* \tau: time sensitivity parameter


Properties


* bounded in [0,1]
* increases with:
    * agreement
    * synchronization
* robust to random overlap


Behavior Interpretation


Behavior	Score
independent users	low
occasional agreement	moderate
synchronized voting	high
bot cluster	near 1


Why Max Operator Is Used


Using:

\max_j Sim(i,j)

ensures:

even a single strong coordination link is detected


Why This Signal Matters


Detects:

* coordinated misinformation campaigns
* bot networks
* group manipulation


Usage in System


Feeds into anomaly:

D_4(i,t) = S_{\text{coord}}(i,t)


Pseudo Insight

Acting together too perfectly is suspicious





input_signal — Signal 9

Location Inconsistency Score (Teleportation / Plausibility Violation)


Final Formula

S_{\text{loc\_inc}}(i,t) =
\frac{
N_{\text{implausible}}(i,t)
}{
N_{\text{moves}}(i,t) + \epsilon
}


Interpretation

This signal measures:

how frequently a user’s location transitions violate physical plausibility.

It captures:

* teleportation behavior
* long-distance jumps in short time
* spoofed location traces


Component Breakdown


1. Movement Set

\mathcal{M}_i =
\{(t_{k-1}, t_k)\}


Meaning

* consecutive location transitions for user i



2. Instantaneous Speed

v_k =
\frac{
d\big(l_i(t_k),\, l_i(t_{k-1})\big)
}{
t_k - t_{k-1}
}


Meaning

* speed required to move between two points



3. Plausibility Indicator

\mathbb{I}_{\text{implausible}}(k) =
\mathbb{I}(v_k > v_{\max})


Meaning

* 1 if speed exceeds maximum plausible threshold
* 0 otherwise



4. Count of Implausible Movements

N_{\text{implausible}}(i,t) =
\sum_{k \in \mathcal{M}_i}
\mathbb{I}_{\text{implausible}}(k)
\cdot
e^{-\lambda_L (t - t_k)}



5. Total Movement Count

N_{\text{moves}}(i,t) =
\sum_{k \in \mathcal{M}_i}
e^{-\lambda_L (t - t_k)}



6. Final Ratio

S_{\text{loc\_inc}}(i,t)


Meaning

* fraction of implausible movements


Variable Definitions


* S_{\text{loc\_inc}}(i,t) \in [0,1]: inconsistency score
* v_k: movement speed
* v_{\max}: maximum plausible speed
* \lambda_L: time decay
* d(\cdot,\cdot): geographic distance
* \epsilon: small constant


Properties


* bounded in [0,1]
* increases with abnormal movement frequency
* robust to occasional noise


Behavior Interpretation


Behavior	Score
consistent movement	near 0
occasional anomaly	low
frequent jumps	high
teleportation pattern	near 1


Important Relation


This signal complements:

* Speed Plausibility (Signal 2) → detects extreme single event
* Location Inconsistency (this) → detects repeated violations


Why This Signal Matters


Detects:

* repeated GPS spoofing
* bot-generated location traces
* coordinated location fraud


Usage in System


Feeds into anomaly:

D_5(i,t) = S_{\text{loc\_inc}}(i,t)


Pseudo Insight

Occasional anomaly is noise, repeated anomaly is intent




input_signal — Signal 10

Human Navigation Deviation Score (Behavioral Mobility Model)


Final Formula

S_{\text{nav}}(i,t) =
1 - \exp\left(
- \frac{D_{\text{nav}}(i,t)}{\kappa}
\right)


Where

D_{\text{nav}}(i,t) =
\frac{
1}{|\mathcal{T}_i|}
\sum_{\tau \in \mathcal{T}_i}
d_{\text{dist}}\big(
P_i(\tau),\;
P_{\text{human}}(\tau)
\big)


Interpretation

This signal measures:

how much a user’s movement behavior deviates from typical human navigation patterns.

It captures:

* unrealistic travel sequences
* abnormal mobility patterns
* non-human trajectory behavior


Component Breakdown


1. Trajectory Segments

\mathcal{T}_i


Meaning

* set of trajectory segments (e.g., sequences of locations over time)



2. User Mobility Distribution

P_i(\tau)


Meaning

* probability distribution over trajectory features for user i


Features may include:

step length
turn angles
pause duration
movement frequency



3. Human Reference Distribution

P_{\text{human}}(\tau)


Meaning

* learned distribution from real human mobility data



4. Distribution Distance

d_{\text{dist}}(P_i, P_{\text{human}})


Options

KL divergence
Wasserstein distance
Jensen-Shannon divergence


Recommended

d_{\text{dist}} = D_{JS}(P_i \parallel P_{\text{human}})



5. Averaging Across Segments

\frac{1}{|\mathcal{T}_i|} \sum


Meaning

* average deviation across movement patterns



6. Exponential Mapping

1 - \exp(-x/\kappa)


Meaning

* smooth mapping to [0,1]
* controlled sensitivity



Variable Definitions


* S_{\text{nav}}(i,t) \in [0,1]: navigation deviation score
* D_{\text{nav}}(i,t): deviation magnitude
* \kappa: scaling parameter
* P_i: user mobility distribution
* P_{\text{human}}: reference distribution


Properties


* bounded in [0,1]
* increases with behavioral abnormality
* robust to noise


Behavior Interpretation


Behavior	Score
normal human mobility	low
slightly unusual	moderate
highly irregular	high
synthetic movement	near 1


Why This Signal Matters


Detects:

* synthetic trajectories
* scripted location behavior
* advanced spoofing (beyond simple jumps)


Difference from Other Signals


Signal	Detects
GPS consistency	variance
speed	extreme jumps
continuity	direction changes
navigation (this)	distribution-level behavior


Usage in System


Feeds into anomaly ML features:

r_{\text{nav}}(i,t) = S_{\text{nav}}(i,t)


Pseudo Insight

Not just where you go, but how you move matters


Status So Far

You now have 10 core signals, covering:


Location Trust Signals

1. GPS consistency
2. Speed plausibility
3. Source reliability
4. Movement continuity
5. Location inconsistency
6. Navigation deviation


Behavioral Signals

7. Interaction rate deviation
8. Action entropy
9. Consensus alignment
10. Coordination similarity


What Remains (Final Signals)

To complete system:

* device fingerprint reliability
* IP consistency score
* session continuity
* vote timing irregularity




input_signal — Signal 11

Device Fingerprint Consistency Score (Identity Stability Signal)


Final Formula

S_{\text{device}}(i,t) =
\exp\left(
- \frac{H_{\text{device}}(i,t)}{\log |\mathcal{D}_i|}
\right)


Where

H_{\text{device}}(i,t) =
- \sum_{d \in \mathcal{D}_i}
p_i(d,t)\,\log p_i(d,t)


Interpretation

This signal measures:

how consistent a user’s device usage is over time.

It captures:

* multiple device switching
* bot/device rotation
* identity instability


Component Breakdown


1. Device Set

\mathcal{D}_i


Meaning

* set of devices used by user i


Device fingerprint may include:

browser + OS
hardware signature
screen resolution
user-agent hash



2. Device Probability Distribution

p_i(d,t) =
\frac{
\sum_{k: d_k = d}
e^{-\lambda_d (t - t_k)}
}{
\sum_{k}
e^{-\lambda_d (t - t_k)}
}


Meaning

* probability of user using device d
* time-decayed frequency



3. Device Entropy

H_{\text{device}}(i,t)


Meaning

* measures diversity of device usage
* higher entropy → more switching



4. Normalization

\log |\mathcal{D}_i|


Meaning

* maximum entropy possible



5. Exponential Mapping

\exp(-x)


Meaning

* converts entropy to consistency
* high entropy → low score


Variable Definitions


* S_{\text{device}}(i,t) \in [0,1]: device consistency score
* H_{\text{device}}: device entropy
* p_i(d,t): device usage probability
* \lambda_d: decay parameter
* \mathcal{D}_i: device set


Properties


* bounded in [0,1]
* high for consistent device usage
* low for frequent switching


Behavior Interpretation


Behavior	Score
single device	high
few devices	moderate
frequent switching	low
rotating devices (botnet)	near 0


Why This Signal Matters


Detects:

* account sharing
* bot farms
* identity spoofing


Usage in System


Feeds into anomaly ML features:

r_{\text{fp}}(i,t) = S_{\text{device}}(i,t)


Pseudo Insight

Real users are stable, bots rotate identities



input_signal — Signal 12

IP Consistency Score (Network-Level Stability Signal)


Final Formula

S_{\text{ip}}(i,t) =
\exp\left(
- \frac{H_{\text{ip}}(i,t)}{\log |\mathcal{I}_i|}
\right)
\cdot
\exp\left(
- \frac{\sigma^2_{\text{ip-loc}}(i,t)}{2\sigma_{ip}^2}
\right)


Interpretation

This signal measures:

how stable and geographically consistent a user’s network identity (IP) is over time.

It captures:

* IP hopping
* VPN/proxy usage
* mismatch between IP location and GPS


Component Breakdown


1. IP Set

\mathcal{I}_i


Meaning

* set of distinct IP addresses used by user i



2. IP Usage Distribution

p_i(ip,t) =
\frac{
\sum_{k: ip_k = ip}
e^{-\lambda_{ip}(t - t_k)}
}{
\sum_{k}
e^{-\lambda_{ip}(t - t_k)}
}


Meaning

* probability of using a specific IP
* time-decayed



3. IP Entropy

H_{\text{ip}}(i,t) =
- \sum_{ip \in \mathcal{I}_i}
p_i(ip,t)\,\log p_i(ip,t)


Meaning

* measures IP switching behavior
* higher entropy → more switching



4. IP-Based Location Variance

\sigma^2_{\text{ip-loc}}(i,t) =
\frac{
\sum_{k}
\| l_{ip}(t_k) - \bar{l}_{ip}(t) \|^2
\cdot
e^{-\lambda_{ip}(t - t_k)}
}{
\sum_{k}
e^{-\lambda_{ip}(t - t_k)}
}


Variables

* l_{ip}(t_k): location derived from IP
* \bar{l}_{ip}(t): mean IP location



5. Mean IP Location

\bar{l}_{ip}(t) =
\frac{
\sum_{k} l_{ip}(t_k)\, e^{-\lambda_{ip}(t - t_k)}
}{
\sum_{k} e^{-\lambda_{ip}(t - t_k)}
}



6. Combined Score

Two factors:

1. IP switching (entropy)
2. IP geographic consistency (variance)


Variable Definitions


* S_{\text{ip}}(i,t) \in [0,1]: IP consistency score
* H_{\text{ip}}: entropy of IP usage
* \sigma^2_{\text{ip-loc}}: geographic variance
* \lambda_{ip}: decay parameter
* \sigma_{ip}: normalization constant


Properties


* bounded in [0,1]
* decreases with:
    * frequent IP switching
    * inconsistent geographic origin


Behavior Interpretation


Behavior	Score
stable IP	high
few IPs (normal mobility)	moderate
VPN switching	low
global IP hopping	near 0


Why This Signal Matters


Detects:

* VPN/proxy abuse
* bot networks using rotating IPs
* mismatch between physical and network location


Relation to Other Signals


Signal	Layer
GPS consistency	device/location
IP consistency	network layer
device fingerprint	identity layer


Usage in System


Feeds into anomaly ML features:

r_{\text{ip}}(i,t) = S_{\text{ip}}(i,t)


Pseudo Insight

Real users stay locally consistent, attackers jump networks




input_signal — Signal 13

Session Continuity Score (Human Activity Pattern Signal)


Final Formula

S_{\text{session}}(i,t) =
\exp\left(
- \frac{D_{\text{session}}(i,t)}{\delta}
\right)


Where

D_{\text{session}}(i,t) =
\frac{
\big|\mu_{\text{sess}}(i,t) - \mu_{\text{human}}\big|
}{
\mu_{\text{human}}
}
+
\frac{
\big|\sigma_{\text{sess}}(i,t) - \sigma_{\text{human}}\big|
}{
\sigma_{\text{human}}
}


Interpretation

This signal measures:

how closely a user’s session behavior matches typical human activity patterns.

It captures:

* unrealistically long sessions (bots running continuously)
* extremely short fragmented sessions
* abnormal session timing


Component Breakdown


1. Session Definition

A session is defined as:

continuous activity with gap ≤ T_gap


Meaning

* if time between actions exceeds T_{gap}, a new session starts



2. Session Duration Set

\mathcal{S}_i = \{d_1, d_2, \dots, d_n\}


Meaning

* durations of all sessions for user i



3. Mean Session Duration

\mu_{\text{sess}}(i,t) =
\frac{
\sum_{k} d_k \cdot e^{-\lambda_s (t - t_k)}
}{
\sum_{k} e^{-\lambda_s (t - t_k)}
}



4. Session Duration Variance

\sigma_{\text{sess}}(i,t) =
\sqrt{
\frac{
\sum_{k}
(d_k - \mu_{\text{sess}})^2
\cdot
e^{-\lambda_s (t - t_k)}
}{
\sum_{k} e^{-\lambda_s (t - t_k)}
}
}



5. Human Reference Values

* \mu_{\text{human}}: average human session duration
* \sigma_{\text{human}}: expected variation


Example

mu_human ≈ 5–20 minutes
sigma_human ≈ moderate variability



6. Deviation Measure

D_{\text{session}}(i,t)


Meaning

* normalized difference from human baseline



7. Final Score

S_{\text{session}}(i,t)


Meaning

* human-like sessions → high score
* abnormal sessions → low score


Variable Definitions


* S_{\text{session}}(i,t) \in [0,1]: session continuity score
* d_k: session duration
* \lambda_s: decay parameter
* \delta: sensitivity constant


Properties


* bounded in [0,1]
* penalizes extreme behavior
* robust to normal variation


Behavior Interpretation


Behavior	Score
normal session patterns	high
slightly irregular	medium
continuous 24/7 activity	low
extremely fragmented	low


Why This Signal Matters


Detects:

* bots running continuously
* scripted periodic behavior
* unnatural usage patterns


Usage in System


Feeds into anomaly ML features:

r_{\text{timing}}(i,t) = S_{\text{session}}(i,t)


Pseudo Insight

Humans take breaks, bots don’t



input_signal — Signal 14

Vote Timing Irregularity Score (Temporal Behavior Signal)


Final Formula

S_{\text{timing}}(i,t) =
\exp\left(
- \frac{\sigma^2_{\Delta t}(i,t)}{\sigma_t^2}
\right)
\cdot
\exp\left(
- \frac{B_i(t)}{B_0}
\right)


Interpretation

This signal measures:

how natural the timing of a user’s actions is.

It captures:

* perfectly regular (bot-like) timing
* synchronized bursts
* unnatural reaction intervals


Component Breakdown


1. Inter-Event Time Differences

\Delta t_k = t_k - t_{k-1}


Meaning

* time gap between consecutive actions



2. Variance of Time Gaps

\sigma^2_{\Delta t}(i,t) =
\frac{
\sum_{k}
(\Delta t_k - \bar{\Delta t})^2
\cdot
e^{-\lambda_t (t - t_k)}
}{
\sum_{k}
e^{-\lambda_t (t - t_k)}
}


3. Mean Time Gap

\bar{\Delta t} =
\frac{
\sum_{k}
\Delta t_k \cdot e^{-\lambda_t (t - t_k)}
}{
\sum_{k}
e^{-\lambda_t (t - t_k)}
}


Meaning

* average delay between user actions



4. Burstiness Measure

B_i(t) =
\frac{
\max_{k \in \mathcal{W}_t} n_k
}{
\bar{n}_i + \epsilon
}


Where

* \mathcal{W}_t: small time bins (e.g., 1 minute windows)
* n_k: number of actions in bin k
* \bar{n}_i: average actions per bin


Meaning

* detects sudden spikes in activity



5. Final Combination

Two penalties:

1. low variance → too regular (bot-like)
2. high burstiness → coordinated/spam behavior


Variable Definitions


* S_{\text{timing}}(i,t) \in [0,1]: timing score
* \Delta t_k: time gaps
* \sigma^2_{\Delta t}: variance of gaps
* B_i(t): burstiness
* \lambda_t: decay parameter
* \sigma_t, B_0: normalization constants


Properties


* bounded in [0,1]
* penalizes:
    * overly regular timing
    * extreme bursts


Behavior Interpretation


Behavior	Score
natural irregular timing	high
slightly structured	medium
perfectly periodic	low
synchronized bursts	low


Why This Is Fully Defined (No Abstraction)

Everything is derived from:

timestamps only

No need for:

* external datasets
* learned distributions
* hidden models


Usage in System


Feeds into anomaly ML:

r_{\text{timing}}(i,t) = S_{\text{timing}}(i,t)


Now Addressing Your Concern Directly

You were correct—some earlier signals can be abstract if implemented loosely. Here is the correction:


Signals That MUST Be Implemented Carefully

1. Navigation Deviation (Signal 10)

Originally abstract → now should be implemented using:

histograms of:
    step length
    angle
    pause time
compare via Jensen-Shannon divergence

No black-box distribution.


2. Category / Keyword Scores

Must be defined as:

keyword → dictionary or TF-IDF weights
category → classifier with explicit output ∈ [0,1]


3. Source Reliability

Must not be static—use:

agreement between sources (GPS vs IP)


Final Status

You now have 14 fully grounded signals, each:

* computable from raw data
* bounded or normalized
* tied directly to formulas


Critical Insight

Your system is now:

signal-complete + mathematically closed

No variable depends on undefined inputs anymore.




Short answer: you are ~95% complete, but not fully closed yet.
There are still a few variables that are either:

* implicitly assumed
* environment-dependent
* or not explicitly mapped to raw data collection

I’ll go through this surgically, not vaguely.


1. What is Fully Defined (No Gaps)

These are safe and computable from raw logs:

✔ User interaction signals

* timestamps t_k
* votes s_k
* post IDs
* interaction counts

✔ Behavioral signals

* S_{\text{rate}}
* S_{\text{entropy}}
* S_{\text{timing}}
* S_{\text{cons}}

All depend only on:

user_id, action_type, timestamp, vote

No ambiguity.


✔ Graph + trust

* adjacency A_{ij}
* trust propagation

Depends only on:

co-interactions + timestamps + votes

Fully computable.


✔ Post-level variables

* N_j(t), S_j(t), C_{Bayes}, Var_j

All derived from:

user weights + interactions

No missing input.


2. Variables That Are Defined BUT Require Explicit Data Collection

These are not undefined—but you must explicitly collect them.


(A) Location Data

Variables:

* l_i(t) (user location)
* l_j (post location)


Required Inputs

GPS coordinates (lat, lon, timestamp)
OR
IP-based geo fallback


Risk

If you don’t collect location:

entire spatial system (Prox, L_i, alerts) breaks



(B) Device Fingerprint

Variables:

* \mathcal{D}_i, device IDs


Required Inputs

user-agent
device_id (hashed)
OS + browser


Risk

Without it:

Signal 11 becomes unusable



(C) IP Data

Variables:

* ip_k, l_{ip}


Required Inputs

IP address per request
Geo-IP mapping


Risk

Without it:

network-level anomaly detection is gone



(D) Content Features

Variables:

* p_j (text)
* keywords \phi(w)
* category Cat_j


Required Inputs

raw post text


Additional Requirement

You must define:

keyword scoring method
category classifier



3. Variables That Still Need Explicit Implementation Decisions

These are not undefined, but not concretely specified yet.


(A) Ground Truth y_j

Used in:

S_{\text{cons}},\; \alpha_i,\; \beta_i


Problem

You never defined:

where truth comes from


Options

manual moderation
fact-check APIs
delayed consensus (majority after stabilization)


Without this:

* reliability becomes weak
* anomaly loses strength



(B) Human Reference Constants

Used in:

* navigation deviation
* session continuity


Variables:

* \mu_{\text{human}}
* \sigma_{\text{human}}
* P_{\text{human}}


Issue

These are:

not raw inputs → must be estimated


Fix

Define:

compute from platform-wide statistics



(C) Hyperparameters

You defined them, but they are not “collected”:

lambda, sigma, tau, alpha, beta, etc.


These require:

* tuning
* validation
* simulation



(D) Similarity Function Sim(j,k) (Memory)

You wrote:

Sim(j,k)


But not concretely:

* cosine over embeddings?
* TF-IDF?


Fix

Define explicitly:

Sim = cosine(embedding_j, embedding_k)



4. Subtle Missing Link (Important)

User Identity Mapping

You assume:

i = \text{user}


But in reality:

You must define:

user_id ↔ device ↔ session ↔ IP


Otherwise:

* signals conflict
* spoofing becomes trivial



5. Final Verdict


Do you have all inputs?

✔ YES (core system)

You can compute:

* credibility
* anomaly
* propagation
* alerts


⚠ PARTIAL (requires infrastructure)

You still need to collect explicitly:

location (GPS/IP)
device fingerprint
IP logs
post text
timestamps (high precision)


⚠ NOT DEFINED (external/system-level)

You must still decide:

ground truth source
human baseline estimation
embedding model for similarity


6. Clean Classification


Fully Ready

* mathematical formulas
* algorithms
* signal definitions


Needs Data Engineering

* location
* device
* IP


Needs System Policy

* truth labeling
* moderation strategy


7. Final Insight (Important)

You are not blocked by math anymore.

You are now at:

data collection + system design phase


8. Direct Answer

Do we have any superficial variable left?

Yes, but only 3 categories:

1. Ground truth y_j (not defined source)
2. Human baseline stats (must be learned)
3. Content similarity definition (must be fixed)

Everything else is:

fully computable from user data

