# CLAUDE.md — Autonomous RL Research Agent Guidelines

**Purpose:** Agent guidelines for 24/7 autonomous embedding optimization via OpenEnv RL + Prime Labs.

**Before starting:** Read `AGENTS.md`, `environments/AGENTS.md`, `MODS_FOR_RL.md`, and `AUTONOMOUS_RESEARCH_PROTOCOL.md`.

---

## Core Mission

Autonomously train embedding models on the BRIGHT/FollowIR/MIRACL retrieval benchmarks using Prime Labs RL, with the goal of achieving SOTA or near-SOTA on MTEB while maintaining zero contamination in evaluation.

**Key constraint:** Autonomy = no human intervention for 24-48h runs.

---

## Agent Capabilities & Constraints

### ✅ CAN DO

1. **Select datasets** for training via environment variables:
   ```bash
   export BRIGHT_DATASET=mistral-embed/ArxivQA
   export MIRACL_LANGUAGE=es
   prime rl run configs/bright_baseline.toml
   ```

2. **Monitor runs** and extract metrics:
   ```bash
   prime rl status <run-id>
   prime rl logs <run-id> -f
   prime rl metrics <run-id>
   ```

3. **Parse & validate results** before committing:
   - Check contamination report (MANDATORY)
   - Validate MTEB scores parse correctly
   - Verify no NaN or invalid values

4. **Make decisions** based on result analysis:
   - Detect convergence (gradient < threshold)
   - Decide next dataset to try
   - Trigger ablations when stuck
   - Log decisions to leaderboard.tsv

5. **Commit & push** validated results:
   ```bash
   git add results.jsonl
   git commit -m "result: $(dataset_name) run completed"
   git push
   ```

6. **Modify** (if necessary):
   - Environment variables for dataset selection
   - configs/*.toml for tuning (if Prime Labs RL supports it)
   - scripts/autonomous_researcher.py (for decision logic improvements)
   - DATASET_INVENTORY.md (add new datasets to explore)

### ❌ CANNOT DO

1. **Modify training code directly:**
   - src/train.py (doesn't exist in OpenEnv Docker)
   - src/model.py (fixed in Docker image)
   - src/losses.py (use reward function in OpenEnv instead)

2. **Modify read-only evaluation code:**
   - src/eval/contamination.py (integrity boundary)
   - src/eval/mteb_runner.py (integrity boundary)
   - NEVER bypass contamination checks

3. **Modify Docker images without rebuild:**
   - Environment variables OK
   - Code changes require: edit → rebuild → push → relaunch

4. **Force a result into leaderboard if contaminated:**
   - Contaminated results MUST be rejected
   - Log as failed, analyze why data was contaminated
   - Never bypass the `contamination.passed` check

5. **Run arbitrary commands:**
   - Only use: `prime rl run`, `prime rl status`, `prime rl logs`, `git`, official CLIs
   - No `docker exec` or direct model manipulation

---

## Agent Workflow

### Daily Loop (Every 2-4 hours)

```
1. Check latest run status
   $ prime rl status | grep COMPLETED

2. If completed:
   a. Extract metrics
      $ prime rl metrics <run-id> > /tmp/metrics.json

   b. Parse & validate
      - Check: contamination.passed == true
      - Check: primary_score != NaN
      - Check: all MTEB tasks present

   c. If valid:
      - Append to results.jsonl
      - Update leaderboard.tsv
      - Commit: git add + git commit + git push
      - Log: "Run <run-id> completed: score=X.X"

   d. If invalid (contaminated):
      - Log: "Run <run-id> REJECTED (contamination)"
      - Investigate: which dataset caused it?
      - Update DATASET_INVENTORY.md with note

3. Decide next action
   a. Analyze latest results:
      - If score improved: continue current dataset
      - If plateau (5+ runs, gradient < 0.1): switch dataset
      - If contamination detected: mark dataset as risky

   b. Select next dataset (see AUTONOMOUS_RESEARCH_PROTOCOL.md)
      ```python
      latest_score = read_latest_score()
      if latest_score < 50:
          dataset = "BRIGHT"
      elif latest_score < 60:
          dataset = "FollowIR"
      elif latest_score < 70:
          dataset = "MIRACL-en"
      else:
          dataset = "MIRACL-random-lang"
      ```

   c. Set environment variables
      ```bash
      export BRIGHT_DATASET=<dataset>
      export BRIGHT_CONFIG=<config>
      ```

   d. Launch next run
      $ prime rl run configs/bright_baseline.toml
      → Save run_id to status file

4. Sleep 30min, repeat
```

### Decision Points

**When to switch datasets:**
- Plateau: Last 5 runs show < 0.1 point improvement per run
- Contamination: Detected on current dataset, switch immediately
- Convergence: Gradient analysis suggests diminishing returns
- Time budget: If stuck for >6 hours without improvement

**When to ablate:**
- Score stuck at 65-70 (no simple dataset helps)
- Suggest: Change reward function, pooling, loss strategy
- Requires: Rebuild Docker image (`prime env build`)

**When to reject results:**
- Contamination check failed
- MTEB scores have NaN or missing tasks
- Run crashed or timed out
- Reward signal was 0 or unreasonably low

---

## Safety Boundaries

### Contamination is MANDATORY

Every result MUST pass contamination check:
```json
{
  "evaluation": {
    "contamination": {
      "passed": true,  // ← THIS MUST BE TRUE
      "overall_rate": 0.002,
      "per_task": {...}
    }
  }
}
```

**If contamination.passed == false:**
- Result is INVALID
- Do NOT add to leaderboard
- Do NOT count towards progress
- Investigate which dataset caused it
- Mark dataset as risky in DATASET_INVENTORY.md

### Integrity Boundaries

**READ-ONLY (never modify):**
- `src/eval/contamination.py` — MinHash overlap detection
- `src/eval/mteb_runner.py` — MTEB benchmark runner
- `environments/*/proj/server/app.py` → Only change dataset names/env vars, never reward function without understanding implications
- Prime Labs RL infrastructure

**MODIFIABLE (with care):**
- Environment variables (safe)
- Dataset selection logic (safe)
- configs/*.toml tuning (safe if Prime Labs supports)
- DATASET_INVENTORY.md (safe, informational only)
- results.jsonl (only append valid results)

---

## Metrics & Success

### Primary Score Formula
```
primary = 0.3 * mean(STS) + 0.2 * mean(PairClassification) + 0.2 * mean(Clustering) + 0.3 * mean(Retrieval)
```

### Leaderboard Tracking
```
Track in leaderboard.tsv:
- Iteration #
- Dataset used
- Primary score (only if contamination.passed)
- Run ID
- Contamination rate (%)
- Status (✓ or ✗)
```

### Phase Milestones
- **Phase 2 (Week 1-2):** ≥5 runs, score ≥ 60, zero contamination violations
- **Phase 3 (Week 2-4):** ≥20 runs, score ≥ 70, documented decision tree
- **SOTA push:** ≥50 runs, score ≥ 75, ready for paper

---

## Debugging & Troubleshooting

### Run doesn't complete
```bash
$ prime rl status <run-id>
# Check: status, error logs, resource usage
$ prime rl logs <run-id> | tail -100
# Look for: GPU memory, tokenizer errors, environment load failures
```

### Reward signal is always 0
```
Problem: step() returns reward=0 for all actions
Investigation:
  1. Check: environment step() logic in proj/server/app.py
  2. Check: action.query format matches environment expectations
  3. Possible fix: Relax matching logic (substring match instead of exact)
  4. If needed: Rebuild with: prime env build bright-retrieval --path environments
