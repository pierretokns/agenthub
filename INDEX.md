# 📚 Complete Cloud Research Documentation Index

**Everything you need to understand, deploy, and operate the cloud research system.**

---

## 🎯 Start Here

**Want to launch immediately?**
→ Read: **[READY_TO_LAUNCH.md](READY_TO_LAUNCH.md)** (5 min)

**Want a quick start?**
→ Read: **[QUICKSTART.md](QUICKSTART.md)** (5 min)

---

## 📖 Documentation Map

### Getting Started
| Document | Time | Purpose |
|----------|------|---------|
| **READY_TO_LAUNCH.md** | 5 min | Launch checklist + expected results |
| **QUICKSTART.md** | 5 min | 3-step launcher guide |
| **SETUP_CHECKLIST.md** | 15 min | Detailed setup with troubleshooting |

### Deployment & Operations
| Document | Time | Purpose |
|----------|------|---------|
| **DEPLOY_FREE_TIER.md** | 10 min | Free tier optimization (L40 GPUs) |
| **LAUNCHCTL_DAEMON.md** | 10 min | Continuous background operation |
| **INFRASTRUCTURE.md** | 20 min | Behind-the-scenes automation |

### Architecture & Design
| Document | Time | Purpose |
|----------|------|---------|
| **CLOUD_RESEARCH.md** | 30 min | Full architecture + design decisions |
| **IMPLEMENTATION_SUMMARY.md** | 20 min | What was built + phase planning |

---

## 🗂️ File Structure

### Core Training (autoresearch-cloud/)

```
autoresearch-cloud/
├── src/
│   ├── train_cuda.py          # 4-stage PyTorch training pipeline
│   ├── model_cuda.py          # ModernBERT bi-encoder wrapper
│   ├── losses_cuda.py         # InfoNCE + EloDistillationLoss
│   └── data_cuda.py           # JSONL dataset loading
├── scripts/
│   ├── experiment.py          # Cloud researcher loop (poll→train→post)
│   ├── setup_node.py          # Pod initialization
│   └── supervisor.sh          # Restart handler for context exhaustion
├── configs/
│   └── training_stages_cuda.yaml  # H100-tuned hyperparameters
└── program.md                 # Cloud agent instructions
```

### Orchestration (agenthub/scripts/)

```
agenthub/scripts/
├── orchestrator.py            # Pod launcher + job assigner + result aggregator
├── install_launchctl.sh       # Daemon installation script
└── manage_orchestrator.sh     # Daemon control (start/stop/logs)
```

### Configuration

```
agenthub/
├── orchestrator_config.yaml   # Pod config + experiment queue
└── launchctl/
    └── com.agenthub.cloud-orchestrator.plist  # Daemon config
```

### Documentation (You are here)

```
agenthub/
├── INDEX.md                   # This file
├── READY_TO_LAUNCH.md         # Launch checklist
├── QUICKSTART.md              # 5-min start
├── SETUP_CHECKLIST.md         # Detailed setup
├── DEPLOY_FREE_TIER.md        # Free tier guide
├── LAUNCHCTL_DAEMON.md        # Daemon docs
├── INFRASTRUCTURE.md          # Automation details
├── CLOUD_RESEARCH.md          # Architecture
└── IMPLEMENTATION_SUMMARY.md  # What was built
```

---

## 🔄 Workflow Overview

```
┌─────────────────────────────────────────────┐
│ 1. Launch Orchestrator                      │
│    python scripts/orchestrator.py           │
└─────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────┐
│ 2. Pods Spin Up (5-10 min)                  │
│    • 4 L40 GPUs (free tier)                 │
│    • Auto-download models                   │
│    • Register with agenthub                 │
└─────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────┐
│ 3. Job Assignment (Automatic)               │
│    • orchestrator.py posts jobs             │
│    • Pods poll for assignments              │
└─────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────┐
│ 4. Training Execution (60-90 min)           │
│    • 4-stage pipeline                       │
│    • WandB logging (live)                   │
│    • Git commits                            │
└─────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────┐
│ 5. Results Collection (Automatic)           │
│    • Post to embed-results                  │
│    • Merge into leaderboard.jsonl           │
│    • Pod auto-terminates                    │
└─────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────┐
│ 6. Next Pod Launches (Auto)                 │
│    • Refill to max_pods=4                   │
│    • Continue until queue empty             │
└─────────────────────────────────────────────┘
```

---

## 📊 Key Metrics

### Current Setup

| Metric | Value |
|--------|-------|
| Free tier pods | 4 |
| GPU type | L40 (48GB VRAM) |
| Experiments queued | 8 |
| Training time per exp | 60-90 min |
| Total runtime | 6-8 hours |
| Cost | $0 |

### Expected Results

| Benchmark | Baseline | zELO (Target) |
|-----------|----------|---------------|
| BRIGHT | 20-24 | 28-33 nDCG@10 |
| FollowIR | 18-22 | 25-28 nDCG@10 |
| Code Search | ~79 | >82 nDCG@10 |
| MIRACL | ~62 | 67+ nDCG@10 |

---

## 🚀 Quick Commands

### Launch & Monitor

```bash
# Install daemon (one-time)
bash scripts/install_launchctl.sh

# Start daemon
bash scripts/manage_orchestrator.sh start

# Monitor logs
bash scripts/manage_orchestrator.sh logs

# Check status
bash scripts/manage_orchestrator.sh status
```

