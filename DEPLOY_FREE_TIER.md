# Deploy Cloud Research — Free Tier (L40 GPUs)

**Your setup**: Free tier account with L40 GPU access
**Max capacity**: 4 parallel pods × 8 experiments = 32 total experiment runs
**Time to completion**: ~6-8 hours (90 min per experiment × 4 pods)
**Cost**: $0 (free tier usage)

---

## 📋 Pre-Flight Checklist

✅ **API Key Stored**
```bash
security find-generic-password -s "primeintellect-api" -w
# Returns: pit_32209a7bcb2b6dada6ad618d87316ec25ab3a53ebaab2db8c938c341e671fb13
```

✅ **prime CLI Authenticated**
```bash
prime whoami
# Returns: Pierre Tokns (pierretokns@gmail.com)
```

✅ **L40 GPUs Available**
```bash
prime availability list | grep L40
# Shows: 1x, 2x, 4x L40 configurations available
```

✅ **Repository Structure**
```bash
cd /Users/pierre/gourmand/agenthub
git submodule status
# autoresearch-cloud should be present and initialized
```

---

## 🚀 Launch (3 Steps)

### Step 1: Set Environment Variables

```bash
# Add these to your shell (e.g., .zshrc)
export PRIME_INTELLECT_API_KEY="pit_32209a7bcb2b6dada6ad618d87316ec25ab3a53ebaab2db8c938c341e671fb13"
export WANDB_API_KEY="your-wandb-api-key"  # From https://wandb.ai/settings/api
export HF_TOKEN="your-hf-token"            # From https://huggingface.co/settings/tokens
export AGENTHUB_API_KEY="your-agenthub-key"
export AGENTHUB_ADDR="http://localhost:8000"

# Verify
echo $PRIME_INTELLECT_API_KEY
```

### Step 2: Verify Orchestrator Config

The config is already optimized for your free tier:

```yaml
# orchestrator_config.yaml
max_pods: 4              # 4 L40 pods in parallel
gpu_type: "L40"          # Free tier available GPU
timeout_minutes: 90      # 90 min per experiment
batch_size: 256-512      # Reduced for 48GB VRAM (vs H100 80GB)
```

This will run **8 experiments sequentially** across **4 pods**:
- 2 baselines (BRIGHT, FollowIR)
- 4 zELO variants (instruction + execution oracles)
- 2 extended zELO (more epochs)

### Step 3: Launch Orchestrator

```bash
cd /Users/pierre/gourmand/agenthub

python scripts/orchestrator.py
```

**Expected output:**
```
[INFO] Orchestrator started
[INFO] Launching pod: researcher-node-1
[INFO] Launching pod: researcher-node-2
[INFO] Launching pod: researcher-node-3
[INFO] Launching pod: researcher-node-4
[INFO] Posted job for node-1
[INFO] Posted job for node-2
[INFO] Posted job for node-3
[INFO] Posted job for node-4
[INFO] New result: baseline-bright-l40 from node-1
...
```

**Leave running.** Total time: ~6-8 hours for all 8 experiments on 4 pods.

---

## 📊 Monitor Experiments

### In Another Terminal:

```bash
# 1. Watch pods launch and train
watch -n 5 'prime pods list | grep researcher'

# 2. Stream live results
watch -n 10 'ah read embed-results | tail -5'

# 3. Check WandB dashboard (every 5 min new runs)
open https://wandb.ai/pierretokns/autoresearch-embed

# 4. View aggregated leaderboard
tail -f leaderboard.jsonl | jq -r '.name, .nDCG@10'
```

### Expected Metrics

**Baseline BRIGHT**: ~20-24 nDCG@10
**Baseline FollowIR**: ~18-22 nDCG@10
**zELO BRIGHT (oracle)**: ~28-33 nDCG@10 (improvement vs baseline)
**zELO FollowIR (oracle)**: ~25-30 nDCG@10 (improvement vs baseline)

---

## 🔍 Troubleshooting

### Pod fails to launch
```bash
# Check current pod limits
prime pods list
# Should show available slots (max 4 for free tier)

# Check GPU availability
prime availability list | grep L40
# If none available, wait or try smaller pod

# Manual pod launch (test)
prime pods create \
  --name test-pod \
  --gpu-type L40 \
  --cpu 14 \
  --memory 128Gi \
  --disk 625Gi \
  --timeout 30m \
  -e NODE_ID=test-node-1 \
  -e WANDB_API_KEY=$WANDB_API_KEY \
  -e HF_TOKEN=$HF_TOKEN \
  --command "sleep 300"
```

