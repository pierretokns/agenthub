"""
MIRACL (Multilingual Information Retrieval Across Cross-Lingual)
Benchmark Environment for Prime RL

This environment trains and evaluates embedding models on the MIRACL
cross-lingual retrieval benchmark.

Dataset: https://huggingface.co/datasets/miracl/miracl
"""

from typing import Any
import random

try:
    import verifiers as vf
    from datasets import load_dataset
except ImportError:
    pass


def render_prompt(observation: Any) -> list[dict[str, Any]]:
    """
    Render a MIRACL task as a prompt.

    Observation format:
    {
        "query": "the search query",
        "language": "language code (e.g., 'en', 'zh', 'ar')",
        "positives": [...],
        "negatives": [...]
    }
    """
    if isinstance(observation, dict):
        query = observation.get("query", "")
        language = observation.get("language", "en")
        if query:
            return [{
                "role": "user",
                "content": f"[{language}] Query: {query}\n\nFind relevant documents."
            }]
    raise RuntimeError("Invalid observation format for MIRACL")


def load_environment(
    num_train_examples: int = 100,
    num_eval_examples: int = 50,
    seed: int = 0,
    split: str = "train",
):
    """
    Load MIRACL dataset.

    Args:
        num_train_examples: Number of training examples
        num_eval_examples: Number of evaluation examples
        seed: Random seed
        split: "train" or "test" split
    """
    random.seed(seed)

    # Load MIRACL dataset from HuggingFace
    try:
        dataset = load_dataset("miracl/miracl", split=split)
    except Exception as e:
        print(f"Warning: Could not load MIRACL dataset: {e}")
        dataset = _generate_synthetic_miracl_examples(
            num_examples=num_train_examples if split == "train" else num_eval_examples
        )

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


def _generate_synthetic_miracl_examples(num_examples: int = 100):
    """Generate synthetic MIRACL-like examples."""
    languages = ["en", "zh", "ar", "fr", "es"]
    queries = [
        "what is artificial intelligence",
        "how does machine learning work",
        "explain neural networks",
        "tell me about transformers",
        "describe deep learning",
    ]

    documents = [
        "AI is the field of computer science",
        "Machine learning learns patterns from data",
        "Neural networks are inspired by the brain",
        "Transformers revolutionized NLP",
        "Deep learning uses neural networks",
    ]

    examples = []
    for i in range(num_examples):
        lang = languages[i % len(languages)]
        query = queries[i % len(queries)]
        pos_idx = i % len(documents)
        neg_indices = [(i + j) % len(documents) for j in range(1, 3)]

        examples.append({
            "query": query,
            "language": lang,
            "positives": [documents[pos_idx]],
            "negatives": [documents[idx] for idx in neg_indices],
        })

    return examples