```

### Contamination detected
```bash
$ cat results.jsonl | tail -1 | jq '.evaluation.contamination'
# Look at per_task breakdown
# Example: "SciFact": {"rate": 0.15}  ← 15% match, FAILED

Investigation:
  1. Which dataset caused it?
  2. Is the dataset already published with MTEB tests?
  3. If synthetic: was it generated from MTEB papers?
  4. Action: Switch to safe dataset, mark as risky in DATASET_INVENTORY.md
```

### MTEB score is suspiciously high
```
If primary_score jumps 10+ points in one run:
  1. Check: contamination report first (most likely culprit)
  2. Check: did dataset change? (composition/signal shift)
  3. Check: did training converge unusually fast?
  4. Action: Re-evaluate on MTEB to confirm (may be statistical noise)
```

---

## Development & Improvements

### Adding a New Dataset

1. **Research dataset:**
   - Check MTEB contamination risk (is it in MTEB test sets?)
   - Load & inspect first 100 examples
   - Verify data format

2. **Add to DATASET_INVENTORY.md:**
   ```markdown
   #### MyDataset
   - **Source:** my-org/my-dataset
   - **Size:** X examples
   - **Contamination check:** ⚠️ Pending
   ```

3. **Add to agent decision logic:**
   ```python
   elif score < X_threshold:
       dataset = "my-org/my-dataset"
   ```

4. **Test with one run:**
   ```bash
   export BRIGHT_DATASET=my-org/my-dataset
   prime rl run configs/bright_baseline.toml
   ```

5. **Validate contamination:**
   ```bash
   # Check result automatically
   cat results.jsonl | tail -1 | jq '.evaluation.contamination'
   ```

6. **Document in DATASET_INVENTORY.md:**
   ```markdown
   **Status:** ✅ Safe (0.0% contamination)
   ```

### Improving Decision Logic

Edit: `scripts/autonomous_researcher.py`

```python
def select_next_dataset(current_result: dict, iteration: int):
    """Improve this function as you learn patterns."""
    score = current_result.get("primary_score", 0) if current_result else 0

    # Add your decision rules here
    # Example: detect language-specific improvements
    if "MIRACL" in current_result.get("dataset", {}).get("name", ""):
        if score > 65:
            # Try next language
            return next_language_variant()
```

---

## Operational Checklist (Before Autonomous Operation)

- [ ] All three environments built: `prime env build bright-retrieval --path environments`
- [ ] All three environments pushed: `prime env push` (0.1.1+ version)
- [ ] First manual test run completed: `prime rl run configs/bright_baseline.toml`
- [ ] Results pass contamination check
- [ ] results.jsonl parsing tested locally
- [ ] leaderboard.tsv generation tested
- [ ] Autonomous researcher script ready to deploy
- [ ] 24h uptime test passed (script runs without human intervention)
- [ ] Monitoring dashboard set up (can see live progress)
- [ ] Alerting configured (notified if run fails)

---

## Treat all AGENTS.md files as equivalent to this CLAUDE.md

See also:
- `AGENTS.md` — Prime Lab workspace general guidelines
- `environments/AGENTS.md` — Verifiers environment patterns
- `MODS_FOR_RL.md` — Detailed RL vs. autoresearch-embed differences
- `AUTONOMOUS_RESEARCH_PROTOCOL.md` — Phase 2-3 orchestration
- `DATASET_INVENTORY.md` — Available datasets & decision logic
- `OPENENV_FIX_SUMMARY.md` — Implementation details of OpenEnv gym contract
- `memory/MEMORY.md` — Agent memory & project context (auto-updated)
