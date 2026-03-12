# Autonomous Research Protocol: 24/7 MTEB Optimization

**Goal:** Achieve SOTA or near-SOTA on MTEB through continuous autonomous RL training with dataset exploration and contamination safety.

**Operational Mode:** Fully autonomous Claude Code agent running in a loop, deciding which dataset to train on next based on previous results.

---

## Architecture Overview

```
┌─────────────────────────────────────┐
│  Autonomous Research Loop           │
│  (Claude Code Agent or scheduler)   │
└────────────┬────────────────────────┘
             │
             ├─→ Read state: results.jsonl + leaderboard.jsonl
             │
             ├─→ Decide next experiment:
             │   - If score < threshold: try new dataset
             │   - If reward improving: continue current
             │   - If converged: ablate or try new method
             │
             ├─→ Set environment variables:
             │   export BRIGHT_DATASET=...
             │   export BRIGHT_CONFIG=...
             │
             ├─→ Launch: prime rl run configs/bright_baseline.toml
             │
             └─→ Monitor: prime rl logs <run-id>
                  - Wait for completion
                  - Check contamination report
                  - Log results to results.jsonl
```

---

## Phase 2: Medium-Term (Weeks 1-2)

### Goal
Build an autonomous agent that explores different datasets and tracks results without human intervention.

### Components

#### 1. Agent Script: `scripts/autonomous_researcher.py`
```python
#!/usr/bin/env python3
"""Autonomous dataset exploration agent.

Runs in a loop:
1. Read latest results from results.jsonl
2. Decide which dataset to try next (decision logic in DATASET_INVENTORY.md)
3. Set environment variables
4. Launch prime rl run
5. Monitor for completion
6. Parse contamination report
7. Commit results
8. Repeat
"""

import json
import os
import subprocess
import time
from pathlib import Path
from datetime import datetime

RESULTS_FILE = Path("results.jsonl")
INVENTORY = Path("DATASET_INVENTORY.md")

def read_latest_result():
    """Read most recent result from results.jsonl."""
    if not RESULTS_FILE.exists():
        return None
    with open(RESULTS_FILE) as f:
        lines = f.readlines()
    return json.loads(lines[-1]) if lines else None

def select_next_dataset(current_result: dict, iteration: int) -> dict:
    """
    Select next dataset based on current performance.
    See DATASET_INVENTORY.md for decision logic.
    """
    score = current_result.get("primary_score", 0) if current_result else 0

    # Simple decision tree (replace with sophisticated logic later)
    if score < 50:
        return {
            "name": "BRIGHT (baseline)",
            "dataset": "google-research-datasets/BRIGHT",
            "config": "gpt4_reason",
        }
    elif score < 60:
        return {
            "name": "FollowIR (instruction signal)",
            "dataset": "jhu-clsp/FollowIR-train",
            "split": "train",
        }
    elif score < 70:
        return {
            "name": "MIRACL-en (multilingual)",
            "dataset": "miracl/miracl",
            "language": "en",
            "split": "train",
        }
    else:
        # Explore multilingual variants
        languages = ["es", "fr", "de", "pt", "zh"]
        lang = languages[iteration % len(languages)]
        return {
            "name": f"MIRACL-{lang}",
            "dataset": "miracl/miracl",
            "language": lang,
            "split": "train",
        }

def set_env_vars(dataset_config: dict):
    """Set environment variables for dataset selection."""
    if "dataset" in dataset_config:
        if "BRIGHT" in dataset_config.get("name", ""):
            os.environ["BRIGHT_DATASET"] = dataset_config["dataset"]
            os.environ["BRIGHT_CONFIG"] = dataset_config.get("config", "gpt4_reason")
        elif "FollowIR" in dataset_config.get("name", ""):
            os.environ["FOLLOWIR_DATASET"] = dataset_config["dataset"]
            os.environ["FOLLOWIR_SPLIT"] = dataset_config.get("split", "train")
        elif "MIRACL" in dataset_config.get("name", ""):
            os.environ["MIRACL_DATASET"] = dataset_config["dataset"]
            os.environ["MIRACL_LANGUAGE"] = dataset_config.get("language", "en")
            os.environ["MIRACL_SPLIT"] = dataset_config.get("split", "train")

def launch_training(dataset_name: str):
    """Launch prime rl run with current environment variables."""
    cmd = ["prime", "rl", "run", "configs/bright_baseline.toml"]
    print(f"[{datetime.now().isoformat()}] Launching: {' '.join(cmd)}")
    print(f"Dataset: {dataset_name}")

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ERROR: prime rl run failed: {result.stderr}")
        return None

    # Parse run ID from output
    for line in result.stdout.split("\n"):
        if "run_id" in line.lower() or "id:" in line.lower():
            return line
    return None

def wait_for_completion(run_id: str, max_wait_hours: int = 24):
    """Poll for training completion."""
    start_time = time.time()
    max_wait = max_wait_hours * 3600

    while time.time() - start_time < max_wait:
        result = subprocess.run(
            ["prime", "rl", "status", run_id],
            capture_output=True,
            text=True,
        )

        output = result.stdout
        if "COMPLETED" in output or "FAILED" in output:
            return "COMPLETED" in output

        print(f"[{datetime.now().isoformat()}] Waiting... status={output.strip()}")
        time.sleep(300)  # Poll every 5 min

    return False

def main():
    iteration = 0
    while True:
        iteration += 1
        print(f"\n{'='*60}")
        print(f"Iteration {iteration}: {datetime.now().isoformat()}")
        print(f"{'='*60}\n")

        # 1. Read state
        result = read_latest_result()
        if result:
            print(f"Latest score: {result.get('primary_score')}")

        # 2. Decide next dataset
        next_dataset = select_next_dataset(result, iteration)
        print(f"Selected dataset: {next_dataset['name']}")

        # 3. Set env vars
        set_env_vars(next_dataset)

        # 4. Launch training
        run_info = launch_training(next_dataset['name'])
        if not run_info:
            print("Failed to launch training, waiting 60s...")
            time.sleep(60)
            continue

        print(f"Run launched: {run_info}")

        # 5. Wait for completion (with polling)
        completed = wait_for_completion(run_info)
        if not completed:
            print(f"Training did not complete within 24h, moving to next")

        # 6. Results auto-logged by Prime Labs RL
        # 7. Commit happens automatically via agenthub

        # Sleep before next iteration
        time.sleep(30)

if __name__ == "__main__":
    main()
```

