
1. Objective of Phase 4

Upgrade system from:

network-aware credibility

to:

spatially-aware information system with localized relevance and alerts



2. What Phase 4 Adds



Core Additions

User location tracking L_i(t)
Location confidence modeling
Post location modeling l_j
Proximity function Prox(u,j,t)
Spatial filtering in alerts
Spatial trust aggregation



Still NOT included

ML content models
Memory similarity
Advanced NLP



3. Core Idea

A post should not be shown or alerted globally just because it is credible.

It must also satisfy:

“Is this relevant to this user’s location?”



4. User Location Model



4.1 Raw Location

l_i(t) = (\text{lat}, \text{lon})

Collected from:

* GPS (preferred)
* IP (fallback)





4.2 Location Confidence



Formula

L_i(t) =
w_1 S_{\text{gps}}
+
w_2 S_{\text{speed}}
+
w_3 S_{\text{source}}
+
w_4 S_{\text{cont}}



Meaning

* aggregates all location trust signals
* outputs value in [0,1]





4.3 Interpretation

High L_i → location is reliable
Low L_i → location is suspicious



5. Post Location



Definition

l_j = \text{location where event occurred}



Collection Options

User-provided location
OR
location inferred from first trusted users





Fallback Strategy

if post has no location:
    estimate l_j = weighted avg of user locations



6. Proximity Function



Formula

Prox(u,j,t) =
L_u(t)
\cdot
\exp\left(
-\frac{d(u,j)^2}{2\sigma_p^2}
\right)



Meaning

* combines:
    * geographic distance
    * trust in location





7. Spatial Trust of Post



Formula

\bar{L}_j(t) =
\frac{
\sum w_i \cdot L_i \cdot e^{-\lambda (t - t_k)}
}{
\sum w_i \cdot e^{-\lambda (t - t_k)}
}



Meaning

* average location reliability of contributors





8. Updated Propagation Condition



Phase 4 Expand Rule

Expand(j,t) =
\mathbb{I}\Big(
C_j \ge \theta
\;\wedge\;
N_j \ge N_{min}
\;\wedge\;
Var_j \le \sigma^2
\;\wedge\;
\bar{L}_j \ge L_{min}
\Big)





9. Updated Alert Function



Phase 4 Alert

Alert(u,j,t) =
\mathbb{I}\Big(
Prox(u,j,t) \ge \tau_p
\;\wedge\;
C_j \ge \theta_{alert}
\;\wedge\;
Var_j \le \sigma^2
\Big)





10. Pipeline (Phase 4)



User action
    ↓
Collect location + compute L_i
    ↓
Update user + graph (Phase 3)
    ↓
Update post credibility
    ↓
Compute post location l_j
    ↓
Compute:
    Prox(u,j,t)
    L̄_j(t)
    ↓
Propagation decision
    ↓
User-specific alert decision





11. What Phase 4 Solves



Problem 1: Irrelevant Alerts

Global alerts for local events

Solution:

Prox(u,j,t) filters by distance





Problem 2: Location Spoofing

Fake location reports

Solution:

Low L_i → low influence





Problem 3: Regional Trust

Users far away influencing local events

Solution:

Proximity reduces their impact





12. Backend Changes



User Table Update

ALTER TABLE users ADD COLUMN:
    lat FLOAT,
    lon FLOAT,
    location_conf FLOAT





Post Table Update

ALTER TABLE posts ADD COLUMN:
    lat FLOAT,
    lon FLOAT,
    location_conf FLOAT





Location Update API

POST /location
{
  "user_id": "u1",
  "lat": 12.34,
  "lon": 56.78
}





13. Optimization Strategy



Spatial Indexing

Use:
    PostGIS
    OR
    geo-hash indexing





Filtering

only compute Prox for posts within radius R





14. Hyperparameters (Phase 4)



sigma_p     → spatial decay
tau_p       → proximity threshold
L_min       → location trust threshold





15. What to Test



Test 1: Local Event

Fire in one city

Expect:

Nearby users → alerted
Far users → ignored





Test 2: Spoofed Location

User jumps locations

Expect:

L_i ↓ → influence ↓





Test 3: Mixed Users

Local + remote users voting

Expect:

local trusted users dominate





16. Phase 4 Summary



Phase 3: “network matters”
Phase 4: “location matters”





17. System Evolution



Phase	Capability
MVP	basic
Phase 2	user-aware
Phase 3	network-aware
Phase 4	geo-aware





18. Final Insight

After Phase 4, your system becomes:

context-sensitive and regionally intelligent

This is what makes it usable in:

* emergency systems
* local information platforms
* real-time event detection


