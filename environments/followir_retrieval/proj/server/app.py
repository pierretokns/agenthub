from openenv.core.app import create_app
from openenv.core.models import Action, Observation
from datasets import load_dataset
from typing import Optional
import os


class FollowIRAction(Action):
    """Action: submit a query with instruction-following constraint."""
    query_with_instruction: str


class FollowIRObservation(Observation):
    """Observation: document and relevance reward."""
    document: str
    reward: float
    done: bool


class FollowIREnvironment:
    """
    FollowIR dataset environment for instruction-aware RL training only.

    WARNING: This is an RL-only environment. Not suitable for deterministic
    evaluation via prime eval run. Use with: prime rl run configs/followir_baseline.toml

    Configurable via environment variables:
    - FOLLOWIR_DATASET: HF dataset name (default: jhu-clsp/FollowIR-train)
    - FOLLOWIR_SPLIT: data split (default: train)
    """

    def __init__(self):
        self.dataset = None
        self.current_idx = 0
        self.current_example = None
        self.dataset_name = os.getenv("FOLLOWIR_DATASET", "jhu-clsp/FollowIR-train")
        self.dataset_split = os.getenv("FOLLOWIR_SPLIT", "train")
        self._load_data()

    def _load_data(self):
        """Load FollowIR dataset from HF or environment vars."""
        try:
            self.dataset = load_dataset(self.dataset_name, split=self.dataset_split)
        except Exception as e:
            print(f"Warning: Could not load {self.dataset_name}: {e}")
            self.dataset = self._synthetic_dataset()

    def _synthetic_dataset(self):
        """Synthetic FollowIR examples."""
        return [
            {
                "query": "machine learning algorithms",
                "instruction": "only recent papers from 2023+",
                "document": "2023 breakthrough in transformers",
                "label": True,
                "score": 0.9,
            },
            {
                "query": "deep learning",
                "instruction": "avoid tutorials and surveys",
                "document": "comprehensive PyTorch tutorial",
                "label": False,
                "score": 0.2,
            },
            {
                "query": "natural language processing",
                "instruction": "focus on BERT-like models",
                "document": "BERT: Pre-training of Deep Bidirectional Transformers",
                "label": True,
                "score": 0.95,
            },
        ]

    async def reset(self, seed=None, **kwargs) -> FollowIRObservation:
        """Reset to next example."""
        if self.dataset is None:
            self.dataset = self._synthetic_dataset()

        self.current_idx = (self.current_idx + 1) % len(self.dataset)
        self.current_example = self.dataset[self.current_idx]

        # Initial observation: provide document
        return FollowIRObservation(
            document=self.current_example.get("document", ""),
            reward=0.0,
            done=False,
        )

    async def step(self, action: FollowIRAction, **kwargs) -> FollowIRObservation:
        """Process action and return reward."""
        if self.current_example is None:
            await self.reset()

        # Reward = pre-labeled confidence score
        reward = float(self.current_example.get("score", 0.0))

        return FollowIRObservation(
            document=self.current_example.get("document", ""),
            reward=reward,
            done=True,
        )

    @property
    def state(self):
        """Return current environment state."""
        if self.current_example is None:
            return {}
        return {
            "example_idx": self.current_idx,
            "query": self.current_example.get("query"),
            "instruction": self.current_example.get("instruction"),
        }


app = create_app(FollowIREnvironment, FollowIRAction, FollowIRObservation)
