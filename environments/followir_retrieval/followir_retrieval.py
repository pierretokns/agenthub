"""
FollowIR Retrieval Benchmark Environment for Prime RL

This environment trains and evaluates embedding models on the FollowIR
retrieval benchmark with instruction-following constraints.

Dataset: https://huggingface.co/datasets/jxmo/followir
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
    Render a FollowIR task as a prompt.

    Observation format:
    {
        "query": "the instruction-aware query",
        "instruction": "follow this constraint...",
        "positives": [...],
        "negatives": [...]
    }
    """
    if isinstance(observation, dict):
        query = observation.get("query", "")
        instruction = observation.get("instruction", "")
        content = f"Query: {query}"
        if instruction:
            content += f"\n\nConstraint: {instruction}"
        if content.strip():
            return [{"role": "user", "content": content}]
    raise RuntimeError("Invalid observation format for FollowIR")


def load_environment(
    num_train_examples: int = 100,
    num_eval_examples: int = 50,
    seed: int = 0,
    split: str = "train",
):
    """
    Load FollowIR dataset.

    Args:
        num_train_examples: Number of training examples
        num_eval_examples: Number of evaluation examples
        seed: Random seed
        split: "train" or "test" split
    """
    random.seed(seed)

    # Load FollowIR dataset from HuggingFace
    try:
        dataset = load_dataset("jxmo/followir", split=split)
    except Exception as e:
        print(f"Warning: Could not load FollowIR dataset: {e}")
        dataset = _generate_synthetic_followir_examples(
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


def _generate_synthetic_followir_examples(num_examples: int = 100):
    """Generate synthetic FollowIR-like examples."""
    queries = [
        "find papers on deep learning",
        "search for information on NLP",
        "locate results about computer vision",
    ]

    instructions = [
        "only include papers from 2023 or later",
        "focus on recent developments",
        "exclude tutorials and surveys",
    ]

    documents = [
        "A 2024 paper on transformer improvements",
        "2020 survey on neural networks",
        "Recent tutorial on PyTorch basics",
        "2023 breakthrough in vision transformers",
        "2022 NLP benchmark paper",
    ]

    examples = []
    for i in range(num_examples):
        query = queries[i % len(queries)]
        instruction = instructions[i % len(instructions)]
        pos_idx = i % len(documents)
        neg_indices = [(i + j) % len(documents) for j in range(1, 3)]

        examples.append({
            "query": query,
            "instruction": instruction,
            "positives": [documents[pos_idx]],
            "negatives": [documents[idx] for idx in neg_indices],
        })

    return examples
