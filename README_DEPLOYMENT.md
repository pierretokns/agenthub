# Deployment Guide: OpenEnv RL + 24/7 MTEB Optimization

**Updated:** March 12, 2026
**Status:** Ready to deploy Phase 1 + 2

---

## Quick Start (5 minutes)

### 1. Build Environments
```bash
cd /Users/pierre/gourmand/agenthub

# Build all three (takes ~10-15 min per environment)
prime env build bright-retrieval --path environments
prime env build followir-retrieval --path environments
prime env build miracl-retrieval --path environments

# Verify .build.json created
ls -la environments/bright_retrieval/proj/.build.json
ls -la environments/followir_retrieval/proj/.build.json
ls -la environments/miracl_retrieval/proj/.build.json
```

### 2. Push to Registry
```bash
# From each environment directory
cd environments/bright_retrieval && prime env push
cd ../followir_retrieval && prime env push
cd ../miracl_retrieval && prime env push

# Versions should bump to 0.1.1+
```

### 3. Test First Run
```bash
# Stop old failed runs (optional)
prime rl stop <run-id>

# Launch test run
prime rl run configs/bright_baseline.toml

# Monitor logs
prime rl logs <run-id> -f

# Extract metrics when done
prime rl metrics <run-id> | jq '.evaluation.contamination.passed'
# Should return: true
```

### 4. Commit Results
```bash
# When first run completes and passes contamination check
git add results.jsonl && git commit -m "result: BRIGHT baseline run completed"
git push
```

---

## Full Deployment Plan (Phase 1-3)

### Phase 1: Build & Validate (This Week)
**Goal:** Verify all three environments build, push, and can run without errors.

**Time:** 2-3 hours

**Steps:**
1. `prime env build bright-retrieval --path environments`
   - Expect: Successfully built image
   - Creates: `.build.json` file
   - If fails: Check Docker running, no syntax errors

2. `cd environments/bright_retrieval && prime env push`
   - Expect: Pushed to registry, version 0.1.1
   - If fails: Check authentication

3. Repeat for FollowIR and MIRACL

4. Manual test run (BRIGHT baseline)
   - `prime rl run configs/bright_baseline.toml`
   - Monitor: `prime rl logs <run-id> -f`
   - Expect: "Successfully installed environment" message
   - NOT: "RuntimeError: OpenEnv project is missing .build.json"

5. Verify contamination
   - `prime rl metrics <run-id> | jq '.evaluation.contamination.passed'`
   - Expect: `true`
   - If `false`: Investigate which dataset caused it

6. Commit & test git workflow
   - `git add results.jsonl && git commit`
   - `git push`

**Success Criteria:**
- ✅ All three environments build without errors
- ✅ `.build.json` created in each proj/ directory
- ✅ Test run completes without "missing .build.json" error
- ✅ Contamination check passes
- ✅ Results committed to git

---

### Phase 2: Autonomous Agent (Week 1-2)
**Goal:** Deploy autonomous researcher script that makes dataset decisions.

**Time:** Full 48h autonomous operation

**Steps:**
1. Write `scripts/autonomous_researcher.py` (template in AUTONOMOUS_RESEARCH_PROTOCOL.md)
   - Daily loop: read results → decide dataset → launch run
   - Contamination validation before committing
   - Leaderboard.tsv generation

2. Set up cron job or supervisor
   ```bash
   # Cron job (runs every 2 hours)
   0 */2 * * * cd /path/to/agenthub && python3 scripts/autonomous_researcher.py

   # Or: supervisor daemon
   [program:autonomous_researcher]
   command=python3 /path/to/scripts/autonomous_researcher.py
   autorestart=true
   ```

3. Monitor for 48h
   - Check: `tail -f results.jsonl | jq '{timestamp, dataset: .dataset.name, score: .evaluation.mteb_scores.primary_score}'`
   - Watch: Autonomous loop should run without human intervention
   - Alert on: Contamination failures, crashes, timeouts

4. After 48h: Review results
   - Which datasets improved score?
   - Which plateaued?
   - Any contamination issues?
   - Refine decision logic if needed

**Success Criteria:**
- ✅ 5+ complete training runs from different datasets
- ✅ All results pass contamination checks
- ✅ Primary score ≥ 60 on at least one dataset
- ✅ Autonomous loop runs 48h without human intervention
- ✅ Results auto-logged, committed to git

---

### Phase 3: Intelligent Selection & SOTA Push (Week 2-4)
**Goal:** Achieve SOTA or near-SOTA through data-driven decisions.

**Time:** 20-30 training runs over 2 weeks

