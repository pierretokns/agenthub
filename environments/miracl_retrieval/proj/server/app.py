from openenv.core.app import create_app
from openenv.core.models import Action, Observation
from datasets import load_dataset
from typing import Optional
import os


class MIRACLAction(Action):
    """Action: query string for retrieval."""
    query: str


class MIRACLObservation(Observation):
    """Observation: passages and reward."""
    passages: list[str]
    reward: float
    done: bool


class MIRACLEnvironment:
    """
    MIRACL multilingual retrieval environment for RL training only.

    WARNING: This is an RL-only environment. Not suitable for deterministic
    evaluation via prime eval run. Use with: prime rl run configs/miracl_baseline.toml

    Configurable via environment variables:
    - MIRACL_DATASET: HF dataset name (default: miracl/miracl)
    - MIRACL_LANGUAGE: language code (default: en)
    - MIRACL_SPLIT: data split (default: train)
    """

    def __init__(self):
        self.dataset = None
        self.current_idx = 0
        self.current_example = None
        self.dataset_name = os.getenv("MIRACL_DATASET", "miracl/miracl")
        self.language = os.getenv("MIRACL_LANGUAGE", "en")
        self.dataset_split = os.getenv("MIRACL_SPLIT", "train")
        self._load_data()

    def _load_data(self):
        """Load MIRACL dataset from HF or environment vars."""
        try:
            self.dataset = load_dataset(self.dataset_name, self.language, split=self.dataset_split)
        except Exception as e:
            print(f"Warning: Could not load {self.dataset_name}[{self.language}]: {e}")
            self.dataset = self._synthetic_dataset()

    def _synthetic_dataset(self):
        """Synthetic MIRACL examples."""
        return [
            {
                "query": "what is artificial intelligence",
                "query_id": "q1",
                "positive_passages": [
                    {
                        "docid": "p1",
                        "title": "AI Overview",
                        "text": "Artificial intelligence is the simulation of human intelligence by computer systems",
                    }
                ],
                "negative_passages": [
                    {
                        "docid": "n1",
                        "title": "Machine Parts",
                        "text": "A machine is a device that uses energy to perform a task",
                    }
                ],
            },
            {
                "query": "how do neural networks work",
                "query_id": "q2",
                "positive_passages": [
                    {
                        "docid": "p2",
                        "title": "Neural Networks",
                        "text": "Neural networks are computing systems inspired by biological neural networks",
                    }
                ],
                "negative_passages": [
                    {
                        "docid": "n2",
                        "title": "Biological Neurons",
                        "text": "Neurons are cells that transmit electrical signals in the brain",
                    }
                ],
            },
        ]

    async def reset(self, seed=None, **kwargs) -> MIRACLObservation:
        """Reset to next example."""
        if self.dataset is None:
            self.dataset = self._synthetic_dataset()

        self.current_idx = (self.current_idx + 1) % len(self.dataset)
        self.current_example = self.dataset[self.current_idx]

        # Provide initial context with positive passages
        positive_passages = self.current_example.get("positive_passages", [])
        passages = [p.get("text", p.get("title", "")) for p in positive_passages[:3]]

        return MIRACLObservation(
            passages=passages if passages else ["No passages available"],
            reward=0.0,
            done=False,
        )

    async def step(self, action: MIRACLAction, **kwargs) -> MIRACLObservation:
        """Process action and compute reward."""
        if self.current_example is None:
            await self.reset()

        # Reward: 1.0 if action query mentions positive passage content, else 0.0
        positive_passages = self.current_example.get("positive_passages", [])
        positive_texts = [p.get("text", "").lower() for p in positive_passages]

        action_lower = action.query.lower()
        reward = 1.0 if any(ptext[:30] in action_lower or action_lower in ptext for ptext in positive_texts) else 0.0

        return MIRACLObservation(
            passages=[p.get("text", "") for p in positive_passages[:1]],
            reward=reward,
            done=True,
        )

    @property
    def state(self):
        """Return current state."""
        if self.current_example is None:
            return {}
        return {
            "example_idx": self.current_idx,
            "query": self.current_example.get("query"),
            "language": self.language,
        }


app = create_app(MIRACLEnvironment, MIRACLAction, MIRACLObservation)
