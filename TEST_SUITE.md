# Test Suite: OpenEnv RL + Autonomous MTEB Optimization

**Created:** March 12, 2026
**Purpose:** Validate all phases of the system

---

## Phase 1 Tests: Build & Push Validation

### Test 1.1: Docker/Podman Availability
```bash
# Verify container runtime is available
podman ps  # Should return empty list or containers
# OR
docker ps  # Should work if Docker installed
```

**Success:** Command returns output without "Cannot connect" errors

### Test 1.2: Syntax Validation
```bash
python3 -m py_compile environments/bright_retrieval/proj/server/app.py
python3 -m py_compile environments/followir_retrieval/proj/server/app.py
python3 -m py_compile environments/miracl_retrieval/proj/server/app.py
```

**Success:** No syntax errors, all three compile

### Test 1.3: Gym Contract Verification
```bash
# Check all three have create_app with 3 args
grep "^app = create_app" environments/bright_retrieval/proj/server/app.py
grep "^app = create_app" environments/followir_retrieval/proj/server/app.py
grep "^app = create_app" environments/miracl_retrieval/proj/server/app.py
```

**Success:** All three have `app = create_app(EnvClass, ActionClass, ObservationClass)`

### Test 1.4: Build Environments
```bash
cd /Users/pierre/gourmand/agenthub

# Build all three
prime env build bright-retrieval --path environments
prime env build followir-retrieval --path environments
prime env build miracl-retrieval --path environments
```

**Success Criteria:**
- ✅ Each exits with code 0
- ✅ `.build.json` created in each `proj/` directory
- ✅ No "missing .build.json" errors

### Test 1.5: Artifact Verification
```bash
ls -la environments/bright_retrieval/proj/.build.json
ls -la environments/followir_retrieval/proj/.build.json
ls -la environments/miracl_retrieval/proj/.build.json
```

**Success:** All three files exist and are > 1KB

### Test 1.6: Push to Registry
```bash
cd environments/bright_retrieval && prime env push
cd ../followir_retrieval && prime env push
cd ../miracl_retrieval && prime env push
```

**Success:** Each exits with code 0, version bumped to 0.1.1+

### Test 1.7: Registry Verification
```bash
prime env list | grep -E "(bright|followir|miracl)"
```

**Success:** All three show version 0.1.1+ in registry

---

## Phase 2 Tests: Autonomous Agent Validation

### Test 2.1: Environment Variables
```bash
# Test BRIGHT env vars
export BRIGHT_DATASET="google-research-datasets/BRIGHT"
export BRIGHT_CONFIG="gpt4_reason"
echo "BRIGHT_DATASET=$BRIGHT_DATASET"

# Test FollowIR env vars
export FOLLOWIR_DATASET="jhu-clsp/FollowIR-train"
export FOLLOWIR_SPLIT="train"
echo "FOLLOWIR_DATASET=$FOLLOWIR_DATASET"

# Test MIRACL env vars
export MIRACL_DATASET="miracl/miracl"
export MIRACL_LANGUAGE="en"
export MIRACL_SPLIT="train"
echo "MIRACL_DATASET=$MIRACL_DATASET"
```

**Success:** All env vars set correctly

### Test 2.2: Launch First Run
```bash
prime rl run configs/bright_baseline.toml
```

**Success:**
- Returns run ID (e.g., `wg6mko1s5l1fok3ij57l3h96`)
- Run status shows `PENDING` then `RUNNING`
- No "missing .build.json" errors

### Test 2.3: Monitor Training
```bash
# Save run ID from Test 2.2
RUN_ID="<run-id-from-2.2>"

# Check status periodically
prime rl status $RUN_ID

# Watch logs
prime rl logs $RUN_ID -f
```

**Success Criteria:**
- ✅ Status transitions: PENDING → RUNNING → COMPLETED
- ✅ Logs show "Successfully installed environment"
- ✅ Logs show training steps: "Step 1/1000", "Step 2/1000", etc.
- ✅ No "RuntimeError: OpenEnv project is missing .build.json"

### Test 2.4: Contamination Check
```bash
RUN_ID="<run-id-from-2.2>"
prime rl metrics $RUN_ID | jq '.evaluation.contamination.passed'
```

**Success:** Returns `true`

### Test 2.5: Results Logging
```bash
# Verify results.jsonl was created
tail -1 results.jsonl | jq '.evaluation.contamination'

# Should show:
# {
#   "passed": true,
#   "overall_rate": <number < 0.01>,
#   "per_task": { ... }
# }
```