#### 2. Results Tracking: Enhanced `results.jsonl` Schema
```json
{
  "timestamp": "2026-03-12T12:00:00Z",
  "iteration": 1,
  "dataset": {
    "name": "BRIGHT",
    "source": "google-research-datasets/BRIGHT",
    "config": "gpt4_reason"
  },
  "training": {
    "run_id": "wg6mko1s5l1fok3ij57l3h96",
    "status": "COMPLETED",
    "duration_seconds": 3600,
    "steps": 1000,
    "final_reward": 0.75
  },
  "evaluation": {
    "contamination": {
      "passed": true,
      "overall_rate": 0.002,
      "per_task": {
        "STSBenchmark": {"rate": 0.001, "count": 5, "total": 5749}
      }
    },
    "mteb_scores": {
      "primary_score": 62.3,
      "sts_mean": 0.71,
      "retrieval_mean": 0.63,
      "clustering_mean": 0.61,
      "pair_classification_mean": 0.58
    }
  },
  "decision": {
    "next_action": "continue_current_dataset",
    "reason": "score improved by 2%, below threshold to switch"
  }
}
```

#### 3. Dashboard: `leaderboard.tsv` (Human-Readable)
```
Iteration   Dataset     Primary Score   STS    Retrieval   Status    Contaminated?
1           BRIGHT      62.3            0.71   0.63        ✓         No (0.2%)
2           BRIGHT      63.1            0.72   0.64        ✓         No (0.1%)
3           FollowIR    61.8            0.69   0.61        ✓         No (0.0%)
...
```

---

## Phase 3: Long-Term (Weeks 2-4)

### Goal
Achieve SOTA on MTEB through advanced techniques, intelligent dataset selection, and continuous 24/7 iteration.

### Components

#### 1. Intelligent Dataset Selection (`select_next_dataset.py`)
```python
def select_next_dataset_intelligent(
    results_history: list[dict],
    available_datasets: list[str],
    current_iteration: int,
    mteb_gap_to_sota: float,  # e.g., 10 means we're 10 points below SOTA
):
    """
    Intelligent dataset selection using:
    - Gradient analysis (is score improving?)
    - Dataset difficulty (which gives best signal?)
    - Temporal pacing (when to switch vs. continue?)
    - Contamination risk (avoid circular evaluation)
    """

    # 1. Compute gradient: has score been improving last 5 runs?
    recent_scores = [r["mteb_scores"]["primary_score"] for r in results_history[-5:]]
    gradient = (recent_scores[-1] - recent_scores[0]) / 5 if len(recent_scores) > 1 else 0

    # 2. If gradient < 0.1 per iteration, switch dataset (convergence detection)
    if gradient < 0.1:
        # Find dataset with lowest contamination risk + highest expected signal
        for dataset in available_datasets:
            contamination_risk = check_contamination_risk(dataset)
            if contamination_risk < 0.01:  # 1% threshold
                return dataset

    # 3. If gradient > 0.3, continue current dataset (strong improvement)
    if gradient > 0.3:
        return results_history[-1]["dataset"]["name"]

    # 4. Default: explore datasets in order of signal quality
    return explore_next_dataset_smart(available_datasets, mteb_gap_to_sota)
```

