# START HERE: OpenEnv RL + 24/7 MTEB Optimization

**Last Updated:** March 12, 2026
**Status:** ✅ Ready for Phase 1 Deployment

---

## What This Is

An autonomous, 24/7 embedding model research system that:
- Trains on retrieval benchmarks (BRIGHT, FollowIR, MIRACL) via Prime Labs RL
- Automatically explores different datasets to find best training signal
- Enforces zero contamination in MTEB evaluation
- Achieves SOTA or near-SOTA results through continuous iteration

**Unlike autoresearch-embed:** Agent doesn't edit training code. Instead, agent selects datasets and lets Prime Labs RL handle training.

---

## Quick Start (5 minutes)

### 1. Understand the System
Read in this order (15 min total):
- **IMPLEMENTATION_COMPLETE.md** — 2 min overview
- **CLAUDE.md** — 8 min agent daily workflow
- **MODS_FOR_RL.md** — 5 min (RL vs supervised differences)

### 2. Deploy Phase 1 (30 min)
```bash
cd /Users/pierre/gourmand/agenthub
prime env build bright-retrieval --path environments
prime env build followir-retrieval --path environments
prime env build miracl-retrieval --path environments

# Then push
cd environments/bright_retrieval && prime env push
cd ../followir_retrieval && prime env push
cd ../miracl_retrieval && prime env push
```

### 3. Test First Run (1 hour)
```bash
# Launch test
prime rl run configs/bright_baseline.toml

# Monitor
prime rl logs <run-id> -f

# Verify contamination
prime rl metrics <run-id> | jq '.evaluation.contamination.passed'
# Should return: true
```

### 4. Deploy Phase 2 (Next 48 hours)
Write autonomous_researcher.py (template in AUTONOMOUS_RESEARCH_PROTOCOL.md) and let it run unattended.

---

## Document Index (Read in This Order)

### First Read (Orient Yourself)
| Document | Purpose | Time | Must Read? |
|----------|---------|------|-----------|
| **START_HERE.md** | This file — entry point | 5 min | ✅ |
| **IMPLEMENTATION_COMPLETE.md** | Executive summary of all 3 phases | 10 min | ✅ |
| **README_DEPLOYMENT.md** | Step-by-step deployment guide | 15 min | ✅ |

### Second Read (Understand the System)
| Document | Purpose | Time | Must Read? |
|----------|---------|------|-----------|
| **CLAUDE.md** | Agent daily workflow, constraints, decision logic | 15 min | ✅ |
| **MODS_FOR_RL.md** | How RL differs from autoresearch-embed | 10 min | ✅ |
| **AUTONOMOUS_RESEARCH_PROTOCOL.md** | Phase 2-3 full roadmap | 20 min | ✅ |

### Third Read (Specific Tasks)
| Document | Purpose | Time | Read When? |
|----------|---------|------|-----------|
| **DATASET_INVENTORY.md** | Available datasets, decision tree | 10 min | Phase 2 start |
| **BUILD_AND_PUSH_COMMANDS.md** | Quick command reference | 5 min | During Phase 1 |
| **IMPLEMENTATION_VALIDATION.md** | Pre-build checklist | 5 min | Before building |
| **OPENENV_FIX_SUMMARY.md** | Technical gym contract details | 15 min | If troubleshooting |

---

## The Three Phases

### Phase 1: Build & Validate ✅ READY
**Goal:** Verify all three OpenEnv environments build, push, and run without errors.

**What changed:**
- All three environments added `create_app()` gym contract
- All three accept environment variables for dataset selection
- No Docker rebuild needed to swap datasets

**Time commitment:** 2-3 hours

