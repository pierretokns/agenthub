# Prime Lab Experiments Status

## Overview

Three baseline embedding models are now training on Prime Lab (free tier) using custom-built OpenEnv environments for BRIGHT, FollowIR, and MIRACL benchmarks.

---

## Custom Environments

All three environments are published to the Prime environment hub and available for use:

### pierretokns/bright-retrieval
- **BRIGHT Benchmark**: BigIR (Binary Relevance Information Gain Task)
- **Status**: ✅ Published & Running
- **Environment Hub**: https://app.primeintellect.ai/dashboard/environments/pierretokns/bright-retrieval
- **Data**: Loads from HuggingFace `google-research-datasets/BRIGHT` (with fallback synthetic examples)

### pierretokns/followir-retrieval
- **FollowIR Benchmark**: Instruction-following retrieval with constraints
- **Status**: ✅ Published & Running
- **Environment Hub**: https://app.primeintellect.ai/dashboard/environments/pierretokns/followir-retrieval
- **Data**: Loads from HuggingFace `jxmo/followir` (with fallback synthetic examples)

### pierretokns/miracl-retrieval
- **MIRACL Benchmark**: Multilingual cross-lingual information retrieval
- **Status**: ✅ Published & Queued
- **Environment Hub**: https://app.primeintellect.ai/dashboard/environments/pierretokns/miracl-retrieval
- **Data**: Loads from HuggingFace `miracl/miracl` (with fallback synthetic examples)

---

## Training Runs (Free Tier: 2 Concurrent Maximum)

### Run 1: BRIGHT Baseline
- **Run ID**: `wg6mko1s5l1fok3ij57l3h96`
- **Model**: PrimeIntellect/Qwen3-0.6B-Reverse-Text-SFT
- **Status**: PENDING → RUNNING
- **Max Steps**: 10,000
- **Config**:
  - Batch size: 512
  - Rollouts per example: 8
  - Learning rate: 2e-5
  - LoRA alpha: 16
- **Eval interval**: 1000 steps
- **Dashboard**: https://app.primeintellect.ai/dashboard/training/wg6mko1s5l1fok3ij57l3h96
- **Logs**: `prime rl logs wg6mko1s5l1fok3ij57l3h96 -f`

### Run 2: FollowIR Baseline
- **Run ID**: `b1k2g2sxenp3jyrxsbylj06b`
- **Model**: PrimeIntellect/Qwen3-0.6B-Reverse-Text-SFT
- **Status**: PENDING → RUNNING
- **Max Steps**: 10,000
- **Config**: (same as BRIGHT)
- **Eval interval**: 1000 steps
- **Dashboard**: https://app.primeintellect.ai/dashboard/training/b1k2g2sxenp3jyrxsbylj06b
- **Logs**: `prime rl logs b1k2g2sxenp3jyrxsbylj06b -f`

### Run 3: MIRACL Baseline (Queued)
- **Status**: QUEUED (waiting for concurrent run slot)
- **Trigger**: Will auto-launch when BRIGHT or FollowIR completes
- **Auto-launcher**: `monitor_and_launch.sh` (running in background)

---

## Monitoring

### Real-time Status
```bash
# List all runs
prime rl list

# Check BRIGHT progress
prime rl progress wg6mko1s5l1fok3ij57l3h96

# Check FollowIR progress
prime rl progress b1k2g2sxenp3jyrxsbylj06b

# View BRIGHT logs (follow mode)
prime rl logs wg6mko1s5l1fok3ij57l3h96 -f

# View FollowIR logs
prime rl logs b1k2g2sxenp3jyrxsbylj06b -f
```

### Background Monitor
```bash
# Status of auto-launcher
tail -f monitor.log

# Will output when MIRACL launches
```

---

## Architecture

