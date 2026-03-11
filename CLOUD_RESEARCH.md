# Cloud Research Implementation — Multi-Node PrimeIntellect Coordination

## Status: ✅ Implementation Complete (Part 0-4)

This document summarizes the implementation of autonomous cloud researchers on PrimeIntellect, coordinated by agenthub.

---

## Architecture Overview

```
Local (M2 Ultra)
├── agenthub/              (coordinator, passive pull-based)
│   ├── scripts/orchestrator.py       (pod launcher, job assigner, result aggregator)
│   ├── orchestrator_config.yaml      (experiment queue)
│   └── leaderboard.jsonl             (unified results from all nodes)
│
├── autoresearch-embed/    (MLX local experiments — UNTOUCHED)
│
└── autoresearch-cloud/    (NEW: PyTorch/CUDA submodule)
    ├── program.md
    ├── scripts/
    │   ├── experiment.py        (cloud loop: poll jobs → train → post results)
    │   ├── setup_node.py        (pod initialization)
    │   └── supervisor.sh        (restart handler)
    ├── src/
    │   ├── train_cuda.py        (4-stage PyTorch pipeline)
    │   ├── model_cuda.py        (ModernBERT bi-encoder)
    │   ├── losses_cuda.py       (InfoNCE + EloDistillationLoss)
    │   └── data_cuda.py         (JSONL dataset loader)
    └── configs/
        └── training_stages_cuda.yaml  (H100-tuned hyperparameters)

Cloud (H100 pods on PrimeIntellect)
├── node-1, node-2, node-3...
│   └── runs autoresearch-cloud/scripts/supervisor.sh
│       └── calls experiment.py in infinite loop
│           ├── polls ah read embed-jobs for assignment
│           ├── executes train_cuda.train()
│           ├── posts result to embed-results channel
│           └── commits to git DAG
```

---

## Components

### 1. **autoresearch-cloud/** (Cloud Training Codebase)

**model_cuda.py**
- `BiEncoder`: HuggingFace ModernBERT wrapper for PyTorch/CUDA
- Mean pooling with attention masking
- `.encode()` method for batch inference

**losses_cuda.py**
- `InfoNCELoss`: Standard contrastive loss with in-batch negatives
- `EloDistillationLoss`: KL-div from LLM-judge scores (NEW for zELO)
- `CombinedLoss`: Mix InfoNCE + Elo with tunable weights

**data_cuda.py**
- `EmbeddingDataset`: Loads JSONL triplets/queries with optional `elo_scores`
- `get_data_loaders()`: Creates train/eval DataLoaders

**train_cuda.py**
- 4-stage pipeline:
  1. **Warmup** (InfoNCE only, 1 epoch)
  2. **Contrastive** (InfoNCE + hard negatives, 2 epochs)
  3. **Fine-tune** (optionally with EloDistillationLoss, 1-2 epochs)
  4. **Cleanup** (old checkpoints)
- Mixed precision (bf16), gradient checkpointing
- Logs to WandB in `autoresearch-embed` project
- Returns result dict compatible with leaderboard

**scripts/experiment.py** (Cloud Loop)
```python
while True:
    job = ah.read('embed-jobs', filter_by_node=NODE_ID)
    if not job: sleep(30); continue
    result = train_cuda.train(job['config'])
    ah.post('embed-results', result)
    git commit -am f"exp: {job['name']}"
    git push
    cleanup_old_checkpoints()
```

**scripts/setup_node.py**
- Called once per pod at startup
- Registers with agenthub (`ah join`)
- Installs PyTorch, transformers, wandb, etc.
- Pre-downloads ModernBERT model
- Exits; supervisor.sh launches experiment.py

**scripts/supervisor.sh**
- Restart handler for context exhaustion
- Runs `setup_node.py` once
- Loops `experiment.py` with retry logic
- Exits cleanly on exit code 0, retries on SIGKILL/SIGTERM