**Key files:**
- environments/*/proj/server/app.py (WITH gym contract)
- IMPLEMENTATION_VALIDATION.md (pre-build checklist)
- BUILD_AND_PUSH_COMMANDS.md (quick reference)

**Success criteria:**
- ✅ Environments build without errors
- ✅ `.build.json` created in each proj/
- ✅ Test run completes without "missing .build.json"
- ✅ Contamination check passes

---

### Phase 2: Autonomous Agent ✅ DOCUMENTED
**Goal:** Deploy autonomous researcher script that makes dataset decisions and validates results.

**What's needed:**
- Write `scripts/autonomous_researcher.py` (template provided)
- Set up cron job or supervisor for 24/7 operation
- Monitor results daily (15 min/day)

**Time commitment:** 48h continuous operation

**Key files:**
- AUTONOMOUS_RESEARCH_PROTOCOL.md (Phase 2 section)
- CLAUDE.md (agent daily workflow)
- DATASET_INVENTORY.md (dataset selection decision tree)

**Success criteria:**
- ✅ 5+ complete training runs from different datasets
- ✅ All results pass contamination checks
- ✅ Primary score ≥ 60 on at least one dataset
- ✅ Autonomous loop runs 48h without human intervention

---

### Phase 3: Intelligent Orchestration ✅ DOCUMENTED
**Goal:** Achieve SOTA or near-SOTA through intelligent dataset selection and ablations.

**What's needed:**
- Analyze 10+ runs to understand dataset signal quality
- Enhance decision logic (convergence detection, plateau handling)
- Explore new datasets and architecture changes
- Document findings for publication

**Time commitment:** 2-4 weeks

**Key files:**
- AUTONOMOUS_RESEARCH_PROTOCOL.md (Phase 3 section)
- DATASET_INVENTORY.md (exploration candidates)
- MODS_FOR_RL.md (how to trigger ablations)

**Success criteria:**
- ✅ 20-30 complete runs
- ✅ Primary score ≥ 70 (SOTA territory)
- ✅ Zero contamination violations
- ✅ Code ready for publication

---

## Key Concepts

### Contamination (CRITICAL)
Every result must pass a contamination check: <1% overlap with MTEB test sets.

**If contamination.passed == false:**
- Result is INVALID
- Do NOT add to leaderboard
- Investigate which dataset caused it
- Mark dataset as risky in DATASET_INVENTORY.md

**Why it matters:** A single contaminated result can invalidate the entire benchmark comparison.

### Environment Variables (Game Changer)
Dataset swaps NO LONGER require Docker rebuild:

**Before (old):**
```
Edit app.py → prime env build → prime env push → wait 15 min → relaunch
```

**After (new):**
```
export BRIGHT_DATASET=new-dataset → prime rl run → instant!
```

### Agent Decision Tree (The Brain)
Agent makes simple decisions based on results:
1. Read latest score
2. Detect plateau (gradient < 0.1 for 5+ runs?)
3. If plateau: switch dataset
4. If improving: continue current
5. If stuck for 6+ hours: trigger ablation

### Integrity Boundaries (Safety)
**Can modify:**
- Environment variables (safe)
- Dataset selection logic (safe)
- scripts/autonomous_researcher.py (safe)

**Cannot modify:**
- src/eval/contamination.py (read-only)
- src/eval/mteb_runner.py (read-only)
- Prime Labs RL infrastructure (read-only)

---

## Decision Logic Flowchart

```
Latest Result
       ↓
   ┌─Contamination Check
   │   ├─ FAILED → Reject result, mark dataset, try different dataset
   │   └─ PASSED ↓
   │
   ├─ Analyze Gradient (last 5 runs)
   │   ├─ Improving (>0.3/run) → Continue current dataset
   │   ├─ Plateau (<0.1/run, 5+ runs) → Switch dataset
   │   ├─ Declining (<0, 3+ runs) → Switch back to previous dataset
   │   └─ Stuck (6+ hours, no progress) → Trigger ablation
   │
   ├─ Select Next Dataset
   │   ├─ Score < 50 → BRIGHT
   │   ├─ Score < 60 → FollowIR
   │   ├─ Score < 70 → MIRACL-en
   │   └─ Score ≥ 70 → MIRACL alternate languages or synthetic
   │
   └─ Set Environment Variables → Launch prime rl run → Monitor
```

---

## Common Questions

### Q: Why is contamination so important?
**A:** If your training data overlaps with MTEB test sets, the benchmark score is meaningless. You're not measuring generalization; you're measuring memorization. Contamination gating prevents this.

### Q: How is this different from autoresearch-embed?
**A:** autoresearch-embed has the agent edit training code. Here, the agent selects datasets. Training is handled by Prime Labs RL infrastructure. See MODS_FOR_RL.md for full explanation.

### Q: Can I modify the reward function?
**A:** Yes, but it's in OpenEnv environments (proj/server/app.py). You'd need to rebuild the Docker image with `prime env build`. Only do this if you need fundamentally different reward signal.

### Q: What if a dataset is contaminated?
**A:** Mark it in DATASET_INVENTORY.md as risky, switch to a safe dataset, and investigate. Never ignore contamination.

### Q: Can the agent run completely unattended?
**A:** Yes! Phase 2 is designed for 48h+ autonomous operation. You can review results daily (15 min) but the agent makes all decisions.

### Q: What's the expected timeline to SOTA?
**A:** Week 1: Score ≥60, Week 2-3: Score ≥70, Week 4: Score ≥75+. Depends on dataset signal quality and hardware.

---

## Next Steps: By Priority

### TODAY (Now)
- [ ] Read: IMPLEMENTATION_COMPLETE.md (2 min)
- [ ] Read: CLAUDE.md (8 min)
- [ ] Read: README_DEPLOYMENT.md (15 min)
- [ ] Skim: MODS_FOR_RL.md (5 min)

### THIS WEEK (Phase 1)
- [ ] Run: `prime env build bright-retrieval --path environments`
- [ ] Run: `prime env build followir-retrieval --path environments`
- [ ] Run: `prime env build miracl-retrieval --path environments`
- [ ] Run: `cd environments/bright_retrieval && prime env push` (etc. for other two)
- [ ] Test: `prime rl run configs/bright_baseline.toml`
- [ ] Verify: Contamination check passes
- [ ] Commit: Results to git

### NEXT WEEK (Phase 2)
- [ ] Write: `scripts/autonomous_researcher.py` (template in AUTONOMOUS_RESEARCH_PROTOCOL.md)
- [ ] Deploy: Cron job or supervisor
- [ ] Monitor: 48h autonomous operation
- [ ] Analyze: Results after 5+ runs
- [ ] Iterate: Refine decision logic

### WEEKS 2-4 (Phase 3)
- [ ] Explore: New datasets from DATASET_INVENTORY.md
- [ ] Ablate: Architecture/loss when plateau detected
- [ ] Document: Findings for publication
- [ ] Push: Towards SOTA (score ≥ 75)

---

## Support & Troubleshooting

### Troubleshooting Guide
See: **README_DEPLOYMENT.md** → "Troubleshooting" section

### Common Issues
```
"RuntimeError: OpenEnv project is missing .build.json"
→ See: BUILD_AND_PUSH_COMMANDS.md, Troubleshooting

"Contamination detected on run"
→ See: CLAUDE.md → Debugging section

"Score not improving"
→ See: AUTONOMOUS_RESEARCH_PROTOCOL.md → Phase 2
```

### Emergency Procedures
See: **README_DEPLOYMENT.md** → "Emergency Procedures"

---

## File Checklist (All Included)

**Code Changes (6 files):**
- ✅ environments/bright_retrieval/proj/server/app.py
- ✅ environments/bright_retrieval/proj/pyproject.toml
- ✅ environments/followir_retrieval/proj/server/app.py
- ✅ environments/followir_retrieval/proj/pyproject.toml
- ✅ environments/miracl_retrieval/proj/server/app.py
- ✅ environments/miracl_retrieval/proj/pyproject.toml

**Documentation (12 files):**
- ✅ START_HERE.md (this file)
- ✅ IMPLEMENTATION_COMPLETE.md
- ✅ README_DEPLOYMENT.md
- ✅ CLAUDE.md (UPDATED)
- ✅ MODS_FOR_RL.md
- ✅ AUTONOMOUS_RESEARCH_PROTOCOL.md
- ✅ DATASET_INVENTORY.md
- ✅ BUILD_AND_PUSH_COMMANDS.md
- ✅ IMPLEMENTATION_VALIDATION.md
- ✅ OPENENV_FIX_SUMMARY.md
- ✅ memory/rl_openenv_setup.md
- ✅ memory/MEMORY.md (UPDATED)

**Commits (6 total):**
- ✅ 92b101a — Fix: Implement OpenEnv gym contract
- ✅ 68ad2df — Docs: Implementation guides & validation
- ✅ 825690a — Feat: Environment variable support
- ✅ 69559da — Docs: Comprehensive RL autonomy guidelines
- ✅ e2ee941 — Docs: Final implementation summary
- ✅ bb1b247 — Docs: Detailed deployment guide

---

## Ready to Deploy?

If you've read the first 3 documents and understand the system, you're ready:

```bash
# Phase 1: Build
prime env build bright-retrieval --path environments
prime env build followir-retrieval --path environments
prime env build miracl-retrieval --path environments

# Then push & test
cd environments/bright_retrieval && prime env push
# ... etc

# Phase 2: Autonomous (Week 1-2)
# Deploy scripts/autonomous_researcher.py

# Phase 3: SOTA Push (Week 2-4)
# Intelligent selection & ablations
```

---

**Questions?** See CLAUDE.md.
**Setup steps?** See README_DEPLOYMENT.md.
**Technical details?** See OPENENV_FIX_SUMMARY.md.

Let's optimize embeddings. 🚀