### View Results

```bash
# See all results
cat leaderboard.jsonl | jq .

# Sort by nDCG@10
cat leaderboard.jsonl | jq -s 'sort_by(.nDCG@10) | reverse'

# WandB dashboard
open https://wandb.ai/pierretokns/autoresearch-embed
```

### Manage Pods

```bash
# List pods
prime pods list

# Stream pod logs
prime pods logs <pod-id> --follow

# Terminate pod
prime pods delete <pod-id>
```

---

## 🔍 Decision Tree: Which Doc to Read?

```
Do you want to...

├─ Launch immediately?
│  └─→ READY_TO_LAUNCH.md
│
├─ Understand how to deploy?
│  └─→ QUICKSTART.md
│
├─ Troubleshoot setup issues?
│  └─→ SETUP_CHECKLIST.md
│
├─ Optimize for free tier?
│  └─→ DEPLOY_FREE_TIER.md
│
├─ Understand the architecture?
│  └─→ CLOUD_RESEARCH.md
│
├─ Learn behind-the-scenes automation?
│  └─→ INFRASTRUCTURE.md
│
├─ Set up continuous operation?
│  └─→ LAUNCHCTL_DAEMON.md
│
├─ Understand what was implemented?
│  └─→ IMPLEMENTATION_SUMMARY.md
│
└─ Find a specific document?
   └─→ This INDEX.md
```

---

## 📋 Phase Roadmap

### Phase 1: Multi-Node Orchestration ✅ COMPLETE
- [x] autoresearch-cloud codebase
- [x] orchestrator.py
- [x] Free tier config (4 L40 pods, 8 experiments)
- [x] Documentation
- **Status**: Ready to launch

### Phase 2: Dataset Curation 📋 PLANNED
- [ ] BRIGHT oracle training data
- [ ] FollowIR instruction augmentation
- [ ] Code execution sandbox
- [ ] MIRACL cross-encoder validation
- **Timeline**: 2-4 days (after Phase 1)

### Phase 3: zELO Experiments 📋 PLANNED
- [ ] Run baselines
- [ ] Run zELO with oracle data
- [ ] Generate ablation tables
- [ ] Compare vs SOTA
- **Timeline**: 1 day (after Phase 2)

### Phase 4: Production Scaling 📋 PLANNED
- [ ] Upgrade to H100 GPUs
- [ ] Scale to 16 parallel pods
- [ ] Cloud checkpointing
- [ ] Auto-scaling
- **Timeline**: 1 week (optional, post-Phase 3)

---

## 🔗 External References

### PrimeIntellect
- **Console**: https://primeintellect.ai/console
- **Docs**: https://docs.primeintellect.ai
- **API**: https://api.primeintellect.ai

### WandB
- **Project**: https://wandb.ai/pierretokns/autoresearch-embed
- **Docs**: https://docs.wandb.ai

### Research Papers
- **AgentIR**: https://arxiv.org/abs/2603.04384
- **pplx-embed**: https://arxiv.org/abs/2602.11151
- **Arctic-Embed**: https://huggingface.co/Snowflake/arctic-embed-l

### GitHub
- **agenthub repo**: https://github.com/pierretokns/agenthub
- **autoresearch-cloud**: https://github.com/pierretokns/autoresearch-cloud
- **Issues**: https://github.com/pierretokns/agenthub/issues

---

## 📞 Support

### For Launch Issues
→ **READY_TO_LAUNCH.md** (troubleshooting section)

### For Setup Issues
→ **SETUP_CHECKLIST.md** (troubleshooting section)

### For Daemon Issues
→ **LAUNCHCTL_DAEMON.md** (troubleshooting section)

### For Architecture Questions
→ **CLOUD_RESEARCH.md** (full reference)

### For Operational Details
→ **INFRASTRUCTURE.md** (automation flows)

---

## ✅ Pre-Launch Checklist

Before running orchestrator, verify:

- [ ] API key stored: `security find-generic-password -s "primeintellect-api" -w`
- [ ] prime CLI works: `prime whoami`
- [ ] L40 GPUs available: `prime availability list | grep L40`
- [ ] Environment variables set: `echo $PRIME_INTELLECT_API_KEY`
- [ ] agenthub accessible: `ah leaves`
- [ ] Repository up-to-date: `git status` (clean)

---

## 🎯 Success Definition

**Phase 1 (Current)**
- ✅ All code deployed
- ✅ Orchestrator working
- ✅ 8 experiments ready
- ✅ Documentation complete

**Phase 1 Success**
- 4 pods launch without manual intervention
- 8 experiments complete in 6-8 hours
- Results stream into WandB and leaderboard.jsonl
- zELO shows improvement over baselines

---

## 📝 Document Version History

| Date | Document | Status |
|------|----------|--------|
| 2026-03-11 | All docs | ✅ Complete |
| 2026-03-11 | Implementation | ✅ Complete |
| 2026-03-11 | Infrastructure | ✅ Complete |
| 2026-03-11 | LaunchCtl | ✅ Complete |

---

**Last Updated**: March 11, 2026
**Status**: ✅ Ready to Launch
**Next Step**: Read READY_TO_LAUNCH.md and launch!