**Steps:**
1. Analyze 10+ run results
   - Compute gradient for each dataset (is score improving?)
   - Identify plateau threshold (when to switch?)
   - Document signal quality per dataset

2. Enhance decision logic
   ```python
   def select_next_dataset(results_history, iteration):
       recent = results_history[-5:]
       gradient = (recent[-1]['score'] - recent[0]['score']) / 5

       if gradient < 0.1:  # Plateau detected
           return switch_to_next_dataset()
       elif gradient > 0.3:  # Strong improvement
           return continue_current_dataset()
       else:
           return explore_next_dataset()
   ```

3. Explore advanced datasets
   - ArxivQA (technical signal)
   - Multilingual MIRACL variants
   - Synthetic hard negatives (if applicable)

4. Trigger ablations when stuck
   - Architecture changes (requires rebuild)
   - Loss function variations (define in reward function)
   - Pooling strategy experiments

5. Document findings
   - Which datasets worked best?
   - Ablation results
   - SOTA comparison

**Success Criteria:**
- ✅ 20-30 complete runs
- ✅ Primary score ≥ 70
- ✅ Zero contamination violations
- ✅ Documented ablations & architecture insights
- ✅ Code ready for publication

---

## Environment Variable Reference

### BRIGHT
```bash
# Set custom dataset
export BRIGHT_DATASET="mistral-embed/ArxivQA"
export BRIGHT_CONFIG="default"
export BRIGHT_SPLIT="examples"

# Then run
prime rl run configs/bright_baseline.toml
```

### FollowIR
```bash
export FOLLOWIR_DATASET="jhu-clsp/FollowIR-train"
export FOLLOWIR_SPLIT="train"

prime rl run configs/bright_baseline.toml
```

### MIRACL
```bash
export MIRACL_DATASET="miracl/miracl"
export MIRACL_LANGUAGE="es"  # Try different languages
export MIRACL_SPLIT="train"

prime rl run configs/bright_baseline.toml
```

---

## Monitoring Dashboard Commands

### Check Status
```bash
# Latest result
tail -1 results.jsonl | jq '.evaluation.mteb_scores.primary_score'

# Full leaderboard
cat leaderboard.tsv | column -t

# Active runs
prime rl status

# Specific run metrics
prime rl metrics <run-id> | jq '.evaluation'
```

### Monitor Live
```bash
# Watch results stream
tail -f results.jsonl | jq '{timestamp, dataset: .dataset.name, score: .evaluation.mteb_scores.primary_score, contaminated: .evaluation.contamination.passed | not}'

# Watch run logs
prime rl logs <run-id> -f
```

### Validate Contamination
```bash
# Check latest run
tail -1 results.jsonl | jq '.evaluation.contamination'

# Per-task breakdown
tail -1 results.jsonl | jq '.evaluation.contamination.per_task'

# Flag any failure
cat results.jsonl | jq -r 'select(.evaluation.contamination.passed | not) | "\(.dataset.name): CONTAMINATED (\(.evaluation.contamination.overall_rate))"'
```

---

## Troubleshooting

### Build Fails: "RuntimeError: OpenEnv project is missing .build.json"
**During:** `prime env build bright-retrieval`

**Solution:**
1. Check Docker is running: `docker ps`
2. Check syntax: `python3 -m py_compile environments/bright_retrieval/proj/server/app.py`
3. Check create_app is present: `grep "app = create_app" environments/bright_retrieval/proj/server/app.py`
4. Rebuild: `prime env build bright-retrieval --path environments` (verbose)

### First Run: "RuntimeError: OpenEnv project is missing .build.json"
**During:** `prime rl run configs/bright_baseline.toml`

**Solution:**
1. Verify build succeeded: `ls environments/bright_retrieval/proj/.build.json`
2. Verify push succeeded: `prime env list` shows version 0.1.1+
3. Stop old run: `prime rl stop <old-run-id>`
4. Launch again: `prime rl run configs/bright_baseline.toml`

### Contamination Detected
**In:** results.jsonl shows `contamination.passed: false`

**Solution:**
1. Check which dataset: `tail -1 results.jsonl | jq '.dataset.name'`
2. Check per-task: `tail -1 results.jsonl | jq '.evaluation.contamination.per_task'`
3. Mark as risky in DATASET_INVENTORY.md
4. Switch to safe dataset for next run
5. Investigate: Is dataset published with MTEB tests?

### Score Didn't Improve
**After:** 5+ runs on same dataset

**Solution:**
1. Compute gradient: Is score trending up or down?
2. If plateau (gradient < 0.1): Switch dataset
3. If declining: Previous dataset was better, switch back
4. If stable: Continue current (may need more data)

---

## File Structure After Deployment

