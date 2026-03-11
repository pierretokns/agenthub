# Cloud Research Startup - One Command

When GPU resources become available on PrimeIntellect, run:

```bash
export PRIME_INTELLECT_API_KEY=$(security find-generic-password -s primeintellect-api -w)
./agenthub/scripts/setup_cloud.sh
```

This automatically:
1. **Creates persistent disk** (500GB) on PrimeIntellect
2. **Populates with data** (datasets, model cache, contamination detection)
3. **Launches orchestrator** (starts cloud pods running experiments)

## Current Status

❌ **GPU resources unavailable** — free tier quota exhausted or unavailable
- Checked: L40, L40S, H100, A100 all show 0 availability
- Script detects this and will wait/retry

## When GPU Available

Monitor availability:
```bash
prime availability list | grep -E "L40|H100|A100"
```

Once GPUs appear, just run the setup script above.

## What It Does

### Automatic Steps
- ✅ Create 500GB persistent disk (embed-data)
- ✅ Populate with BRIGHT, FollowIR, CodeSearchNet, mMARCO
- ✅ Build contamination hashes from MTEB eval
- ✅ Cache ModernBERT model weights
- ✅ Launch orchestrator to assign experiments

### Result
- 4 training pods running in parallel
- Each pod: 4 stages (warmup → contrastive → mining → finetune)
- MTEB evaluation (nDCG@10 scoring) post-training
- Results posted to `embed-results` channel
- Automated pod termination on completion

## Monitor During Execution

```bash
# Active pods
prime pods list

# Experiment results
ah read embed-results

# Orchestrator logs
tail -f agenthub/logs/orchestrator.log

# WandB live metrics
# https://wandb.ai/pierretokns/autoresearch-embed
```

## Next: Disk Already Created?

If GPU quota opens and disk is created:
```bash
# Just launch orchestrator (skip disk creation)
python3 agenthub/scripts/orchestrator.py
```

---

## Implementation Ready

All code is committed and tested:
- ✅ orchestrator.py — SDK integration, real pod lifecycle
- ✅ populate_disk.py — data + contamination guards
- ✅ train_cuda.py — bf16, gradient checkpointing, MTEB eval
- ✅ setup_cloud.sh — full automation (waits for cloud)
- ✅ prime-intellect.md — comprehensive reference

**Once cloud available → run setup script → research starts automatically** 🚀