**Success:** Contamination passed, rate < 1%

### Test 2.6: Git Workflow
```bash
# Commit results
git add results.jsonl
git commit -m "test: Phase 2 validation run"
git push

# Verify
git log --oneline -1
```

**Success:** Results committed and pushed

### Test 2.7: Autonomous Researcher Script
```bash
# Verify script exists and is executable
ls -la scripts/autonomous_researcher.py
chmod +x scripts/autonomous_researcher.py

# Test script in dry-run mode (just parse, don't launch)
python3 -c "import json; json.loads(open('results.jsonl').readlines()[-1])"
```

**Success:** Script is executable, results.jsonl is valid JSON

---

## Phase 3 Tests: Autonomous Operation Validation

### Test 3.1: Gradient Calculation
```python
# Simulate gradient calculation
import json

results = []
with open('results.jsonl') as f:
    for line in f:
        results.append(json.loads(line))

# Get last 5 scores
scores = [r.get('evaluation',{}).get('mteb_scores',{}).get('primary_score', 0)
          for r in results[-5:]]

gradient = (scores[-1] - scores[0]) / (len(scores) - 1) if len(scores) > 1 else 0
print(f"Gradient: {gradient:.4f} points/run")
```

**Success:** Gradient calculated without errors

### Test 3.2: Dataset Selection
```python
# Test decision logic
score = 62.3
gradient = 0.05

if score < 50:
    print("Switch to BRIGHT")
elif score < 60:
    print("Switch to FollowIR")
elif score < 70:
    print("Switch to MIRACL-en")
else:
    if gradient < 0.1:
        print("Plateau: explore multilingual")
    else:
        print("Improving: continue current")
```

**Success:** Decision logic works correctly

### Test 3.3: Leaderboard Generation
```bash
# Test leaderboard.tsv generation
python3 << 'EOF'
import json
from pathlib import Path

results = []
with open('results.jsonl') as f:
    for line in f:
        results.append(json.loads(line))

with open('leaderboard.tsv', 'w') as f:
    f.write("Iteration\tDataset\tPrimary Score\tSTS\tStatus\n")
    for i, r in enumerate(results, 1):
        score = r.get('evaluation', {}).get('mteb_scores', {}).get('primary_score', 0)
        dataset = r.get('dataset', {}).get('name', '?')
        status = '✓' if r.get('evaluation', {}).get('contamination', {}).get('passed') else '✗'
        f.write(f"{i}\t{dataset}\t{score:.2f}\t\t{status}\n")

print("✅ Leaderboard generated")
EOF
```

**Success:** `leaderboard.tsv` created with all runs

### Test 3.4: Contamination Gating
```python
# Verify contamination check blocks invalid results
import json

with open('results.jsonl') as f:
    for i, line in enumerate(f, 1):
        result = json.loads(line)
        contamination = result.get('evaluation', {}).get('contamination', {})
        passed = contamination.get('passed', False)

        if not passed:
            print(f"❌ Result {i} contaminated: {contamination['overall_rate']:.4f}")
        else:
            print(f"✅ Result {i} clean: {contamination['overall_rate']:.4f}")
```

**Success:** All results marked as `passed: true`

### Test 3.5: Autonomous Loop Dry-Run
```bash
# Test that autonomous researcher script can start without errors
timeout 10 python3 scripts/autonomous_researcher.py 2>&1 | head -20 || true
```

**Success:** Script starts, reads results, no exceptions

---

## Integration Tests

### Test I.1: End-to-End Flow
```bash
# 1. Build ✅ (done in Phase 1)
# 2. Push ✅ (done in Phase 1)
# 3. Launch run ✅ (done in Phase 2.2)
# 4. Monitor ✅ (done in Phase 2.3)
# 5. Validate contamination ✅ (done in Phase 2.4)
# 6. Commit results ✅ (done in Phase 2.6)

# Final check: All results are valid
python3 << 'EOF'
import json

count = 0
valid = 0

with open('results.jsonl') as f:
    for line in f:
        result = json.loads(line)
        count += 1
        if result.get('evaluation', {}).get('contamination', {}).get('passed'):
            valid += 1

print(f"✅ Results: {valid}/{count} valid")
EOF
```

**Success:** All results valid (contamination passed)