```
agenthub/
├── environments/
│   ├── bright_retrieval/
│   │   ├── proj/
│   │   │   ├── server/
│   │   │   │   └── app.py (WITH gym contract + env vars)
│   │   │   ├── .build.json ✨ (created by prime env build)
│   │   │   └── pyproject.toml (updated with datasets>=2.0.0)
│   │   └── bright_retrieval.py
│   ├── followir_retrieval/
│   │   ├── proj/
│   │   │   ├── server/
│   │   │   │   └── app.py (WITH gym contract + env vars)
│   │   │   ├── .build.json ✨ (created by prime env build)
│   │   │   └── pyproject.toml (updated with datasets>=2.0.0)
│   │   └── followir_retrieval.py
│   └── miracl_retrieval/
│       ├── proj/
│       │   ├── server/
│       │   │   └── app.py (WITH gym contract + env vars)
│       │   ├── .build.json ✨ (created by prime env build)
│       │   └── pyproject.toml (updated with datasets>=2.0.0)
│       └── miracl_retrieval.py
├── configs/
│   ├── bright_baseline.toml
│   ├── followir_baseline.toml
│   └── miracl_baseline.toml
├── scripts/
│   └── autonomous_researcher.py ✨ (deploy Phase 2)
├── results.jsonl (auto-populated by runs)
├── leaderboard.tsv (auto-generated, human-readable)
├── CLAUDE.md (updated with agent guidelines)
├── MODS_FOR_RL.md (RL paradigm differences)
├── AUTONOMOUS_RESEARCH_PROTOCOL.md (Phase 2-3)
├── DATASET_INVENTORY.md (available datasets)
└── [11 other documentation files]
```

---

## Safety Checklist (Before Going 24/7)

- [ ] All three environments build without errors
- [ ] All three environments push successfully (0.1.1+)
- [ ] Test run completes without "missing .build.json" error
- [ ] Contamination check passes on test run
- [ ] Results parse correctly (all MTEB tasks present)
- [ ] Git workflow tested (commit + push)
- [ ] Autonomous researcher script written & tested locally
- [ ] Cron job or supervisor configured
- [ ] Monitoring dashboard set up
- [ ] Alerting configured (email/Slack on failure)
- [ ] 24h dry-run completed without crashes
- [ ] Human review of 24h results completed

---

## Emergency Procedures

### Stop All Runs
```bash
prime rl status | grep RUNNING | awk '{print $1}' | xargs -I{} prime rl stop {}
```

### Investigate Contaminated Results
```bash
# Find contamination failures
cat results.jsonl | jq -r 'select(.evaluation.contamination.passed | not) | "\(.timestamp) \(.dataset.name): \(.evaluation.contamination.overall_rate)"'

# Check which dataset caused it
tail -10 results.jsonl | jq '.dataset.name'
```

### Roll Back to Last Known Good
```bash
# If agent makes bad decisions:
git log --oneline | head -5
git revert <commit-id>  # Revert problematic decision
git push
```

### Manual Override
```bash
# Force specific dataset for next run
export BRIGHT_DATASET="google-research-datasets/BRIGHT"
export BRIGHT_CONFIG="gpt4_reason"
prime rl run configs/bright_baseline.toml  # This run only
```

---

## Success Metrics Dashboard

### Week 1
```
target: primary_score ≥ 60
tracking: cat leaderboard.tsv | tail -10
```

### Week 2-3
```
target: primary_score ≥ 70
tracking: cat leaderboard.tsv | tail -20
```

### Week 4
```
target: primary_score ≥ 75
tracking: cat leaderboard.tsv | tail -30
```

---

## Next Steps

1. **Read key documents** (90 min):
   - IMPLEMENTATION_COMPLETE.md
   - CLAUDE.md (agent guidelines)
   - MODS_FOR_RL.md (paradigm differences)

2. **Build environments** (30 min):
   - `prime env build` × 3
   - `prime env push` × 3

3. **Test first run** (30-60 min):
   - `prime rl run configs/bright_baseline.toml`
   - Monitor & validate contamination

4. **Deploy Phase 2** (2-4 hours):
   - Write autonomous_researcher.py
   - Set up cron/supervisor
   - Monitor 48h operation

5. **Analyze & iterate** (Week 2-4):
   - Refine decision logic based on 10+ runs
   - Explore new datasets
   - Push towards SOTA

---

**Questions?** See CLAUDE.md for comprehensive agent guidelines.
**Technical details?** See OPENENV_FIX_SUMMARY.md for gym contract implementation.
**Full roadmap?** See AUTONOMOUS_RESEARCH_PROTOCOL.md for Phase 2-3 orchestration.

Ready to begin. 🚀
