# EXECUTE NOW: Complete Deployment Guide

**Updated:** March 12, 2026
**Status:** Ready to execute

---

## Current State

✅ All code implemented and committed
✅ All documentation completed
✅ Syntax validated
✅ **Your machine has Podman + Colima** (better than Docker Desktop!)
✅ Ready for Phase 1 build & deployment

---

## What You Need to Do (In Order)

### Phase 1: Build & Push (30 min - 2 hours depending on network/build speed)

#### Step 1: Start Podman via Colima
Your machine has **Podman 5.2.5 + Colima 0.8.0** pre-installed (better for M2 Ultra than Docker Desktop!)

```bash
colima start
```

Wait for output:
```
INFO[0020] colima is running
```

Verify it works:
```bash
podman ps
```

See: **DOCKER_SETUP_PODMAN.md** for detailed Podman setup & troubleshooting

#### Step 2: Run Build Script
```bash
/tmp/build_and_deploy.sh
```

This script will:
1. ✅ Check Docker is running
2. ✅ Validate Python syntax
3. ✅ Build BRIGHT environment (creates .build.json)
4. ✅ Build FollowIR environment (creates .build.json)
5. ✅ Build MIRACL environment (creates .build.json)
6. ✅ Push BRIGHT to registry (0.1.1)
7. ✅ Push FollowIR to registry (0.1.1)
8. ✅ Push MIRACL to registry (0.1.1)

**Expected output:**
```
[9/9] Pushing MIRACL environment...
✅ MIRACL pushed successfully

✅ Phase 1 Complete: All Environments Built & Pushed
```

**If it fails:**
- Check Docker is running: `docker ps`
- Check network: Try `ping 8.8.8.8`
- Check Prime Labs CLI: `which prime`
- See: README_DEPLOYMENT.md → Troubleshooting

---

### Phase 2: Test First Run (1-4 hours depending on dataset size + model)

#### Step 1: Launch Test Run
```bash
cd /Users/pierre/gourmand/agenthub
prime rl run configs/bright_baseline.toml
```

**Expected output:**
```
Run ID: wg6mko1s5l1fok3ij57l3h96
Status: PENDING
```

**Save the run ID** — you'll need it for monitoring.

#### Step 2: Monitor Training
```bash
# Watch logs (replace <run-id> with actual ID from Step 1)
prime rl logs <run-id> -f

# Expect to see:
# - "Installing environment"
# - "Successfully installed environment"
# - "Starting training loop"
# - "Step 1/1000", "Step 2/1000", etc.
# - Eventually: "Training complete"
```

**Let this run** — it will take 1-4 hours depending on dataset.

#### Step 3: Check Status (While Waiting)
```bash
# In another terminal, check status periodically
prime rl status <run-id>

# Should show: RUNNING, then eventually COMPLETED
```

#### Step 4: Verify Contamination (When Complete)
```bash
# When training finishes, check metrics
prime rl metrics <run-id> | jq '.evaluation.contamination.passed'

# Expected output: true

# If false, see: CLAUDE.md → Debugging → Contamination Detected
```

#### Step 5: Commit Results
```bash
# If contamination.passed == true:
git add results.jsonl
git commit -m "result: BRIGHT baseline run completed - phase 1 validation"
git push
```

---

### Phase 3: Deploy Autonomous Agent (Next 48 hours)

Once Phase 1 test run completes successfully, deploy the autonomous researcher:

#### Step 1: Review Autonomous Researcher Script
```bash
cat scripts/autonomous_researcher.py | head -50
```

Script is ready to use. It implements:
- Read latest results
- Detect plateau (gradient analysis)
- Select next dataset based on decision tree
- Set environment variables
- Launch prime rl run
- Monitor for completion
- Validate contamination
- Commit to git
- Repeat every 2-4 hours