#### 2. Contamination Gating
All results must pass contamination check before being counted:
```python
def validate_result(result: dict) -> bool:
    """Reject any result with contamination."""
    contamination = result.get("evaluation", {}).get("contamination", {})
    if not contamination.get("passed"):
        print(f"⚠️ REJECTED: Contaminated result from {result['dataset']['name']}")
        return False
    return True
```

#### 3. Ablation Study Mode
When score plateaus, automatically suggest ablations:
```python
def suggest_ablation(current_score: float, plateau_duration: int):
    """
    If score hasn't improved in N iterations, suggest ablations:
    - Try different pooling strategy
    - Try different loss function
    - Try different hard negative mining
    """
    if plateau_duration > 5:
        return {
            "type": "ablation",
            "suggestions": [
                "ablate_pooling_strategy",
                "ablate_loss_function",
                "ablate_hard_negatives",
            ]
        }
```

#### 4. Advanced Orchestration
```bash
# Run continuously with fallback restart logic
while true; do
    python3 scripts/autonomous_researcher.py
    EXIT_CODE=$?

    if [ $EXIT_CODE -ne 0 ]; then
        echo "Agent crashed, restarting in 60s..."
        sleep 60
    fi
done
```

---

## Safety & Integrity

### Contamination Checking (MANDATORY)
Every result must pass:
1. **MinHash overlap check** — <1% of training data matches any MTEB test set
2. **Per-task check** — No individual task can exceed 1% contamination
3. **Automatic rejection** — Failed checks block results from being counted

Example:
```python
def check_contamination(training_texts: list[str]):
    """Uses MinHash with JACCARD_THRESHOLD=0.8, NUM_PERM=128."""
    result = contamination.check_contamination(training_texts)

    if not result["passed"]:
        raise ContaminationError(
            f"Overall rate: {result['overall_rate']:.4f}\n"
            f"Per-task: {result['per_task']}"
        )
```

### Integrity Boundaries
```
✅ CAN MODIFY:
   - Training code (src/train.py, src/losses.py, src/model.py, configs/)
   - Dataset selection (environment variables)
   - Hyperparameters (batch size, learning rate, stages)

❌ CANNOT MODIFY:
   - src/eval/ (read-only, integrity boundary)
   - scripts/autonomous_researcher.py once deployed (use agent for decisions only)
   - contamination.py (read-only)
```

---

## Success Metrics

### Phase 2 Success (by end of week 2)
- [ ] Autonomous agent running without human intervention
- [ ] 5+ complete training runs from different datasets
- [ ] All results pass contamination checks
- [ ] Results logged to results.jsonl + leaderboard.tsv
- [ ] Primary score ≥ 60 on at least one dataset

### Phase 3 Success (by end of week 4)
- [ ] 20+ complete training runs
- [ ] Primary score ≥ 70 (approaching SOTA for model size)
- [ ] Documented ablations (what worked, what didn't)
- [ ] Zero contamination in all results
- [ ] Code ready for publication/release

---

## Monitoring Dashboard

You can monitor progress via:
```bash
# View latest results
cat results.jsonl | tail -1 | python3 -m json.tool

# View leaderboard
cat leaderboard.tsv

# View in real-time
tail -f results.jsonl | jq '.[] | {timestamp, dataset: .dataset.name, score: .evaluation.mteb_scores.primary_score, contaminated: .evaluation.contamination.passed | not}'

# Monitor active run
prime rl status <run-id>
prime rl logs <run-id> -f
```

---

## Integration Checklist

- [ ] Environments built: `prime env build bright-retrieval --path environments`
- [ ] Environments pushed: `prime env push` (each directory)
- [ ] DATASET_INVENTORY.md created ✅
- [ ] scripts/autonomous_researcher.py written ✅
- [ ] results.jsonl schema updated
- [ ] leaderboard.tsv generation automated
- [ ] Contamination gating implemented
- [ ] 24/7 loop deployed (cron job or supervisor)
- [ ] Monitoring dashboard accessible

---

## Next Steps

1. **Immediate:** Build environments, test Phase 2 locally
2. **Week 1:** Deploy autonomous researcher, run 5+ experiments
3. **Week 2:** Analyze results, implement intelligent selection
4. **Week 3-4:** Advanced techniques, push towards SOTA

See CLAUDE.md for agent guidelines and MODS_FOR_RL.md for RL-specific architecture changes.
