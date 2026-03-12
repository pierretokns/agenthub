# OpenEnv RL Modifications: Differences from autoresearch-embed

**Goal:** Clarify how RL-based training (Prime Labs) differs from autoresearch-embed's supervised training, and what needs to be different in the agent's approach.

---

## Core Differences

### autoresearch-embed (Supervised Training)
```
Train on:
  - Curated positive/negative pairs from datasets
  - Fixed loss: contrastive (InfoNCE with hard negatives)
  - MLX native, Apple Silicon optimized
  - Agent edits training code, loss functions, hyperparameters
  - Evaluation: MTEB offline (deterministic)

Result:
  - Model weights saved to checkpoints/
  - Scores logged to results.jsonl
  - Agent reads results, decides next change
```

### OpenEnv RL (Reinforcement Learning)
```
Train via:
  - OpenEnv gym environment (reset/step API)
  - Agent takes actions in environment
  - Receives reward signal
  - Prime Labs RL policy optimization (PPO, DPO, or similar)
  - Agent NOT running training code directly

Result:
  - Policy weights optimized by Prime Labs infrastructure
  - Reward signal critical (not just evaluation metric)
  - Agent role: choose environment/dataset, not algorithm
  - Evaluation: contamination-checked MTEB (if connected)
```

---

## What Agent CAN Control in RL Mode

### 1. Environment & Dataset Selection
```python
# Agent can:
export BRIGHT_DATASET="mistral-embed/ArxivQA"  # Swap dataset
export MIRACL_LANGUAGE="es"                     # Change language
prime rl run configs/bright_baseline.toml       # Launch training

# Agent CANNOT:
# Edit src/train.py (doesn't exist in OpenEnv env)
# Change batch size in OpenEnv gym (fixed by image)
# Modify reward function (defined in proj/server/app.py)
```

### 2. Reward Function Definition
```python
# Agent MUST define clear reward signal in proj/server/app.py
# Example: BRIGHT
async def step(self, action: QueryAction, **kwargs) -> RetrievalObservation:
    reward = 1.0 if action.query_matches_gold_doc else 0.0
    return RetrievalObservation(
        passages=[...],
        reward=reward,  # 👈 This drives RL optimization
        done=True,
    )
```

### 3. Environment Config (Limited)
```toml
# configs/bright_baseline.toml might have:
[env]
model = "ModernBERT-base"
max_seq_length = 512
# But NOT training hyperparameters (those are Prime Labs RL config)
```

### 4. Dataset & Evaluation Protocol
```python
# Agent selects:
# 1. Which dataset to train on (via env vars)
# 2. When to evaluate (MTEB + contamination check)
# 3. When to switch datasets (convergence detection)
# 4. Ablation strategy (architecture vs. data signal)
```

---

## What Agent CANNOT Control

| Component | autoresearch-embed | OpenEnv RL | Why |
|-----------|-----------------|-----------|-----|
| Training loop | ✅ Edit `src/train.py` | ❌ Read-only | Prime Labs manages it |
| Loss function | ✅ Edit `src/losses.py` | ⚠️ Reward function only | Defined in OpenEnv gym |
| Batch size | ✅ Change in code | ❌ Docker image fixed | Image built, can't change |
| Learning rate | ✅ Tune per experiment | ❌ Prime Labs RL config | Infrastructure controls |
| Model architecture | ✅ Edit `src/model.py` | ⚠️ Fixed in Docker | Need rebuild to change |
| Evaluation | ✅ Run manually | ✅ Automatic (MTEB + contamination) | Infrastructure automated |

---

## Program.md Structure (RL Version)

### autoresearch-embed program.md
```markdown
# Workflow
1. Read state: cat results.jsonl
2. Decide what to try: edit src/ or configs/
3. Run: uv run scripts/experiment.py
4. Analyze results
```