**configs/training_stages_cuda.yaml**
- H100-tuned configs for baseline + zELO experiments
- Batch size 512-1024, bf16, gradient checkpointing
- Baseline BRIGHT, FollowIR, Code Search, MIRACL variants

### 2. **agenthub/scripts/orchestrator.py** (Local Coordinator)

**PrimeIntellectAPI**
```python
pi.launch_pod(pod_config, env_vars)  # POST pod with H100_80GB
pi.get_pod_status(pod_id)
pi.terminate_pod(pod_id)
```

**Orchestrator**
- `run()`: Main loop
  1. Launch pods (up to `max_pods`, e.g., 3)
  2. Assign experiments via `ah post embed-jobs`
  3. Monitor `ah read embed-results` for completion
  4. Terminate idle pods
  5. Aggregate leaderboard from all nodes
- Reads experiment queue from `orchestrator_config.yaml`

**orchestrator_config.yaml**
```yaml
max_pods: 3
experiment_queue:
  - name: "baseline-bright-h100"
    config: {...}
  - name: "zelo-bright-instruction-oracle"
    config: {...}
```

---

## Setup: Next Steps

### Step 0: Store PrimeIntellect API Key (REQUIRED)

```bash
# 1. Get your API key from https://primeintellect.ai/console
# Format: pit_32209a...

# 2. Store in Keychain (macOS)
security add-generic-password -s "primeintellect-api" -a "pierre" -w "pit_32209a..."

# 3. Verify
security find-generic-password -s "primeintellect-api" -w

# 4. Add to GitHub Secrets (for CI/CD later)
gh secret set PRIME_INTELLECT_API_KEY --repo pierretokns/agenthub \
  --body "$(security find-generic-password -s primeintellect-api -w)"
```

### Step 1: Configure Environment

```bash
# Set in shell profile or .env
export PRIME_INTELLECT_API_KEY="pit_32209a..."
export AGENTHUB_API_KEY="<your-agenthub-api-key>"
export AGENTHUB_ADDR="http://localhost:8000"  # or cloud endpoint
export WANDB_API_KEY="<your-wandb-key>"
export HF_TOKEN="<your-hf-token>"
```

### Step 2: Verify prime CLI

```bash
prime --version
prime config set-api-key "$(security find-generic-password -s primeintellect-api -w)"
prime availability list  # Check available GPUs
prime pods status        # List running pods
```

### Step 3: Store API Keys in PrimeIntellect Secrets (For Pod Injection)

```bash
curl -X POST https://api.primeintellect.ai/api/v1/secrets/ \
  -H "Authorization: Bearer $(security find-generic-password -s primeintellect-api -w)" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "WANDB_API_KEY",
    "value": "'$(echo $WANDB_API_KEY)'"
  }'

# Repeat for HF_TOKEN, AGENTHUB_API_KEY
```

### Step 4: Launch Local Orchestrator (Optional Test)

```bash
cd /Users/pierre/gourmand/agenthub
python scripts/orchestrator.py

# Or with custom config
python scripts/orchestrator.py --config scripts/my_config.yaml
```

---

## Experiment Workflow

### Local (MLX)
1. Edit `autoresearch-embed/scripts/experiment.py`
2. Run: `python autoresearch-embed/scripts/experiment.py --config config.yaml`
3. Results logged to `autoresearch-embed/results.jsonl` + WandB
4. **autoresearch-embed code is NEVER touched by cloud nodes**

### Cloud (CUDA)
1. **Orchestrator** posts job to `embed-jobs` channel:
   ```json
   {"node": "node-1", "experiment": "zelo-bright-oracle", "config": {...}}
   ```

2. **Cloud node** (experiment.py) polls and picks up job
   ```bash
   ah read embed-jobs --filter "node:node-1"
   ```

3. **Cloud node** executes training
   ```python
   result = train_cuda.train(config)
   ```

