Purpose

Define the minimum and complete set of raw inputs required to compute all signals, mathematical formulas, and algorithms in the system.

This document ensures:

every variable used in the system is traceable to a concrete, collectable data field.



1. Core Principle

All computations in the system must originate from:

User Event Logs

Each event must be recorded in a structured format.



2. Unified Event Schema

Every interaction generates one event:

{
  "event_id": "uuid",
  "user_id": "string",
  "post_id": "string",
  "event_type": "vote | post | view | share",
  "vote": -1 | 0 | +1,
  "timestamp": "unix_ms",
  "location": {
    "lat": float,
    "lon": float,
    "accuracy": float,
    "source": "gps | wifi | ip | unknown"
  },
  "device": {
    "device_id": "hashed_id",
    "user_agent": "string",
    "os": "string",
    "browser": "string"
  },
  "network": {
    "ip": "string",
    "ip_geo": {
      "lat": float,
      "lon": float,
      "country": "string"
    }
  },
  "content": {
    "text": "string (only for post events)"
  }
}



3. Mapping: Raw Data → Signals



3.1 Location-Based Signals



Required Fields

location.lat
location.lon
timestamp



Used In

* GPS consistency
* speed plausibility
* movement continuity
* location inconsistency
* proximity



Collection Method

Frontend:
    navigator.geolocation API
Backend fallback:
    IP-based geo lookup



Demo Simplification

If GPS unavailable:
    use ip_geo only





3.2 Device Fingerprint



Required Fields

device.device_id
device.user_agent
device.os
device.browser



Used In

* device consistency score



Collection Method

Generate device_id = hash(user_agent + screen + random_seed)



Demo Simplification

Use only user_agent hash





3.3 Network / IP Data



Required Fields

network.ip
network.ip_geo



Used In

* IP consistency
* location cross-validation



Collection Method

Backend:
    extract IP from request
    use GeoIP database





3.4 Temporal Data



Required Fields

timestamp (high precision)



Used In

* rate deviation
* entropy
* timing irregularity
* session continuity



Requirement

millisecond precision preferred





3.5 Interaction Data



Required Fields

event_type
vote
post_id
user_id



Used In

* credibility
* anomaly
* graph construction





3.6 Content Data



Required Fields

content.text



Used In

* urgency (keywords)
* category classification
* ML credibility



Demo Simplification

Use keyword dictionary instead of ML





4. Derived Data (Computed, Not Collected)



4.1 Ground Truth y_j



For Demo

y_j = majority_vote_after_threshold



Rule

if N_j > threshold AND Var_j < limit:
    y_j = sign(S_j)





4.2 Human Baselines



For Demo

Use fixed constants:

mu_human_session = 10 minutes
sigma_human_session = 5 minutes
v_max = 50 m/s





4.3 Keyword Scores



Define Dictionary

{
  "fire": 1.0,
  "accident": 0.9,
  "urgent": 0.8,
  "help": 0.7
}





4.4 Category Score



Demo Rule

if keyword_score > threshold:
    Cat_j = 1
else:
    Cat_j = 0.3





4.5 Similarity Function



Define

Sim(j,k) = cosine(TF-IDF(j), TF-IDF(k))





5. Minimum Viable Data (For Demo)

If you want to simplify system:



Collect Only

user_id
post_id
vote
timestamp
text
ip



Optional

location (if available)
device_id (basic)





6. Data Flow Pipeline



User Action
    ↓
Frontend collects:
    location + device + action
    ↓
Backend enriches:
    IP + geo
    ↓
Store in Event Log DB
    ↓
Signal Computation Layer
    ↓
Mathematical Engine
    ↓
Propagation + Alerts





7. Storage Recommendation



Primary DB

PostgreSQL (structured data)



Cache

Redis (real-time signals)



Optional

Vector DB (for similarity)





8. Critical Constraints



Consistency

user_id must be stable across sessions



Privacy (Important)

hash device_id
do not store raw sensitive data





