# 🚀 Ready to Launch

**Status**: ✅ **COMPLETE** — All systems ready

Your cloud research infrastructure is fully deployed and automated. You can launch continuous experiments with a single command.

---

## What You Have

### ✅ Cloud Training Codebase (autoresearch-cloud/)
- PyTorch/CUDA 4-stage training pipeline
- InfoNCE + EloDistillationLoss implementations
- H100/L40 GPU compatible (automatic batch sizing)
- Complete experiment loop with WandB logging

### ✅ Local Orchestrator (agenthub/scripts/orchestrator.py)
- Pod lifecycle management
- Job assignment via agenthub message board
- Result aggregation into leaderboard.jsonl
- Free tier optimized (4 L40 pods, 8 experiments)

### ✅ Continuous Operation (launchctl daemon)
- Runs 24/7 automatically
- Auto-restart on boot
- Auto-recovery on crash
- Logs to ~/.local/var/log/agenthub/

### ✅ Comprehensive Documentation
- **DEPLOY_FREE_TIER.md** — 6-8 hour experiment run
- **LAUNCHCTL_DAEMON.md** — Daemon setup and control
- **INFRASTRUCTURE.md** — Behind-the-scenes automation
- **QUICKSTART.md** — 5-minute launcher guide
- **SETUP_CHECKLIST.md** — Detailed setup
- **CLOUD_RESEARCH.md** — Full architecture reference

### ✅ GitHub Issues (Tracking)
- Issue #19: Phase 1 (COMPLETED)
- Issue #20: Phase 2 (Dataset Curation)
- Issue #21: Phase 3 (zELO Experiments)
- Issue #22: Phase 4 (Scaling & Production)
- Issue #23: Anti-Cheat (Train/Test Contamination)
- Issue #24: AgentIR Integration (Reasoning-Aware Retrieval)

---

## Getting Started (3 Steps)

### Step 1: Set Environment

```bash
# Verify API key is stored
security find-generic-password -s "primeintellect-api" -w
# Returns: pit_32209a7bcb2b6dada6ad618d87316ec25ab3a53ebaab2db8c938c341e671fb13

# Add to your shell profile (.zshrc, .bashrc)
export PRIME_INTELLECT_API_KEY="pit_32209a7bcb2b6dada6ad618d87316ec25ab3a53ebaab2db8c938c341e671fb13"
export WANDB_API_KEY="your-wandb-api-key"
export HF_TOKEN="your-hf-token"
export AGENTHUB_API_KEY="your-agenthub-key"
export AGENTHUB_ADDR="http://localhost:8000"

# Reload shell
source ~/.zshrc
```

### Step 2: Install Daemon (Optional but Recommended)

```bash
cd /Users/pierre/gourmand/agenthub
bash scripts/install_launchctl.sh
```

This sets up the orchestrator to run continuously in the background.

### Step 3: Launch

**Option A: Run in foreground (for testing)**
```bash
cd /Users/pierre/gourmand/agenthub
python scripts/orchestrator.py
```

**Option B: Run as daemon (for production)**
```bash
bash scripts/manage_orchestrator.sh start
# Verify: bash scripts/manage_orchestrator.sh status
# Monitor: bash scripts/manage_orchestrator.sh logs
```

---

## What Happens Next

### Launch Sequence (5-10 min)

1. Orchestrator reads `orchestrator_config.yaml` (4 L40 pods, 8 experiments)
2. Launches 4 pods via PrimeIntellect API
3. Each pod runs `supervisor.sh` → `setup_node.py` → `experiment.py`
4. Pods register with agenthub

### Training Phase (60-90 min per experiment)

1. experiment.py polls `embed-jobs` channel
2. Orchestrator posts: `{"node": "node-1", "experiment": "baseline-bright-l40", "config": {...}}`
3. Pod receives job and calls `train_cuda.train(config)`
4. 4-stage pipeline:
   - **Warmup** (1 epoch, InfoNCE)
   - **Contrastive** (2 epochs, hard negatives)
   - **Fine-tune** (1 epoch, optional EloDistillation)
   - **Evaluation** (MTEB benchmark)
5. Results logged to WandB every 50 steps
6. Final result posted to `embed-results` channel
7. Git commit and push

### Completion Phase

1. Orchestrator reads results from `embed-results`
2. Pod auto-terminates (quota freed for next pod)
3. Results merged into `leaderboard.jsonl`
4. Next pod launches automatically

### Timeline for Full Run

- 4 pods × 8 experiments (2 per pod) = 2 rounds
- 90 min per experiment × 2 rounds = ~3 hours per pod
- Running 4 pods in parallel = ~3-4 hours total

**Total estimated time: 6-8 hours for all 8 experiments**

---

## Monitoring in Real-Time

### Terminal 1: Watch Orchestrator Logs

```bash
bash scripts/manage_orchestrator.sh logs
# or
tail -f ~/.local/var/log/agenthub/orchestrator.stderr.log
```

### Terminal 2: Watch Pod Status

```bash
watch -n 10 'prime pods list'
```

### Terminal 3: Watch Results Stream

```bash
watch -n 10 'ah read embed-results | tail -5'
```

### Browser: WandB Dashboard

