"""
Simulation Engine — Synthetic Data Generator.

Source: docs/context/simulation_evaluation_framework.md §3–4

Generates:
  - Synthetic users (honest, noisy, adversarial, bot)
  - Synthetic posts (true, false, ambiguous)
  - Simulated interactions (votes with timing patterns)
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
        """Create a bot user (high rate, low entropy, coordinated)."""
        return cls(
            user_type=UserType.BOT,
            p_correct=0.1,
            rate=random.uniform(5.0, 15.0),
            entropy=random.uniform(0.05, 0.2),
            coord_group=group,
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
