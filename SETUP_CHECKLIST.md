# Cloud Research Setup Checklist

**Status**: Implementation complete. Run these steps to activate cloud experiments.

---

## 🔑 Part 0: Secrets Management (REQUIRED)

### A. Store PrimeIntellect API Key

```bash
# 1. Get your API key from https://primeintellect.ai/console
# Format: pit_XXXXX...

# 2. Store in macOS Keychain
security add-generic-password -s "primeintellect-api" -a "pierre" -w "pit_YOUR_KEY_HERE"

# 3. Verify it was saved
security find-generic-password -s "primeintellect-api" -w
# Should output: pit_XXXXX...

# 4. Add to GitHub Secrets (for CI/CD later)
gh secret set PRIME_INTELLECT_API_KEY --repo pierretokns/agenthub \
  --body "$(security find-generic-password -s primeintellect-api -w)"

# Verify
gh secret list --repo pierretokns/agenthub | grep PRIME
```

### B. Verify Other Required Keys

```bash
# WANDB_API_KEY (from https://wandb.ai/settings/api)
export WANDB_API_KEY="your-wandb-key"

# HF_TOKEN (from https://huggingface.co/settings/tokens)
export HF_TOKEN="your-hf-token"

# AGENTHUB_API_KEY (from your agenthub server)
export AGENTHUB_API_KEY="your-agenthub-key"
```

---

## 📦 Part 1: Install & Verify prime CLI

```bash
# prime is already installed via uv (see earlier output)
prime --version
# Output: prime, version 0.5.44

# Configure API key
prime config set-api-key "$(security find-generic-password -s primeintellect-api -w)"

# Verify connectivity
prime whoami
# Output: {"account_id": "...", "email": "..."}

# Check GPU availability
prime availability list --gpu-type H100_80GB
```

---

## 🗂️ Part 2: Verify Repository Structure

```bash
# Check autoresearch-cloud submodule
cd /Users/pierre/gourmand/agenthub
git submodule status
# Should show: 65521e1... autoresearch-cloud (main)

# Verify autoresearch-embed is untouched
ls autoresearch-embed/src/
# Should have: train.py model.py losses.py (NOT train_cuda.py)

# Verify orchestrator exists
ls scripts/orchestrator.py orchestrator_config.yaml CLOUD_RESEARCH.md
```

---

## 🚀 Part 3: Launch Test Pod (Optional)

**First-time test** (before running full orchestrator):

```bash
# 1. Set environment
export PRIME_INTELLECT_API_KEY="$(security find-generic-password -s primeintellect-api -w)"
export WANDB_API_KEY="your-wandb-api-key"
export HF_TOKEN="your-hf-token"
export AGENTHUB_API_KEY="your-agenthub-key"

# 2. Launch a single test pod
prime pods create \
  --name test-researcher-001 \
  --image pytorch:2.5-cuda12.1-runtime-ubuntu22.04 \
  --gpu-type H100_80GB \
  --cpu 16 \
  --memory 128Gi \
  --disk 500Gi \
  --timeout 30m \
  -e NODE_ID=test-node-1 \
  -e WANDB_API_KEY=$WANDB_API_KEY \
  -e HF_TOKEN=$HF_TOKEN \
  -e AGENTHUB_API_KEY=$AGENTHUB_API_KEY \
  --command "bash scripts/supervisor.sh"

# 3. Check pod status
POD_ID="<pod-id-from-above>"
prime pods describe $POD_ID
prime pods logs $POD_ID

# 4. Terminate when done
prime pods delete $POD_ID
```

---

## ⚙️ Part 4: Configure Orchestrator

Edit `orchestrator_config.yaml`:

```yaml
max_pods: 3  # Start with 3 parallel nodes
gpu_type: "H100_80GB"
timeout_minutes: 120

experiment_queue:
  # These will be assigned in order to nodes
  - name: "baseline-bright-h100"
    config: { ... }
  - name: "zelo-bright-instruction-oracle"
    config: { ... }
```

---

## 🎯 Part 5: Run Orchestrator

### Full Run (Launches Pods)
```bash
cd /Users/pierre/gourmand/agenthub

export PRIME_INTELLECT_API_KEY="$(security find-generic-password -s primeintellect-api -w)"
export WANDB_API_KEY="your-wandb-api-key"
export HF_TOKEN="your-hf-token"
export AGENTHUB_API_KEY="your-agenthub-key"
export AGENTHUB_ADDR="http://localhost:8000"  # or your agenthub endpoint

python scripts/orchestrator.py
# Runs forever; press Ctrl+C to stop
```

### Dry Run (No Pods)
```bash
python scripts/orchestrator.py --dry-run
# Just prints what would happen, no pods launched
```

