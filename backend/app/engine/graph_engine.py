"""
Graph Engine -- Phase 3 from phase3_system_design.md

Implements:
  - Graph construction: edge weights A_ij (Sec 4)
  - Row normalization: A_norm_ij (Sec 5)
  - Trust propagation: T_i iterative (Sec 6)
  - Coordination detection: Sim(i,j), S_coord(i) (Sec 8)

Pipeline (Sec 9):
  Vote -> Update edges -> Run trust propagation -> Compute coordination -> Update anomaly
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from collections import defaultdict

from app.config import config


@dataclass
class VoteRecord:
    """A vote cast by a user on a post."""

    user_id: str
    post_id: str
    vote: int         # +1 or -1
    timestamp: datetime


@dataclass
class EdgeWeight:
    """Computed edge weight between two users."""

    user_i: str
    user_j: str
    agreement: float       # Agree_ij in [0,1]
    time_similarity: float # TimeSim_ij in [0,1]
    frequency: float       # Freq_ij in [0,1]
    weight: float          # A_ij = w1*Agree + w2*TimeSim + w3*Freq


@dataclass
class GraphState:
    """Complete graph state after computation."""

    edges: dict[str, dict[str, float]]             # user_i -> {user_j -> A_ij}
    normalized_edges: dict[str, dict[str, float]]   # user_i -> {user_j -> A_norm_ij}
    trust_scores: dict[str, float]                  # user_id -> T_i
    coordination_scores: dict[str, float]           # user_id -> S_coord_i
    iterations_converged: int                       # How many iterations to converge


# ──────────────────────────────────────────────────────────
# Sec 4: Graph Construction
# ──────────────────────────────────────────────────────────

def _build_user_post_map(
    votes: list[VoteRecord],
) -> dict[str, dict[str, tuple[int, datetime]]]:
    """
    Build map: user_id -> {post_id -> (vote, timestamp)}.
    """
    user_posts: dict[str, dict[str, tuple[int, datetime]]] = defaultdict(dict)
    for v in votes:
        user_posts[v.user_id][v.post_id] = (v.vote, v.timestamp)
    return dict(user_posts)


def _build_post_users_map(
    votes: list[VoteRecord],
) -> dict[str, list[str]]:
    """
    Build map: post_id -> [user_ids who voted on it].
    """
    post_users: dict[str, list[str]] = defaultdict(list)
    for v in votes:
        if v.user_id not in post_users[v.post_id]:
            post_users[v.post_id].append(v.user_id)
    return dict(post_users)


def compute_edge_weight(
    user_i_votes: dict[str, tuple[int, datetime]],
    user_j_votes: dict[str, tuple[int, datetime]],
    p_max: int,
) -> EdgeWeight | None:
    """
    Compute edge weight A_ij between two users.

    Sec 4.3::

        A_ij = w1*Agree_ij + w2*TimeSim_ij + w3*Freq_ij

    Args:
        user_i_votes: post_id -> (vote, timestamp) for user i
        user_j_votes: post_id -> (vote, timestamp) for user j
        p_max: Maximum shared posts across any pair (for normalization)

    Returns:
        EdgeWeight or None if no shared posts.
    """
    # Find shared posts
    shared_posts = set(user_i_votes.keys()) & set(user_j_votes.keys())
    n_shared = len(shared_posts)

    if n_shared == 0:
        return None

    # Sec 4.3 -- Agreement: Agree_ij = (1/|P_ij|) sum I(s_i == s_j)
    agree_count = 0
    for post_id in shared_posts:
        if user_i_votes[post_id][0] == user_j_votes[post_id][0]:
            agree_count += 1
    agreement = agree_count / n_shared

    # Sec 4.3 -- Time Similarity: TimeSim_ij = (1/|P_ij|) sum exp(-|t_i - t_j| / tau)
    tau = config.graph_tau
    time_sim_sum = 0.0
    for post_id in shared_posts:
        t_i = user_i_votes[post_id][1]
        t_j = user_j_votes[post_id][1]
        dt = abs((t_i - t_j).total_seconds())
        time_sim_sum += math.exp(-dt / tau)
    time_similarity = time_sim_sum / n_shared

    # Sec 4.3 -- Frequency: Freq_ij = |P_ij| / P_max
    frequency = n_shared / max(p_max, 1)

    # Final edge weight
    w1, w2, w3 = config.graph_edge_weights
    weight = w1 * agreement + w2 * time_similarity + w3 * frequency

    return EdgeWeight(
        user_i="",  # Filled by caller
        user_j="",
        agreement=agreement,
        time_similarity=time_similarity,
        frequency=frequency,
        weight=weight,
    )


def build_graph(
    votes: list[VoteRecord],
) -> dict[str, dict[str, float]]:
    """
    Build the full user interaction graph.

    Sec 4: For each pair of users who voted on the same post,
    compute A_ij and keep top-K neighbors per user.

    Returns:
        Adjacency dict: user_i -> {user_j -> A_ij}
    """
    user_posts = _build_user_post_map(votes)
    post_users = _build_post_users_map(votes)
    user_ids = list(user_posts.keys())

    # Compute max shared posts (P_max) for frequency normalization
    # Optimization: compute pairwise shared counts using post_users index
    pair_shared: dict[tuple[str, str], int] = defaultdict(int)
    for post_id, users in post_users.items():
        for i_idx in range(len(users)):
            for j_idx in range(i_idx + 1, len(users)):
                u_i, u_j = users[i_idx], users[j_idx]
                key = (min(u_i, u_j), max(u_i, u_j))
                pair_shared[key] += 1

    p_max = max(pair_shared.values()) if pair_shared else 1

    # Compute edge weights
    edges: dict[str, dict[str, float]] = defaultdict(dict)

    for (u_i, u_j), count in pair_shared.items():
        edge = compute_edge_weight(
            user_posts[u_i],
            user_posts[u_j],
            p_max,
        )
        if edge is not None and edge.weight > config.epsilon:
            edges[u_i][u_j] = edge.weight
            edges[u_j][u_i] = edge.weight

    # Sec 12: Keep only top-K neighbors per user (sparse graph)
    k = config.graph_max_neighbors
    sparse_edges: dict[str, dict[str, float]] = {}
    for uid, neighbors in edges.items():
        sorted_neighbors = sorted(
            neighbors.items(), key=lambda x: x[1], reverse=True
        )[:k]
        sparse_edges[uid] = dict(sorted_neighbors)

    return sparse_edges


# ──────────────────────────────────────────────────────────
# Sec 5: Row Normalization
# ──────────────────────────────────────────────────────────

def normalize_graph(
    edges: dict[str, dict[str, float]],
) -> dict[str, dict[str, float]]:
    """
    Row-normalize the adjacency matrix.

    Sec 5::

        A_norm_ij = A_ij / (sum_k A_ik + eps)
    """
    normalized: dict[str, dict[str, float]] = {}

    for uid, neighbors in edges.items():
        total = sum(neighbors.values()) + config.epsilon
        normalized[uid] = {
            nid: w / total for nid, w in neighbors.items()
        }

    return normalized


# ──────────────────────────────────────────────────────────
# Sec 6: Trust Propagation
# ──────────────────────────────────────────────────────────

def propagate_trust(
    normalized_edges: dict[str, dict[str, float]],
    r_star_scores: dict[str, float],
    all_user_ids: list[str],
) -> tuple[dict[str, float], int]:
    """
    Conservative trust propagation.

    Sec 6.2 (conservative variant)::

        T = R_star
        repeat:
            T_new[i] = lambda_g * neighbor_trust + (1 - lambda_g) * R_i_star
        until convergence

    Key safety rule: network component cannot INCREASE trust beyond
    the user's own R_i_star. It can only decrease. This prevents bots
    from boosting each other.

    Args:
        normalized_edges: Row-normalized adjacency A_norm.
        r_star_scores: R_i_star for each user (base trust).
        all_user_ids: List of all user IDs.

    Returns:
        (trust_scores dict, iterations to converge)
    """
    lambda_g = config.lambda_g
    max_iter = config.graph_propagation_iterations
    conv_eps = config.graph_convergence_epsilon

    # Initialize: T = R*
    trust: dict[str, float] = {}
    for uid in all_user_ids:
        trust[uid] = r_star_scores.get(uid, 0.5)

    for iteration in range(max_iter):
        new_trust: dict[str, float] = {}
        max_delta = 0.0

        for uid in all_user_ids:
            r_star = r_star_scores.get(uid, 0.5)
            neighbors = normalized_edges.get(uid, {})

            if not neighbors:
                # No neighbors: trust = R_i*
                new_trust[uid] = r_star
                continue

            # Network component: weighted average of neighbor trust
            network_sum = 0.0
            for nid, a_norm in neighbors.items():
                network_sum += a_norm * trust.get(nid, 0.0)

            # T_i = lambda_g * network + (1 - lambda_g) * R_i_star
            t_new = lambda_g * network_sum + (1.0 - lambda_g) * r_star

            # SAFETY: network can only pull trust DOWN, never above R_i*
            # This prevents bot clusters from boosting each other
            t_new = min(t_new, r_star)

            # Clamp to [0, 1]
            t_new = min(max(t_new, 0.0), 1.0)

            new_trust[uid] = t_new
            max_delta = max(max_delta, abs(t_new - trust.get(uid, 0.5)))

        trust = new_trust

        # Check convergence
        if max_delta < conv_eps:
            return trust, iteration + 1

    return trust, max_iter


# ──────────────────────────────────────────────────────────
# Sec 8: Coordination Detection
# ──────────────────────────────────────────────────────────

def compute_pairwise_similarity(
    user_i_votes: dict[str, tuple[int, datetime]],
    user_j_votes: dict[str, tuple[int, datetime]],
) -> float:
    """
    Sec 8.1: Pairwise coordination similarity.

    Measures two separate signals:
      1. Agreement rate: how often users vote the same way
      2. Timing sync: how close in time their votes are

    ``Sim(i,j) = agreement_rate * timing_sync``

    This catches bots who vote the same way AND at similar times.
    Honest users who agree but vote hours apart get low similarity.
    """
    shared_posts = set(user_i_votes.keys()) & set(user_j_votes.keys())
    n_shared = len(shared_posts)

    if n_shared < 2:  # Need at least 2 shared posts for meaningful similarity
        return 0.0

    # Component 1: Agreement rate
    agree_count = 0
    for post_id in shared_posts:
        if user_i_votes[post_id][0] == user_j_votes[post_id][0]:
            agree_count += 1
    agreement_rate = agree_count / n_shared

    # Component 2: Timing synchronization
    # Use a wider window (10 minutes) to catch bot patterns
    timing_window = 600.0  # 10 minutes
    sync_count = 0
    for post_id in shared_posts:
        t_i = user_i_votes[post_id][1]
        t_j = user_j_votes[post_id][1]
        dt = abs((t_i - t_j).total_seconds())
        if dt < timing_window:
            sync_count += 1
    timing_sync = sync_count / n_shared

    # Combined: high agreement AND timing sync = coordinated
    similarity = agreement_rate * timing_sync

    # Amplify by frequency — more shared posts = more evidence
    freq_factor = min(n_shared / 5.0, 1.0)  # Saturates at 5 shared posts
    similarity *= freq_factor

    return min(similarity, 1.0)


def compute_coordination_scores(
    votes: list[VoteRecord],
    edges: dict[str, dict[str, float]],
) -> dict[str, float]:
    """
    Sec 8.2: Coordination score for each user.

    ``S_coord_i = average of top-3 similarities to neighbors``

    Using average of top-K instead of max reduces noise from
    honest users who happen to agree with one neighbor.
    Coordinated bots will have MULTIPLE high-similarity neighbors.
    """
    user_posts = _build_user_post_map(votes)
    coordination: dict[str, float] = {}

    top_k = 3  # Average over top-3 most similar neighbors

    for uid, neighbors in edges.items():
        if uid not in user_posts:
            coordination[uid] = 0.0
            continue

        similarities = []
        for nid in neighbors:
            if nid not in user_posts:
                continue
            sim = compute_pairwise_similarity(
                user_posts[uid],
                user_posts[nid],
            )
            similarities.append(sim)

        if similarities:
            # Sort descending, take top-K, average
            similarities.sort(reverse=True)
            top_sims = similarities[:top_k]
            coordination[uid] = sum(top_sims) / len(top_sims)
        else:
            coordination[uid] = 0.0

    # Users with no edges get 0.0
    for uid in user_posts:
        if uid not in coordination:
            coordination[uid] = 0.0

    return coordination


# ──────────────────────────────────────────────────────────
# Full Graph Pipeline (Sec 9)
# ──────────────────────────────────────────────────────────

def run_graph_pipeline(
    votes: list[VoteRecord],
    r_star_scores: dict[str, float],
) -> GraphState:
    """
    Full Phase 3 graph pipeline.

    CRITICAL ORDER (Sec 8.4 + Sec 9)::

        1. Build graph edges A_ij
        2. Detect coordination -> S_coord_i
        3. Dampen edges FROM coordinated users
        4. Penalize R_i_star for coordinated users
        5. Normalize dampened graph -> A_norm_ij
        6. Propagate trust using penalized base scores -> T_i

    This ensures coordinated bots can neither contribute trust
    through edges NOR start with high base trust.

    Args:
        votes: All vote records in the system.
        r_star_scores: R_i_star for each user.

    Returns:
        GraphState with edges, trust, and coordination scores.
    """
    all_user_ids = list(set(
        list(r_star_scores.keys()) + [v.user_id for v in votes]
    ))

    # Step 1: Build graph
    edges = build_graph(votes)

    # Step 2: Coordination detection (BEFORE trust propagation)
    coordination_scores = compute_coordination_scores(votes, edges)

    # Step 3: Dampen edges FROM coordinated users
    # A coordinated user's outgoing edges get reduced by (1 - S_coord)
    dampened_edges: dict[str, dict[str, float]] = {}
    for uid, neighbors in edges.items():
        s_coord = coordination_scores.get(uid, 0.0)
        dampen_factor = 1.0 - s_coord
        dampened_edges[uid] = {
            nid: w * dampen_factor for nid, w in neighbors.items()
        }

    # Step 4: Penalize R_i* for coordinated users
    penalized_r_star: dict[str, float] = {}
    for uid in all_user_ids:
        r_star = r_star_scores.get(uid, 0.5)
        s_coord = coordination_scores.get(uid, 0.0)
        penalized_r_star[uid] = r_star * (1.0 - s_coord)

    # Step 5: Normalize dampened graph
    normalized = normalize_graph(dampened_edges)

    # Step 6: Trust propagation with penalized base scores
    trust_scores, iterations = propagate_trust(
        normalized, penalized_r_star, all_user_ids
    )

    return GraphState(
        edges=edges,
        normalized_edges=normalized,
        trust_scores=trust_scores,
        coordination_scores=coordination_scores,
        iterations_converged=iterations,
    )