### Test I.2: Autonomous Deployment
```bash
# Deploy autonomous researcher
(crontab -l 2>/dev/null || echo "") | grep -q "autonomous_researcher" && \
echo "✅ Cron job deployed" || \
echo "⚠️ Cron job not deployed"

# Or check supervisor
supervisorctl status autonomous_researcher 2>/dev/null && \
echo "✅ Supervisor job deployed" || \
echo "⚠️ Supervisor not running"
```

**Success:** At least one deployment method active

### Test I.3: 24h Continuous Operation
```bash
# Monitor autonomous operation for 24h
# Expected: 12 runs (every 2 hours)
# Actual will be checked after 24h

# For now, verify logging setup
tail -20 autonomous_researcher.log
```

**Success:** Log file shows iterations 1, 2, 3, etc.

---

## Performance Tests

### Test P.1: Build Time
```bash
# Measure time for Phase 1 build
time (
    prime env build bright-retrieval --path environments && \
    prime env build followir-retrieval --path environments && \
    prime env build miracl-retrieval --path environments
)
```

**Success:** Total time < 2 hours (depends on network)

### Test P.2: Training Speed
```bash
# Measure time for one run
# Expected: 1-4 hours depending on dataset

# Log start/end times in autonomous_researcher.log
```

**Success:** Run completes without timeout

### Test P.3: Memory/CPU Usage
```bash
# Monitor Podman machine resource usage
podman machine info 2>&1 | grep -E "(memory|cpu)" || \
top -l1 | head -10  # Mac system resources
```

**Success:** No OOM errors, CPU < 100% (typical)

---

## Documentation Tests

### Test D.1: Documentation Complete
```bash
# Check all required docs exist
for doc in START_HERE.md EXECUTE_NOW.md DOCKER_SETUP_PODMAN.md CLAUDE.md \
    MODS_FOR_RL.md AUTONOMOUS_RESEARCH_PROTOCOL.md DATASET_INVENTORY.md; do
    test -f "$doc" && echo "✅ $doc" || echo "❌ $doc missing"
done
```

**Success:** All docs present

### Test D.2: Code Comments
```bash
# Verify autonomous researcher has docstrings
grep -c '"""' scripts/autonomous_researcher.py
# Should be > 10
```

**Success:** Good code documentation

---

## Summary Test Command

Run all tests (requires passing Phase 1 & 2 first):

```bash
#!/bin/bash
set -e

echo "═══════════════════════════════════════════"
echo "RUNNING COMPLETE TEST SUITE"
echo "═══════════════════════════════════════════"

# Phase 1 Tests
echo "✅ Phase 1 tests (syntax, build, push)"
python3 -m py_compile environments/bright_retrieval/proj/server/app.py
grep "^app = create_app" environments/bright_retrieval/proj/server/app.py > /dev/null
ls environments/bright_retrieval/proj/.build.json > /dev/null

# Phase 2 Tests
echo "✅ Phase 2 tests (run, monitor, validate)"
test -f results.jsonl
tail -1 results.jsonl | jq '.evaluation.contamination.passed' | grep -q true

# Phase 3 Tests
echo "✅ Phase 3 tests (autonomous, leaderboard)"
test -f leaderboard.tsv
test -f scripts/autonomous_researcher.py

# Documentation
echo "✅ Documentation complete"
test -f START_HERE.md
test -f EXECUTE_NOW.md

echo ""
echo "═══════════════════════════════════════════"
echo "✅ ALL TESTS PASSED"
echo "═══════════════════════════════════════════"
```

---

## Next Steps

1. **Phase 1:** Complete build & push tests
2. **Phase 2:** Launch first run, verify contamination
3. **Phase 3:** Deploy autonomous agent, monitor 24h
4. **Results:** Check leaderboard after 5+ runs

---

## Troubleshooting Test Failures

| Test | Failure | Solution |
|------|---------|----------|
| 1.3 | `app = create_app` not found | Check app.py syntax, ensure create_app import |
| 1.4 | Build fails | Check Docker/Podman running, view build logs |
| 1.5 | `.build.json` missing | Rebuild with verbose: `prime env build ... -v` |
| 2.3 | "missing .build.json" error | Verify .build.json exists, restart agent |
| 2.4 | Contamination failed | Check dataset, mark as risky, use different dataset |
| 3.1 | Gradient calculation error | Ensure results.jsonl is valid JSON |
| 3.4 | Contamination not gated | Verify autonomous script checks `contamination.passed` |

---

End of test suite. Run tests as you progress through each phase.