#### Step 2: Set Up Cron Job (Option A: Lightweight)
```bash
# Edit crontab
crontab -e

# Add this line (runs every 2 hours):
0 */2 * * * cd /Users/pierre/gourmand/agenthub && python3 scripts/autonomous_researcher.py >> autonomous_researcher.log 2>&1

# Save and exit (Cmd+X in nano, then Y)
```

#### Step 3: Set Up Supervisor (Option B: Robust, Recommended)
```bash
# Create supervisor config
cat > /tmp/autonomous_researcher.conf << 'EOF'
[program:autonomous_researcher]
command=python3 /Users/pierre/gourmand/agenthub/scripts/autonomous_researcher.py
directory=/Users/pierre/gourmand/agenthub
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/Users/pierre/gourmand/agenthub/autonomous_researcher.log
user=pierre
EOF

# Install supervisor if needed
brew install supervisor

# Copy config
sudo cp /tmp/autonomous_researcher.conf /usr/local/etc/supervisor.d/

# Start supervisor
supervisord
supervisorctl reread
supervisorctl update
supervisorctl start autonomous_researcher
```

#### Step 4: Monitor Autonomous Operation
```bash
# Watch log in real-time
tail -f autonomous_researcher.log

# Expected to see:
# - "Iteration 1 — 2026-03-12T..."
# - "Selected: BRIGHT (First run - baseline)"
# - "Launching: prime rl run..."
# - "Run ... COMPLETED"
# - "Iteration 2 — ..."
# - Repeats every 2-4 hours

# Check status
cat leaderboard.tsv | tail -10

# Should show growing list of runs with improving scores
```

---

## Success Criteria Checklist

### Phase 1 Complete ✅
- [ ] Docker running
- [ ] Build script executed successfully
- [ ] All 3 environments built (no .build.json errors)
- [ ] All 3 environments pushed (0.1.1+)
- [ ] No "missing .build.json" errors

### Phase 2 Complete ✅
- [ ] Test run launched: `prime rl run configs/bright_baseline.toml`
- [ ] Test run completed (took 1-4 hours)
- [ ] Contamination check passed: `contamination.passed == true`
- [ ] Results committed to git
- [ ] `results.jsonl` has one entry

### Phase 3 Complete ✅ (After 48h)
- [ ] Autonomous researcher running continuously
- [ ] 5+ training runs completed
- [ ] All results pass contamination check
- [ ] `leaderboard.tsv` shows 5+ results
- [ ] Primary score ≥ 60 on at least one dataset
- [ ] Agent log shows no crashes for 48h

---

## Troubleshooting Quick Reference

### Build fails: "RuntimeError: OpenEnv project is missing .build.json"
**Solution:**
1. Check: `docker ps` (is Docker running?)
2. Check: `python3 -m py_compile environments/bright_retrieval/proj/server/app.py`
3. Check: `grep "app = create_app" environments/bright_retrieval/proj/server/app.py`
4. Rebuild: `prime env build bright-retrieval --path environments -v` (verbose)

### First run shows "missing .build.json" error
**Solution:**
1. Verify build: `ls environments/bright_retrieval/proj/.build.json`
2. Verify push: `prime env list | grep bright`
3. Stop old run: `prime rl stop <run-id>`
4. Relaunch: `prime rl run configs/bright_baseline.toml`

### Contamination check failed
**Solution:**
1. Check which dataset: `tail -1 results.jsonl | jq '.dataset.name'`
2. Mark as risky: Update DATASET_INVENTORY.md
3. Next run will select different dataset
4. Never ignore contamination — result is invalid if `contamination.passed == false`

### Score not improving
**Solution (this happens, give it time):**
1. Let autonomous agent run 5-10 iterations
2. Agent automatically switches datasets when plateau detected
3. Different datasets will have different signal quality
4. After 10+ runs, analyze which datasets work best

---

## Time Estimates