### agenthub (RL) program.md
```markdown
# Workflow (RL-Based)
1. Read state: cat results.jsonl | tail -1
2. Decide next dataset: based on score gradient
3. Set env vars: export BRIGHT_DATASET=...
4. Run: prime rl run configs/bright_baseline.toml
5. Monitor: prime rl logs <run-id> -f
6. Analyze: results auto-logged by Prime Labs
7. Detect convergence: gradient < threshold → switch dataset
8. Validate: contamination check before accepting
```

**Key difference:** Agent doesn't edit code, only decides parameters (dataset, hyperparameters via config).

---

## Results Schema Changes

### autoresearch-embed
```json
{
  "name": "exp_1",
  "status": "COMPLETED",
  "loss": 0.123,
  "mteb_scores": { "primary": 62.3 },
  "training_config": { "batch_size": 64, "lr": 5e-5 }
}
```

### agenthub (RL)
```json
{
  "timestamp": "2026-03-12T12:00:00Z",
  "run_id": "wg6mko1s5l1fok3ij57l3h96",
  "dataset": {
    "name": "BRIGHT",
    "source": "google-research-datasets/BRIGHT",
    "config": "gpt4_reason"
  },
  "training": {
    "status": "COMPLETED",
    "steps": 1000,
    "final_reward": 0.75
  },
  "evaluation": {
    "contamination": {
      "passed": true,
      "overall_rate": 0.002
    },
    "mteb_scores": {
      "primary_score": 62.3
    }
  }
}
```

**New fields:**
- `run_id` — Track Prime Labs RL run
- `dataset` — Which dataset was used
- `training.reward` — Average reward during training (signal quality)
- `evaluation.contamination` — **CRITICAL** — all results must pass

---

## Agent Decision Framework

### For autoresearch-embed
```
Agent asks: "What should I change in the code?"
Options:
  - Try new loss function
  - Try new data augmentation
  - Try new pooling strategy
  - Change architecture
```

### For OpenEnv RL
```
Agent asks: "Which dataset should I train on next?"
Options:
  - Continue current dataset (if gradient good)
  - Switch to new dataset (if plateau detected)
  - Try multilingual variant (if monolingual done)
  - Trigger ablation study (if stuck)

Then:
  - Set environment variables
  - Launch Prime Labs RL
  - Monitor for completion
  - Validate contamination
  - Log results
```

---

## Contamination Handling (CRITICAL)

### autoresearch-embed
```python
# Contamination check BEFORE eval:
contamination_result = check_contamination(training_data)
if not contamination_result["passed"]:
    # Reject experiment, don't log
    raise ContaminationError()
```

### agenthub (RL)
```python
# Same check, but for MULTIPLE datasets:
def validate_run_result(result: dict):
    """Reject if contaminated."""
    contamination = result["evaluation"]["contamination"]
    if not contamination["passed"]:
        print(f"❌ REJECTED: {result['dataset']['name']} contaminated")
        # Remove from leaderboard, log as failed
        return False
    return True
```

**Rule:** A single contaminated result can invalidate all previous results on that dataset. Example:
```
Iteration 1-5: BRIGHT training, all pass contamination ✅
Iteration 6: BRIGHT with LLM-synthetic data, FAILS contamination ❌
→ Iterations 1-5 still valid, but know this approach is risky
```

---

## Evaluation Protocol (RL-Aware)

### MTEB Evaluation
```python
# After training, evaluate on MTEB (8 target tasks):
# - STSBenchmark, SICK-R
# - TwitterURLCorpus, SprintDuplicateQuestions
# - TwentyNewsgroupsClustering, RedditClustering
# - SciFact, NFCorpus

# With gating:
def eval_and_record(run_id: str, dataset_name: str):
    """Eval + contamination check."""

    # 1. Run MTEB
    mteb_scores = run_mteb_evaluation(run_id)

    # 2. Check contamination on this dataset
    training_texts = load_training_data(dataset_name)
    contamination = check_contamination(training_texts)

    # 3. Only record if contam passed
    if contamination["passed"]:
        record_result({
            "run_id": run_id,
            "mteb_scores": mteb_scores,
            "contamination": contamination,
        })
    else:
        print(f"Rejected: {dataset_name} contaminated ({contamination['overall_rate']:.4f})")
```

