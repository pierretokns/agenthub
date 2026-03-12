from openenv.core.app import create_app
from openenv.core.models import Action, Observation
from datasets import load_dataset
from typing import Optional
import json
import os


class QueryAction(Action):
    """Action: submit a query for retrieval."""
    query: str


class RetrievalObservation(Observation):
    """Observation: passages retrieved and reward signal."""
    passages: list[str]
    reward: float
    done: bool


class BrightEnvironment:
    """
    BRIGHT dataset environment for RL training only.

    WARNING: This is an RL-only environment. Not suitable for deterministic
    evaluation via prime eval run. Use with: prime rl run configs/bright_baseline.toml

    Configurable via environment variables:
    - BRIGHT_DATASET: HF dataset name (default: google-research-datasets/BRIGHT)
    - BRIGHT_CONFIG: dataset config (default: gpt4_reason)
    - BRIGHT_SPLIT: data split (default: examples)
    """

    def __init__(self):
        self.dataset = None
        self.current_idx = 0
        self.current_example = None
        self.corpus = {}
        self.dataset_name = os.getenv("BRIGHT_DATASET", "google-research-datasets/BRIGHT")
        self.dataset_config = os.getenv("BRIGHT_CONFIG", "gpt4_reason")
        self._load_data()

    def _load_data(self):
        """Load BRIGHT dataset and corpus from HF or environment vars."""
        try:
            # Load examples (queries with gold passages)
            examples = load_dataset(self.dataset_name, "examples", split=None)
            self.dataset = examples[self.dataset_config] if self.dataset_config in examples else examples

            # Load corpus
            corpus_data = load_dataset(self.dataset_name, "documents", split=None)
            corpus_split = corpus_data["default"] if "default" in corpus_data else corpus_data

            for doc in corpus_split:
                doc_id = doc.get("id", str(len(self.corpus)))
                self.corpus[doc_id] = doc.get("content", "")
        except Exception as e:
            # Fallback to synthetic data
            print(f"Warning: Could not load {self.dataset_name}: {e}")
            self.dataset = self._synthetic_dataset()
            self.corpus = self._synthetic_corpus()

    def _synthetic_dataset(self):
        """Synthetic BRIGHT examples."""
        return [
            {
                "query": "how does photosynthesis work",
                "gold_ids": ["d1"],
                "gold_answer": "photosynthesis is the process by which plants convert light into chemical energy",
            },
            {
                "query": "what are neural networks",
                "gold_ids": ["d2"],
                "gold_answer": "neural networks are computational models inspired by biological neural networks",
            },
        ]

    def _synthetic_corpus(self):
        """Synthetic corpus."""
        return {
            "d1": "photosynthesis is the process by which plants convert light into chemical energy",
            "d2": "neural networks are computational models inspired by biological neural networks",
            "d3": "quantum computing uses quantum mechanics principles for computation",
        }

    async def reset(self, seed=None, **kwargs) -> RetrievalObservation:
        """Reset to next example."""
        if self.dataset is None:
            self.dataset = self._synthetic_dataset()
            self.corpus = self._synthetic_corpus()

        self.current_idx = (self.current_idx + 1) % len(self.dataset)
        self.current_example = self.dataset[self.current_idx]

        # Initial observation: provide query context
        return RetrievalObservation(
            passages=self._get_initial_passages(),
            reward=0.0,
            done=False,
        )

    def _get_initial_passages(self):
        """Get initial passage context (corpus sample)."""
        corpus_list = list(self.corpus.values())
        return corpus_list[:5] if corpus_list else ["No passages available"]

    async def step(self, action: QueryAction, **kwargs) -> RetrievalObservation:
        """Process query action."""
        if self.current_example is None:
            await self.reset()

        # Compute reward: 1.0 if action query matches any gold passage
        gold_ids = self.current_example.get("gold_ids", [])
        gold_docs = [self.corpus.get(gid, "") for gid in gold_ids]

        reward = 1.0 if any(action.query.lower() in doc.lower() or
                            doc.lower() in action.query.lower()
                            for doc in gold_docs) else 0.0

        return RetrievalObservation(
            passages=[self.current_example.get("gold_answer", "")],
            reward=reward,
            done=True,
        )

    @property
    def state(self):
        """Return current environment state."""
        return {
            "example_idx": self.current_idx,
            "current_query": self.current_example.get("query") if self.current_example else None,
        }


app = create_app(BrightEnvironment, QueryAction, RetrievalObservation)
