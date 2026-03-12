"""
BRIGHT Retrieval Benchmark Environment for Prime RL

This environment trains and evaluates embedding models on the BRIGHT
retrieval benchmark (BigIR: Binary Relevance Information Gain Task).

Dataset: https://huggingface.co/datasets/google-research-datasets/BRIGHT
"""

from typing import Any
import json
import random

try:
    import verifiers as vf
    from datasets import load_dataset
except ImportError:
    pass


def render_prompt(observation: Any) -> list[dict[str, Any]]:
    """
    Render a retrieval task as a prompt for the language model.

    Observation format:
    {
        "query": "the question to answer",
        "positives": [...],  # relevant document passages
        "negatives": [...]   # non-relevant passages
    }
    """
    if isinstance(observation, dict):
        query = observation.get("query", "")
        if query:
            return [{
                "role": "user",
                "content": f"Query: {query}\n\nProvide relevant document passages for this query."
            }]
    raise RuntimeError("Invalid observation format for BRIGHT")


def load_environment(
    num_train_examples: int = 100,
    num_eval_examples: int = 50,
    seed: int = 0,
    split: str = "train",
):
    """
    Load BRIGHT dataset.

    Args:
        num_train_examples: Number of training examples
        num_eval_examples: Number of evaluation examples
        seed: Random seed
        split: "train" or "test" split
    """
    random.seed(seed)

    # Load BRIGHT dataset from HuggingFace
    try:
        dataset = load_dataset("google-research-datasets/BRIGHT", split=split)
    except Exception as e:
        # Fallback: return synthetic examples if dataset unavailable
        print(f"Warning: Could not load BRIGHT dataset: {e}")
        dataset = _generate_synthetic_bright_examples(
            num_examples=num_train_examples if split == "train" else num_eval_examples
        )

    # Limit to requested number of examples
    num_examples = num_train_examples if split == "train" else num_eval_examples
    if hasattr(dataset, '__len__'):
        examples = list(dataset)[:num_examples]
    else:
        examples = [x for i, x in enumerate(dataset) if i < num_examples]

    return vf.OpenEnvEnv(
        examples=examples,
        num_train_examples=num_train_examples,
        num_eval_examples=num_eval_examples,
        seed=seed,
        prompt_renderer=render_prompt,
    )


def _generate_synthetic_bright_examples(num_examples: int = 100):
    """Generate synthetic BRIGHT-like examples for testing."""
    queries = [
        "what is machine learning",
        "how to train neural networks",
        "transformer attention mechanism",
        "BERT language model",
        "embeddings for NLP",
    ]

    documents = [
        "Machine learning is a subset of artificial intelligence",
        "Deep learning uses neural networks with multiple layers",
        "Transformers use self-attention mechanisms",
        "BERT is a bidirectional encoder from Transformers",
        "Word embeddings map words to vector space",
        "Neural networks learn from data examples",
        "Gradient descent optimizes model parameters",
        "Backpropagation computes gradients efficiently",
    ]

    examples = []
    for i in range(num_examples):
        query = queries[i % len(queries)]
        pos_idx = i % len(documents)
        neg_indices = [(i + j) % len(documents) for j in range(1, 3)]

        examples.append({
            "query": query,
            "positives": [documents[pos_idx]],
            "negatives": [documents[idx] for idx in neg_indices],
        })

    return examples