4. **Cloud node** posts result:
   ```bash
   ah post embed-results '{"timestamp": "...", "node": "node-1", "name": "zelo-bright-oracle", ...}'
   ```

5. **Cloud node** commits and pushes:
   ```bash
   git add checkpoints/ results.jsonl leaderboard.jsonl
   git commit -am "exp: zelo-bright-oracle"
   git push origin remote/node-1
   ```

6. **Orchestrator** reads results and aggregates leaderboard:
   ```bash
   ah read embed-results | jq -r '.name, .nDCG@10'
   ```

---

## Key Design Decisions

### 1. **Passive Coordination (No Job Queue)**
- **Why**: Avoids complex orchestration state management
- **How**: Git DAG + message board (channels) as coordination primitives
- **Trade-off**: Cloud nodes must poll rather than receive push notifications

### 2. **Isolation per Node**
- Each node has its own git branch (`remote/node-{id}`)
- Separate `results.jsonl`, `checkpoints/`, `run.log`
- No shared mutable state — safe for parallel execution

### 3. **Unified WandB Project**
- All runs (MLX + Cloud) log to `autoresearch-embed` WandB project
- Single unified dashboard for all experiments
- Cloud nodes inject `WANDB_API_KEY` via PrimeIntellect secrets

### 4. **Same Result Format**
- Cloud `result.json` format matches `autoresearch-embed` version
- `leaderboard.jsonl` is append-only and language-agnostic
- Leaderboard merge is trivial (JSON cat)

### 5. **Context Exhaustion Handling**
- supervisor.sh restarts experiment.py on SIGKILL/SIGTERM
- Max retries prevents infinite loops
- Clean exit (code 0) stops supervisor

---

## Priority Experiments (zELO New Domains)

| Priority | Task | Oracle | Target |
|----------|------|--------|--------|
| 1 | BRIGHT/FollowIR (Instruction Adherence) | Claude/GPT-4 pairwise judge | >30 nDCG@10 |
| 2 | Code Search (Execution) | Python test execution | Beat C2LLM-7B (80.75) |
| 3 | MIRACL (Cross-lingual) | mGTE cross-encoder | +4-6 nDCG@10 on low-resource |

---

## Verification Checklist

- [ ] `security find-generic-password -s primeintellect-api -w` returns key
- [ ] `prime --version` shows installed version
- [ ] `prime availability list` shows H100 availability
- [ ] `export AGENTHUB_API_KEY=...` and test `ah leaves`
- [ ] `cd autoresearch-cloud && git log --oneline` shows commits
- [ ] `cd agenthub && git submodule status` shows autoresearch-cloud
- [ ] `python agenthub/scripts/orchestrator.py` launches without errors (in dry mode)
- [ ] Confirm `autoresearch-embed` is completely untouched

---

## Troubleshooting

### Pod fails to launch
```bash
prime pods status --verbose
# Check: GPU availability, account credits, image pull errors
```

### Cloud node can't reach agenthub
```bash
# Inside pod
curl $AGENTHUB_ADDR/health
# Check: AGENTHUB_ADDR, network policy, firewall
```

### Results not posted
```bash
# Check local agenthub
ah read embed-results | tail -5

# Check pod logs
prime pods logs <pod_id> | tail -50
```

### CUDA OOM
```bash
# Reduce batch_size in orchestrator_config.yaml
batch_size: 512  # or 256
```

### WandB runs not showing
```bash
# Verify WANDB_API_KEY is set in pod environment
# Check: project name is "autoresearch-embed"
# Verify: WANDB_API_KEY was successfully injected via PrimeIntellect secrets API
```

---

## Future: Phase 2 (Beyond Part 4)

- [ ] Dataset curation pipeline for oracle training data
- [ ] Hard negative mining between cloud runs
- [ ] Checkpoint checkpointing + resume from cloud storage
- [ ] Automated pod scaling based on job queue depth
- [ ] Real-time dashboard: orchestrator → leaderboard → wandb sync