### Pod crashes (OOM)
L40 has 48GB VRAM. If OOM:
```yaml
# Reduce batch size in orchestrator_config.yaml
batch_size: 256  # Further reduction if needed
epochs_contrastive: 1  # Reduce iterations
```

### Results not appearing
```bash
# Check if pods are running
prime pods logs <pod-id> | tail -50

# Check agenthub channel
ah read embed-jobs
ah read embed-results

# Verify WandB
curl -H "Authorization: Bearer $WANDB_API_KEY" \
  https://api.wandb.ai/graphql \
  -d '{"query": "{ viewer { entity } }"}'
```

### Orchestrator hangs
```bash
# Ctrl+C to stop
# Manually terminate pods
prime pods list --format json | jq -r '.[] | .id' | xargs -I {} prime pods delete {}

# Restart
python scripts/orchestrator.py
```

---

## 📈 What to Expect

### Phase 1: Pod Startup (5-10 min)
- 4 L40 pods spin up
- Each runs `setup_node.py` (pip install, model download)

### Phase 2: Training (70-80 min per experiment)
- experiment.py polls for job assignment
- 4-stage pipeline executes in parallel
- Results post to WandB every 50 training steps
- Pod logs available via `prime pods logs <id>`

### Phase 3: Results Aggregation (5-10 min)
- Results post to `embed-results` channel
- Orchestrator reads and merges into `leaderboard.jsonl`
- WandB dashboard updates automatically

### Phase 4: Pod Cleanup (5 min)
- Completed pods terminate
- Next batch of 4 pods launch
- Queue shrinks: 8 → 4 → 0

---

## 🎯 Success Criteria

✅ **All 8 experiments complete**
```bash
cat leaderboard.jsonl | jq 'length'
# Should be 8
```

✅ **Results in WandB**
- https://wandb.ai/pierretokns/autoresearch-embed
- 8 new runs visible
- nDCG@10 metrics logged

✅ **Improvement over baseline**
```bash
cat leaderboard.jsonl | jq -s 'sort_by(.nDCG@10) | reverse'
# zELO runs should rank higher than baselines
```

---

## 💡 Next Steps (After Phase 1)

### Phase 2: Oracle Data Preparation
- BRIGHT: LLM-judge scoring for instruction adherence
- FollowIR: MS-MARCO instruction augmentation
- Code Search: Python test execution sandbox
- MIRACL: mGTE cross-encoder validation

### Phase 3: Extended Experiments
- Hyperparameter sweep (learning rate, elo_weight)
- Larger datasets (if free tier quota increases)
- Multi-stage distillation chains

### Phase 4: Scale to Paid Tier (Optional)
- Switch to H100 GPUs (larger batch size, faster training)
- Run 8-16 parallel pods
- Complete hyperparameter sweep in 2-3 hours

---

## 📞 Support

**For orchestrator issues:**
- Check logs: `python scripts/orchestrator.py 2>&1 | tee orchestrator.log`
- Review: `CLOUD_RESEARCH.md` (architecture)

**For pod issues:**
- Pod logs: `prime pods logs <pod-id> --follow`
- Node script: `autoresearch-cloud/scripts/experiment.py`

**For results/metrics:**
- Leaderboard: `leaderboard.jsonl`
- WandB: https://wandb.ai/pierretokns/autoresearch-embed
- Channel: `ah read embed-results`

---

## 🎪 Free Tier Limits & Status

**Your Account:**
- Tier: Free
- Quota: 4 simultaneous pods
- GPU Type: L40 (48GB VRAM each)
- Cost: $0 (free)

**Current Usage:**
- Pods running: 0/4
- Experiments queued: 8
- Estimated time: 6-8 hours
- Estimated cost: $0

**API Key Validity:**
- Token: pit_32209a7bcb2b6dada6ad618d87316ec25ab3a53ebaab2db8c938c341e671fb13
- Status: ✅ Active
- Scope: pods, secrets, inference, instances

---

**Ready to launch?**

```bash
cd /Users/pierre/gourmand/agenthub && python scripts/orchestrator.py
```

Monitor with:
```bash
watch -n 10 'prime pods list && echo "---" && ah read embed-results | tail -3'
```

Watch results stream into WandB:
```
https://wandb.ai/pierretokns/autoresearch-embed
```
