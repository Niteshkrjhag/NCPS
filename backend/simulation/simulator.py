"""
Simulation Engine — Synthetic Data Generator.

Source: docs/context/simulation_evaluation_framework.md §3–4
        docs/context/phase4_system_design.md §4–5

Generates:
  - Synthetic users (honest, noisy, adversarial, bot)
  - Synthetic posts (true, false, ambiguous)
  - Simulated interactions (votes with timing patterns)
  - Location histories with spoofing patterns (Phase 4)
"""

from __future__ import annotations

import random
import uuid
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum


class UserType(Enum):
    """User behavioral types from simulation_evaluation_framework.md §3.1"""
    HONEST = "honest"
    NOISY = "noisy"
    ADVERSARIAL = "adversarial"
    BOT = "bot"


class PostLabel(Enum):
    """Post ground truth labels from simulation_evaluation_framework.md §3.3"""
    TRUE = 1
    FALSE = -1
    AMBIGUOUS = 0


@dataclass
class SimulatedUser:
    """A synthetic user with behavioral parameters."""

    user_id: uuid.UUID = field(default_factory=uuid.uuid4)
    user_type: UserType = UserType.HONEST

    # Behavioral parameters (from §3.2)
    p_correct: float = 0.9       # Probability of correct vote
    rate: float = 1.0            # Actions per minute
    entropy: float = 0.8         # Action diversity
    coord_group: int | None = None  # Group for coordination
    location_spoofing: bool = False  # Phase 4: does user spoof location?
    lat: float = 0.0
    lon: float = 0.0

    @classmethod
    def honest(cls, lat: float = 0.0, lon: float = 0.0) -> SimulatedUser:
        """Create an honest user (p_correct ≈ 0.9)."""
        return cls(
            user_type=UserType.HONEST,
            p_correct=random.uniform(0.8, 0.95),
            rate=random.uniform(0.5, 2.0),
            entropy=random.uniform(0.6, 0.9),
            lat=lat + random.gauss(0, 0.01),
            lon=lon + random.gauss(0, 0.01),
        )

    @classmethod
    def noisy(cls, lat: float = 0.0, lon: float = 0.0) -> SimulatedUser:
        """Create a noisy user (p_correct ≈ 0.5)."""
        return cls(
            user_type=UserType.NOISY,
            p_correct=random.uniform(0.4, 0.6),
            rate=random.uniform(0.3, 1.5),
            entropy=random.uniform(0.5, 0.8),
            lat=lat + random.gauss(0, 0.02),
            lon=lon + random.gauss(0, 0.02),
        )

    @classmethod
    def adversarial(cls, lat: float = 0.0, lon: float = 0.0) -> SimulatedUser:
        """Create an adversarial user (p_correct ≈ 0.1)."""
        return cls(
            user_type=UserType.ADVERSARIAL,
            p_correct=random.uniform(0.05, 0.15),
            rate=random.uniform(1.0, 3.0),
            entropy=random.uniform(0.2, 0.5),
            lat=lat + random.gauss(0, 0.05),
            lon=lon + random.gauss(0, 0.05),
        )

    @classmethod
    def bot(cls, group: int, lat: float = 0.0, lon: float = 0.0) -> SimulatedUser:
        """Create a bot user (high rate, low entropy, coordinated, location spoofing)."""
        return cls(
            user_type=UserType.BOT,
            p_correct=0.1,
            rate=random.uniform(5.0, 15.0),
            entropy=random.uniform(0.05, 0.2),
            coord_group=group,
            location_spoofing=True,  # Phase 4: bots spoof location
            lat=lat + random.gauss(0, 0.1),
            lon=lon + random.gauss(0, 0.1),
        )


@dataclass
class SimulatedPost:
    """A synthetic post with ground truth."""

    post_id: uuid.UUID = field(default_factory=uuid.uuid4)
    author_id: uuid.UUID = field(default_factory=uuid.uuid4)
    content: str = ""
    label: PostLabel = PostLabel.TRUE
    difficulty: float = 0.5     # How hard to classify (0 = easy, 1 = hard)
    lat: float = 0.0
    lon: float = 0.0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class SimulatedInteraction:
    """A simulated vote event."""

    user_id: uuid.UUID
    post_id: uuid.UUID
    vote: int           # +1 or -1
    timestamp: datetime
    is_correct: bool     # Whether vote matches ground truth