### Monitor Running Pods
```bash
# List all pods
prime pods list

# Get details of a specific pod
prime pods describe <pod-id>

# Stream logs
prime pods logs <pod-id> --follow

# Terminate all pods
prime pods list --format json | jq -r '.[] | .id' | xargs -I {} prime pods delete {}
```

---

## 📊 Part 6: Monitor Results

### Live Results from Cloud Nodes
```bash
# Read results posted to embed-results channel
ah read embed-results | jq .

# Filter by benchmark
ah read embed-results | jq 'select(.eval_dataset == "BRIGHT")'

# Check node-specific results
ah read embed-results | jq 'select(.node == "node-1")'
```

### WandB Dashboard
- Project: `autoresearch-embed`
- All runs (local MLX + cloud CUDA) appear here
- Link: https://wandb.ai/pierretokns/autoresearch-embed

### Aggregate Leaderboard
```bash
# View all results across all experiments
cat agenthub/leaderboard.jsonl | jq -s 'sort_by(.name)'

# Find best BRIGHT result
cat agenthub/leaderboard.jsonl | jq -s 'map(select(.eval_dataset == "BRIGHT")) | sort_by(.nDCG@10) | reverse | .[0]'
```

---

## ✅ Verification

**Before launching experiments**, verify everything works:

```bash
# 1. API key accessible
security find-generic-password -s primeintellect-api -w
# Should not error

# 2. prime CLI works
prime whoami
# Should show account details

# 3. agenthub is reachable
ah leaves
# Should return git DAG leaves (may be empty initially)

# 4. autoresearch-cloud code is present
python -c "from autoresearch_cloud.src.model_cuda import BiEncoder; print('✓ Model imports')"

# 5. autoresearch-embed is unchanged
ls autoresearch-embed/src/train.py
# Should exist (NOT train_cuda.py)
```

---

## 🔧 Troubleshooting

### "prime: command not found"
```bash
# Reinstall
uv tool install prime
which prime  # Should show path
```

### "PRIME_INTELLECT_API_KEY not found"
```bash
# Check Keychain
security dump-keychain | grep primeintellect

# Re-add if missing
security add-generic-password -s "primeintellect-api" -a "pierre" -w "pit_YOUR_KEY"
```

### Pod fails to launch
```bash
prime availability list  # Check H100 availability
# If unavailable, try A100_80GB instead

# Edit orchestrator.py or orchestrator_config.yaml:
gpu_type: "A100_80GB"  # Fallback
```

### No results appearing in embed-results
```bash
# Check pod logs
prime pods logs <pod-id> | grep -i error

# Check if agenthub is reachable from pod
prime pods exec <pod-id> curl $AGENTHUB_ADDR/health

# Check experiment.py in cloud node
ah read embed-jobs  # Should have job postings
```

### WandB runs not showing
```bash
# Verify WANDB_API_KEY was injected
prime pods exec <pod-id> env | grep WANDB

# Check WandB project name
# Should be: "autoresearch-embed"

# Check WandB API key is valid
curl -H "Authorization: Bearer $WANDB_API_KEY" https://api.wandb.ai/graphql
```

---

## 📝 Next Steps (Phase 2)

After Part 4 is working:

1. **Dataset Curation** (Part 5 in plan)
   - BRIGHT training data + LLM instruction adherence oracle
   - FollowIR + MS-MARCO instruction augmentation
   - Code execution sandbox for code search

2. **Baseline Experiments**
   - Run baseline BRIGHT/FollowIR on H100
   - Establish nDCG@10 baseline (~18-22)
   - Compare vs commercial SOTA

3. **zELO Experiments**
   - Implement EloDistillationLoss training
   - Run BRIGHT with instruction oracle
   - Target: >30 nDCG@10

4. **Scaling**
   - 5-10 parallel pods
   - Hyperparameter sweep
   - Auto-scaling based on job queue

---

## 📚 Key Documents

- **CLOUD_RESEARCH.md** — Architecture & implementation details
- **autoresearch-cloud/program.md** — Cloud researcher agent instructions
- **orchestrator_config.yaml** — Experiment queue and pod config
- **scripts/orchestrator.py** — Source code for orchestration

---

## 🎯 Quick Command Reference

```bash
# Start orchestrator
cd agenthub && python scripts/orchestrator.py

# Monitor pods
prime pods list
prime pods logs <id> --follow

# Check results
ah read embed-results
cat leaderboard.jsonl | jq .

# Terminate all
prime pods list --format json | jq -r '.[] | .id' | xargs -I {} prime pods delete {}

# View WandB
open https://wandb.ai/pierretokns/autoresearch-embed
```