---

## Auto-Logging & Git Workflow

### autoresearch-embed
```
scripts/experiment.py handles:
  - git add + commit
  - Checkpoint saving
  - Results logging
  - wandb sync
```

### agenthub (RL)
```
Prime Labs RL handles:
  - Model checkpoint saving
  - Logs to infrastructure
  - Agent reads via: prime rl logs <run-id>
  - Agent commits results: git add results.jsonl && git commit
```

**Rule:** Only commit results that have passed contamination validation.

---

## Agent Responsibility Matrix

| Task | autoresearch-embed | agenthub (RL) | How |
|------|-----------------|-----------|-----|
| Decide what to train on | ✅ Agent (code changes) | ✅ Agent (dataset selection) | Results analysis |
| Run training | Script | Prime Labs RL | prime rl run |
| Monitor training | Script logs | prime rl logs | Polling |
| Evaluate model | Script (MTEB) | Prime Labs + contamination | Automatic + gating |
| Validate integrity | Script (contamination) | Agent (must validate) | Read contamination report |
| Log results | Script (auto) | Agent (manual commit) | Parse + validate |
| Iterate | Agent (read results, edit code) | Agent (read results, set env vars) | Next dataset selection |

---

## Operational Differences: Day-to-Day

### autoresearch-embed Day
```bash
# Agent reads:
$ cat results.jsonl | tail -1 | jq '.primary_score'
62.3

# Agent edits:
$ vim src/losses.py  # Try new loss

# Agent runs:
$ uv run scripts/experiment.py "test new loss"

# Script handles: train → eval → log → commit → push

# Agent reads results:
$ cat results.jsonl | tail -1 | jq '.primary_score'
63.1  # Improved!

# Repeat
```

### agenthub (RL) Day
```bash
# Agent reads:
$ cat results.jsonl | tail -1 | jq '.evaluation.mteb_scores.primary_score'
62.3

# Agent decides:
$ python3 -c "
  score = 62.3
  if score < 70:
      print('Switch dataset')
"

# Agent sets vars & launches:
$ export BRIGHT_DATASET=mistral-embed/ArxivQA
$ prime rl run configs/bright_baseline.toml
# Outputs: run_id = wg6mko1s5l1fok3ij57l3h96

# Agent monitors:
$ prime rl logs wg6mko1s5l1fok3ij57l3h96 -f
# Watches for "COMPLETED"

# Agent validates:
$ prime rl metrics wg6mko1s5l1fok3ij57l3h96 | jq '.contamination'
{ "passed": true, "overall_rate": 0.002 }

# Agent commits:
$ git add results.jsonl && git commit -m "result: ArxivQA run passed"
$ git push

# Repeat
```

---

## Summary: What the Agent Should Know

| Aspect | Key Point |
|--------|-----------|
| **Control** | Agent controls dataset selection, not training algorithm |
| **Reward** | Reward signal = what RL optimizes. Must be carefully designed |
| **Contamination** | MANDATORY check. No results without passing validation |
| **Iteration speed** | Faster than autoresearch-embed (dataset swaps vs. code changes) |
| **Evaluation** | Automatic MTEB + contamination, results auto-logged |
| **Integrity** | Read-only boundaries: src/eval/, contamination.py, RL infrastructure |
| **Failure mode** | Contaminated training data = invalid results (reject immediately) |

---

## Next: See AUTONOMOUS_RESEARCH_PROTOCOL.md

Once you understand these differences, the autonomous protocol (Phase 2-3) makes sense:
1. Read results + check contamination
2. Decide next dataset (based on gradient/plateau)
3. Set env vars
4. Launch
5. Monitor + validate
6. Commit + repeat
