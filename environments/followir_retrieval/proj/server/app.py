from openenv.core.app import create_app
from openenv.core.models import Action, Observation
from datasets import load_dataset
from typing import Optional


class FollowIRAction(Action):
    """Action: submit a query with instruction-following constraint."""
    query_with_instruction: str


class FollowIRObservation(Observation):
    """Observation: document and relevance reward."""
    document: str
    reward: float
    done: bool


class FollowIREnvironment:
    """FollowIR dataset environment for instruction-aware retrieval."""

    def __init__(self):
        self.dataset = None
        self.current_idx = 0
        self.current_example = None
        self._load_data()

    def _load_data(self):
        """Load FollowIR dataset."""
        try:
            self.dataset = load_dataset("jhu-clsp/FollowIR-train", split="train")
        except Exception as e:
            print(f"Warning: Could not load FollowIR: {e}")
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