Each environment:
1. **Implements OpenEnv interface** (verified by Prime CLI check ✓)
2. **Loads actual HF datasets** (BRIGHT, FollowIR, MIRACL)
3. **Falls back to synthetic data** if HF unavailable (prevents init failures)
4. **Supports train/test splits** via `args = { split = "train" }` in config
5. **Renders prompts** for the language model to generate embeddings

### Training Flow
1. Prime RL samples examples from the environment
2. Model generates embeddings via `Qwen3-0.6B`
3. LoRA adapters optimize embeddings for the task
4. Evaluation runs every 1000 steps on test split
5. Results saved to Prime dashboard

---

## Key Differences from Original Plan

**Original**: Tried to use non-existent pre-built `primeintellect/bright-retrieval` environments
- ❌ Failed: These don't exist on Prime Lab

**New**: Created custom environments from scratch
- ✅ `pierretokns/bright-retrieval` (and followir/miracl variants)
- ✅ Published to Prime environment hub
- ✅ All configs updated to use new environments
- ✅ Experiments now launching successfully

---

## Expected Timeline

### Phase 1: Baseline Runs (Now)
- **BRIGHT**: 10k steps ~4-6 hours on L40S GPU
- **FollowIR**: 10k steps ~4-6 hours
- **MIRACL**: 10k steps ~4-6 hours
- **Total**: ~12-18 hours (parallel, respecting 2-run limit)
- **Estimated completion**: Mar 12, 2026, 14:00-20:00 UTC

### Phase 2: Checkpoint Download
- Download final checkpoints from Prime Lab
- Extract nDCG@10 scores from eval metrics
- Compare to local MLX baselines (38.44 score)

### Phase 3: Next Iterations
- **Curriculum learning** (hard examples first)
- **zELO experiments** (oracle-guided reward models)
- **Multi-task training** (BRIGHT + FollowIR + MIRACL together)

---

## Files & References

**Environments** (all committed to git):
- `/agenthub/environments/bright_retrieval/`
- `/agenthub/environments/followir_retrieval/`
- `/agenthub/environments/miracl_retrieval/`

**Configs** (all committed to git):
- `/agenthub/configs/bright_baseline.toml`
- `/agenthub/configs/followir_baseline.toml`
- `/agenthub/configs/miracl_baseline.toml`

**Monitoring**:
- `/agenthub/monitor_and_launch.sh` — Auto-launches MIRACL when slot opens
- `/agenthub/monitor.log` — Log of monitoring script

---

## Troubleshooting

### "Environment not found" error
- → Ensure environment is published: `prime env list | grep pierretokns`
- → Check for typos in config IDs (should be lowercase, hyphenated)

### "Reached concurrent training run limit"
- → Free tier allows 2 concurrent runs
- → Monitor existing runs: `prime rl list`
- → Auto-launcher (`monitor_and_launch.sh`) will queue next run

### Logs not available immediately
- → Prime RL queues logs asynchronously
- → Wait ~30-60s after run starts, then: `prime rl logs <run-id>`

### Environment still "in progress"
- → Environment is being validated by Prime
- → First-time environments take ~2-5 minutes to validate
- → Training will start once validation completes

---

## Next Steps

1. **Monitor training** (30-45 min check intervals):
   ```bash
   prime rl list
   prime rl metrics wg6mko1s5l1fok3ij57l3h96
   ```

2. **When first run completes**:
   - MIRACL auto-launches via `monitor_and_launch.sh`
   - Check: `tail -f monitor.log`

3. **After all runs complete**:
   - Download checkpoints: `prime rl checkpoints <run-id>`
   - Extract nDCG@10 scores from eval metrics
   - Compare to MLX baseline (38.44)
   - Plan Phase 2 experiments

---

## Success Criteria

- ✅ Environments created and published
- ✅ BRIGHT and FollowIR running
- ⏳ MIRACL queued and auto-launching
- ⏳ Completion: All three runs finish with valid nDCG@10 scores
- ⏳ Comparison: Scores available vs local MLX baseline