class Simulator:
    """
    Generates synthetic users, posts, and interactions.
    Source: simulation_evaluation_framework.md §4
    """

    def __init__(
        self,
        num_honest: int = 50,
        num_noisy: int = 10,
        num_adversarial: int = 5,
        num_bots: int = 10,
        bot_groups: int = 2,
        num_true_posts: int = 30,
        num_false_posts: int = 20,
        center_lat: float = 28.6139,  # Delhi
        center_lon: float = 77.2090,
        seed: int | None = 42,
    ):
        if seed is not None:
            random.seed(seed)

        self.center_lat = center_lat
        self.center_lon = center_lon

        # Generate users
        self.users: list[SimulatedUser] = []
        for _ in range(num_honest):
            self.users.append(SimulatedUser.honest(center_lat, center_lon))
        for _ in range(num_noisy):
            self.users.append(SimulatedUser.noisy(center_lat, center_lon))
        for _ in range(num_adversarial):
            self.users.append(SimulatedUser.adversarial(center_lat, center_lon))
        for i in range(num_bots):
            group = i % bot_groups
            self.users.append(SimulatedUser.bot(group, center_lat, center_lon))

        # Generate posts
        self.posts: list[SimulatedPost] = []
        urgent_words = ["fire", "accident", "emergency", "danger", "flood"]
        normal_words = ["update", "news", "report", "information", "local"]

        for i in range(num_true_posts):
            words = random.choices(normal_words, k=5) + random.choices(urgent_words, k=random.randint(0, 2))
            random.shuffle(words)
            self.posts.append(SimulatedPost(
                author_id=random.choice(self.users).user_id,
                content=" ".join(words),
                label=PostLabel.TRUE,
                difficulty=random.uniform(0.2, 0.7),
                lat=center_lat + random.gauss(0, 0.02),
                lon=center_lon + random.gauss(0, 0.02),
            ))

        for i in range(num_false_posts):
            words = random.choices(urgent_words, k=3) + random.choices(normal_words, k=3)
            random.shuffle(words)
            self.posts.append(SimulatedPost(
                author_id=random.choice(self.users).user_id,
                content=" ".join(words),
                label=PostLabel.FALSE,
                difficulty=random.uniform(0.4, 0.9),
                lat=center_lat + random.gauss(0, 0.03),
                lon=center_lon + random.gauss(0, 0.03),
            ))

    def generate_interactions(
        self,
        time_steps: int = 100,
        interactions_per_step: int = 10,
    ) -> list[SimulatedInteraction]:
        """
        Generate interaction stream.
        Source: simulation_evaluation_framework.md §4

        For each time step:
          - Sample users based on activity rate
          - Generate votes based on user type and post truth
          - Bots in same group target same posts (coordinated attack)
        """
        interactions: list[SimulatedInteraction] = []
        base_time = datetime.now(timezone.utc) - timedelta(minutes=time_steps)

        # Pre-assign bot group targets: each bot group targets specific false posts
        false_posts = [p for p in self.posts if p.label == PostLabel.FALSE]
        all_posts_for_bots = self.posts  # Fallback
        bot_group_targets: dict[int, list[SimulatedPost]] = {}

        if false_posts:
            # Split false posts across bot groups
            bot_groups = set(
                u.coord_group for u in self.users
                if u.user_type == UserType.BOT and u.coord_group is not None
            )
            for group_id in bot_groups:
                # Each group targets a specific subset of false posts + some true posts to attack
                n_targets = max(len(false_posts) // max(len(bot_groups), 1), 3)
                target_false = false_posts[:n_targets] if group_id == 0 else \
                    false_posts[min(group_id * n_targets, len(false_posts) - 1):][:n_targets]
                # Also target some true posts to undermine them
                true_posts = [p for p in self.posts if p.label == PostLabel.TRUE]
                target_true = true_posts[:n_targets] if true_posts else []
                bot_group_targets[group_id] = target_false + target_true

        for t in range(time_steps):
            current_time = base_time + timedelta(minutes=t)

            # Sample users weighted by activity rate
            weights = [u.rate for u in self.users]
            total_weight = sum(weights)
            probs = [w / total_weight for w in weights]

            selected_users = random.choices(
                self.users, weights=probs, k=interactions_per_step
            )

            for user in selected_users:
                # Select post based on user type
                if user.user_type == UserType.BOT and user.coord_group is not None:
                    # Bots target their assigned posts (coordinated)
                    targets = bot_group_targets.get(user.coord_group, self.posts)
                    post = random.choice(targets) if targets else random.choice(self.posts)
                else:
                    # Normal users pick any post
                    post = random.choice(self.posts)

                # Generate vote based on user type (§4.3)
                vote = self._generate_vote(user, post)
                is_correct = (vote == post.label.value) if post.label != PostLabel.AMBIGUOUS else True

                # Add timing jitter
                jitter = timedelta(seconds=random.uniform(0, 59))
                if user.user_type == UserType.BOT:
                    # Bots are more synchronized (§4.5)
                    jitter = timedelta(seconds=random.uniform(0, 5))

                interactions.append(SimulatedInteraction(
                    user_id=user.user_id,
                    post_id=post.post_id,
                    vote=vote,
                    timestamp=current_time + jitter,
                    is_correct=is_correct,
                ))

        return interactions

    def generate_location_history(
        self,
        time_steps: int = 100,
        readings_per_step: int = 1,
    ) -> dict[str, list[dict]]:
        """
        Generate location history for all users.
        Phase 4: phase4_system_design.md §4

        Honest users: stable locations near their origin.
        Bots: teleport between distant locations (spoofing).
        Adversarial: occasionally jump to random locations.

        Returns:
            dict: user_id -> list of {lat, lon, timestamp, accuracy, source}
        """
        base_time = datetime.now(timezone.utc) - timedelta(minutes=time_steps)
        histories: dict[str, list[dict]] = {}

        # Distant cities for bot teleportation
        spoof_locations = [
            (28.6139, 77.2090),   # Delhi
            (19.0760, 72.8777),   # Mumbai
            (13.0827, 80.2707),   # Chennai
            (22.5726, 88.3639),   # Kolkata
            (40.7128, -74.0060),  # New York
            (51.5074, -0.1278),   # London
        ]

        for user in self.users:
            uid = str(user.user_id)
            history = []

            for t in range(0, time_steps, max(time_steps // (readings_per_step * 10), 1)):
                current_time = base_time + timedelta(minutes=t)

                if user.location_spoofing:
                    # Bots: teleport between distant cities
                    if random.random() < 0.3:  # 30% chance of teleport per reading
                        spoof_lat, spoof_lon = random.choice(spoof_locations)
                        lat = spoof_lat + random.gauss(0, 0.01)
                        lon = spoof_lon + random.gauss(0, 0.01)
                    else:
                        lat = user.lat + random.gauss(0, 0.05)
                        lon = user.lon + random.gauss(0, 0.05)
                    accuracy = random.uniform(100, 500)  # Poor GPS accuracy
                    source = random.choice(["ip", "ip", "gps"])  # Mostly IP
                elif user.user_type == UserType.ADVERSARIAL:
                    # Adversarial: occasional jumps
                    if random.random() < 0.1:
                        lat = user.lat + random.gauss(0, 0.5)
                        lon = user.lon + random.gauss(0, 0.5)
                    else:
                        lat = user.lat + random.gauss(0, 0.01)
                        lon = user.lon + random.gauss(0, 0.01)
                    accuracy = random.uniform(20, 150)
                    source = "gps"
                else:
                    # Honest / Noisy: stable near origin
                    lat = user.lat + random.gauss(0, 0.005)
                    lon = user.lon + random.gauss(0, 0.005)
                    accuracy = random.uniform(5, 50)  # Good GPS
                    source = "gps"

                history.append({
                    "lat": lat,
                    "lon": lon,
                    "timestamp": current_time,
                    "accuracy": accuracy,
                    "source": source,
                })

            histories[uid] = history

        return histories

    def generate_user_metadata(
        self,
        interactions: list[SimulatedInteraction],
    ) -> dict[str, dict]:
        """
        Generate Phase 6 metadata: device fingerprints, IP addresses, session data.

        Honest users: 1-2 stable devices, 1-3 stable IPs, natural session gaps.
        Bots: 3-8 rotating devices, 5-15 rotating IPs, continuous sessions.

        Returns:
            dict[user_id] -> {
                "device_ids": list[str],
                "ip_addresses": list[str],
                "ip_locations": list[tuple[lat, lon]],
                "timestamps": list[float],
            }
        """
        metadata: dict[str, dict] = {}

        # Pre-generate device/IP pools per user
        user_devices: dict[str, list[str]] = {}
        user_ips: dict[str, list[str]] = {}
        user_ip_locs: dict[str, list[tuple[float, float]]] = {}

        for user in self.users:
            uid = str(user.user_id)

            if user.user_type in (UserType.HONEST, UserType.NOISY):
                # Stable: 1-2 devices, 1-3 IPs near their location
                n_devices = random.randint(1, 2)
                n_ips = random.randint(1, 3)
                user_devices[uid] = [f"dev_{uid[:8]}_{i}" for i in range(n_devices)]
                user_ips[uid] = [f"192.168.{random.randint(1,255)}.{random.randint(1,255)}"
                                 for _ in range(n_ips)]
                user_ip_locs[uid] = [
                    (user.lat + random.gauss(0, 0.005), user.lon + random.gauss(0, 0.005))
                    for _ in range(n_ips)
                ]
            elif user.user_type == UserType.ADVERSARIAL:
                # Moderate rotation: 2-4 devices, 3-6 IPs
                n_devices = random.randint(2, 4)
                n_ips = random.randint(3, 6)
                user_devices[uid] = [f"dev_{uid[:8]}_{i}" for i in range(n_devices)]
                user_ips[uid] = [f"10.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"
                                 for _ in range(n_ips)]
                user_ip_locs[uid] = [
                    (user.lat + random.gauss(0, 0.1), user.lon + random.gauss(0, 0.1))
                    for _ in range(n_ips)
                ]
            else:  # BOT
                # Heavy rotation: 3-8 devices, 5-15 IPs with geographic spread
                n_devices = random.randint(3, 8)
                n_ips = random.randint(5, 15)
                user_devices[uid] = [f"bot_{random.randint(1000,9999)}_{i}" for i in range(n_devices)]
                user_ips[uid] = [f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"
                                 for _ in range(n_ips)]
                # Bots: IPs from all over the world (large geographic spread)
                user_ip_locs[uid] = [
                    (random.uniform(-60, 60), random.uniform(-180, 180))
                    for _ in range(n_ips)
                ]

        # Collect per-user interaction data
        user_inter: dict[str, list[SimulatedInteraction]] = {}
        for inter in interactions:
            uid = str(inter.user_id)
            if uid not in user_inter:
                user_inter[uid] = []
            user_inter[uid].append(inter)

        for user in self.users:
            uid = str(user.user_id)
            inters = user_inter.get(uid, [])

            # Assign device/IP per interaction (rotating for bots)
            devices_pool = user_devices.get(uid, ["unknown"])
            ips_pool = user_ips.get(uid, ["0.0.0.0"])
            ip_locs_pool = user_ip_locs.get(uid, [(0.0, 0.0)])

            device_ids = []
            ip_addrs = []
            ip_locs = []
            timestamps = []

            for i, inter in enumerate(inters):
                if user.user_type == UserType.BOT:
                    # Bots rotate through devices/IPs
                    device_ids.append(devices_pool[i % len(devices_pool)])
                    ip_idx = i % len(ips_pool)
                    ip_addrs.append(ips_pool[ip_idx])
                    ip_locs.append(ip_locs_pool[ip_idx % len(ip_locs_pool)])
                else:
                    # Honest/noisy: mostly use primary device
                    device_ids.append(devices_pool[0] if random.random() < 0.85 else random.choice(devices_pool))
                    ip_addrs.append(ips_pool[0] if random.random() < 0.8 else random.choice(ips_pool))
                    ip_locs.append(ip_locs_pool[0])

                timestamps.append(inter.timestamp.timestamp())

            metadata[uid] = {
                "device_ids": device_ids,
                "ip_addresses": ip_addrs,
                "ip_locations": ip_locs,
                "timestamps": timestamps,
            }

        return metadata

    def _generate_vote(self, user: SimulatedUser, post: SimulatedPost) -> int:
        """Generate a vote based on user type and post truth."""
        if post.label == PostLabel.AMBIGUOUS:
            return random.choice([-1, 1])

        truth = post.label.value  # +1 or -1
        difficulty_factor = 1.0 - (post.difficulty * 0.3)
        effective_p = user.p_correct * difficulty_factor

        if user.user_type == UserType.HONEST:
            return truth if random.random() < effective_p else -truth

        elif user.user_type == UserType.NOISY:
            return random.choice([-1, 1])

        elif user.user_type == UserType.ADVERSARIAL:
            # Intentionally vote wrong
            return -truth if random.random() < effective_p else truth

        elif user.user_type == UserType.BOT:
            # Coordinated: always vote to make false posts look true
            if post.label == PostLabel.FALSE:
                return 1  # Make false look credible
            else:
                return -1  # Undermine true posts

        return random.choice([-1, 1])