| Phase | Task | Time |
|-------|------|------|
| 1 | Start Docker | 2 min |
| 1 | Run build script | 30-60 min (depends on network) |
| 1 | Verify builds & pushes | 5 min |
| **2** | **Launch test run** | **1-4 hours** |
| 2 | Monitor & verify | 10 min |
| 2 | Commit results | 5 min |
| **3** | **Deploy autonomous agent** | **5 min setup + 48h operation** |
| 3 | Monitor for 48h | 15 min/day (human review) |

**Total to Phase 2 operational:** ~2-5 hours
**Total to Phase 3 insights:** 2-3 days

---

## What NOT to Do

❌ Don't edit code while training is running
❌ Don't bypass contamination checks
❌ Don't force push to git
❌ Don't modify src/eval/ or contamination.py (read-only boundaries)
❌ Don't expect instant results (MTEB evaluation takes time)
❌ Don't ignore contamination failures (they're critical)

---

## What to Monitor

### Real-Time (While Training)
```bash
prime rl logs <run-id> -f
```
Watch for:
- ✅ "Successfully installed environment"
- ✅ "Starting training"
- ❌ NOT: "RuntimeError: OpenEnv project is missing .build.json"

### Daily (After Each Run)
```bash
tail -1 results.jsonl | jq '.evaluation'
cat leaderboard.tsv | tail -5
```
Watch for:
- ✅ All results have `contamination.passed: true`
- ✅ Primary score is increasing (or switching datasets if plateau)
- ✅ No NaN values

### Weekly (Phase 3 onwards)
```bash
cat leaderboard.tsv | tail -20
```
Analyze:
- Which datasets improved score most?
- Which plateaued?
- What's the trend?

---

## Commands Quick Reference

```bash
# Phase 1: Build & Push
/tmp/build_and_deploy.sh

# Phase 2: Test
prime rl run configs/bright_baseline.toml
prime rl logs <run-id> -f
prime rl metrics <run-id> | jq '.evaluation.contamination.passed'

# Phase 3: Autonomous (after Phase 2 succeeds)
crontab -e  # Add: 0 */2 * * * cd /path && python3 scripts/autonomous_researcher.py
tail -f autonomous_researcher.log
cat leaderboard.tsv | tail -10

# Monitoring
prime rl status
prime rl logs <run-id>
git log --oneline -5
cat results.jsonl | tail -1 | jq '.'
```

---

## Next: By Priority

### THIS HOUR
1. Read: START_HERE.md (5 min)
2. Read: README_DEPLOYMENT.md → Quick Start (10 min)
3. Check: Docker Desktop is installed & working
4. Start: Docker Desktop

### TODAY
1. Run: `/tmp/build_and_deploy.sh`
2. Watch: Build progress (30-60 min)
3. Launch: `prime rl run configs/bright_baseline.toml`
4. Monitor: `prime rl logs <run-id> -f`

### TOMORROW (When Phase 2 Run Completes)
1. Verify: Contamination check passed
2. Commit: `git add results.jsonl && git commit`
3. Deploy: Autonomous researcher script
4. Monitor: 48h autonomous operation

### WEEK 2-4
1. Analyze results (which datasets work?)
2. Refine decision logic
3. Explore new datasets
4. Push towards SOTA (score ≥ 75)

---

## Support

**Questions about execution?** See: README_DEPLOYMENT.md
**Questions about agent?** See: CLAUDE.md
**Questions about datasets?** See: DATASET_INVENTORY.md
**Technical issues?** See: OPENENV_FIX_SUMMARY.md
**Troubleshooting?** See: README_DEPLOYMENT.md → Troubleshooting

---

## Ready to Execute?

```bash
# Step 1: Start Docker Desktop (do this first!)

# Step 2: Run this
/tmp/build_and_deploy.sh

# Step 3: When complete, run this
prime rl run configs/bright_baseline.toml

# Step 4: Monitor
prime rl logs <run-id> -f
```

**Let's go!** 🚀