```
https://wandb.ai/pierretokns/autoresearch-embed
```

Live metrics:
- Training loss curves
- Evaluation nDCG@10 per benchmark
- GPU utilization
- Training time per stage

---

## Expected Results

### Baselines (What Current Model Gets)

| Benchmark | Expected nDCG@10 |
|-----------|------------------|
| BRIGHT | 20-24 |
| FollowIR | 18-22 |
| Code Search | ~79 |
| MIRACL | ~62 |

### zELO Improvements (Oracle Training)

| Benchmark | Expected Improvement |
|-----------|----------------------|
| BRIGHT | +6-10 → 28-33 nDCG@10 |
| FollowIR | +5-7 → 25-28 nDCG@10 |
| Code Search | +2-4 → 81-83 nDCG@10 |
| MIRACL | +4-6 on low-resource |

**Success criteria**: zELO beats commercial SOTA (Elastic, OpenAI, Cohere)

---

## No Manual Intervention Required

Everything is automated:

- ✅ Pods created automatically
- ✅ Jobs assigned automatically
- ✅ Training runs unattended
- ✅ Results collected automatically
- ✅ Leaderboard updated in real-time
- ✅ Pods terminate automatically
- ✅ Daemon restarts on crash
- ✅ Logs rotated automatically
- ✅ Error recovery automatic

You only need to:
1. Start the orchestrator (once)
2. Monitor via WandB dashboard (optional)
3. Check results in `leaderboard.jsonl` (after completion)

---

## Troubleshooting

### Daemon Won't Start

```bash
# Check syntax
plutil -lint ~/Library/LaunchAgents/com.agenthub.cloud-orchestrator.plist

# Check logs
bash scripts/manage_orchestrator.sh logs-error

# Manually verify
python scripts/orchestrator.py --help
```

### Pod Fails to Launch

```bash
# Check GPU availability
prime availability list | grep L40

# Check account quota
prime whoami

# Try manual pod
prime pods create --name test-pod --gpu-type L40 --timeout 30m
```

### Results Not Appearing

```bash
# Check if pods are running
prime pods list

# Check pod logs
prime pods logs <pod-id> | tail -50

# Check agenthub channels
ah read embed-jobs
ah read embed-results

# Check WandB
curl -H "Authorization: Bearer $WANDB_API_KEY" \
  https://api.wandb.ai/graphql \
  -d '{"query": "{ viewer { entity } }"}'
```

---

## Next Steps (After Phase 1)

### Immediate (Post-Launch Analysis)
- [ ] Review baseline results
- [ ] Confirm zELO improvements
- [ ] Identify best-performing experiments
- [ ] Compare vs commercial SOTA

### Phase 2: Dataset Curation (2-4 days)
- [ ] Create oracle-scored training data (BRIGHT, FollowIR)
- [ ] Code execution sandbox for Code Search
- [ ] mGTE cross-encoder for MIRACL
- [ ] Update experiment configs with oracle data

### Phase 3: Extended Experiments (1 day)
- [ ] Run hyperparameter sweep (learning rate, elo_weight)
- [ ] Compare multiple oracle strategies
- [ ] Generate ablation tables
- [ ] Prepare for publication

### Phase 4: Scaling & Production (1 week)
- [ ] Upgrade to paid tier (H100 GPUs)
- [ ] Scale to 16 parallel pods
- [ ] Implement cloud checkpointing
- [ ] Automated dataset updates
- [ ] Production monitoring dashboard

---

## Success Checklist

Before launching, verify:

- [ ] API key stored: `security find-generic-password -s "primeintellect-api" -w`
- [ ] prime CLI works: `prime whoami`
- [ ] L40 GPUs available: `prime availability list | grep L40`
- [ ] agenthub reachable: `ah leaves`
- [ ] Config updated: `cat orchestrator_config.yaml | grep max_pods`
- [ ] Code committed: `git log --oneline | head -5`

---

## Launch Command

```bash
# One-time: Install daemon
cd /Users/pierre/gourmand/agenthub
bash scripts/install_launchctl.sh

# Then: Start and forget
bash scripts/manage_orchestrator.sh start

# Or: Run in foreground for testing
python scripts/orchestrator.py
```

---

## Support & Docs

| Scenario | Document |
|----------|----------|
| Quick start | QUICKSTART.md |
| Detailed setup | SETUP_CHECKLIST.md |
| Free tier optimization | DEPLOY_FREE_TIER.md |
| Daemon management | LAUNCHCTL_DAEMON.md |
| Full architecture | CLOUD_RESEARCH.md |
| Automation details | INFRASTRUCTURE.md |
| Implementation summary | IMPLEMENTATION_SUMMARY.md |

---

## Contact

For questions or issues:
- Check relevant documentation (above)
- Review orchestrator logs: `bash scripts/manage_orchestrator.sh logs-error`
- Check pod logs: `prime pods logs <id>`
- Monitor WandB: https://wandb.ai/pierretokns/autoresearch-embed

---

**Status**: ✅ Ready to launch
**Time to first result**: ~10 minutes (pod startup) + ~90 minutes (training)
**Total estimated time**: 6-8 hours (all 8 experiments, 4 pods in parallel)
**Cost**: $0 (free tier)

Let's go! 🚀
