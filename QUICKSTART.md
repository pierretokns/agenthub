# Cloud Research Quick Start (5-Minute Setup)

**TL;DR**: Store API key → configure environment → launch orchestrator → watch experiments run on H100s.

---

## Step 1: Store API Key (1 min)

```bash
# Get your PrimeIntellect API key from https://primeintellect.ai/console
# (format: pit_XXXXX...)

security add-generic-password -s "primeintellect-api" -a "pierre" -w "pit_YOUR_KEY_HERE"

# Verify
security find-generic-password -s "primeintellect-api" -w
# Should print: pit_XXXXX...
```

---

## Step 2: Set Environment (1 min)

Add to your `.zshrc` or `.bashrc`:

```bash
export PRIME_INTELLECT_API_KEY="$(security find-generic-password -s primeintellect-api -w)"
export WANDB_API_KEY="your-wandb-api-key"
export HF_TOKEN="your-hf-token"
export AGENTHUB_API_KEY="your-agenthub-key"
export AGENTHUB_ADDR="http://localhost:8000"
```

Then reload:
```bash
source ~/.zshrc
```

---

## Step 3: Verify Setup (1 min)

```bash
prime whoami
# Output: {"account_id": "...", "email": "..."}

ah leaves
# Output: empty (ok if no experiments yet)
```

---

## Step 4: Launch Orchestrator (1 min)

```bash
cd /Users/pierre/gourmand/agenthub

python scripts/orchestrator.py
# Starts launching pods...
# Assigns experiments...
# Waits for results...
# Aggregates leaderboard...
```

**Leave running.** It will:
1. Launch up to 3 H100 pods
2. Assign experiments from `orchestrator_config.yaml`
3. Monitor results in real-time
4. Terminate pods when done
5. Write `leaderboard.jsonl` with all results

---

## Step 5: Monitor (While Running)

### In another terminal:

```bash
# Check active pods
prime pods list

# See results streaming in
ah read embed-results | jq -r '.name, .nDCG@10'

# Watch WandB
open https://wandb.ai/pierretokns/autoresearch-embed

# View logs of a specific pod
prime pods logs <pod-id> --follow
```

---

## What's Running?

Each H100 pod is executing:

1. **Warmup Stage** — InfoNCE loss, 1 epoch
2. **Contrastive Stage** — hard negative mining, 2 epochs
3. **Fine-tune Stage** — optional EloDistillationLoss, 1 epoch
4. **Evaluation** — MTEB benchmark (BRIGHT, FollowIR, Code, MIRACL)
5. **Results** → WandB + embed-results channel + git DAG

Total per experiment: ~2 hours on H100 80GB

---

## Expected Output

### In Console:
```
[INFO] Launching pod: researcher-node-1
[INFO] Launching pod: researcher-node-2
[INFO] Launching pod: researcher-node-3
[INFO] Posted job for node-1
[INFO] New result: baseline-bright-h100 from node-1
[INFO] Pod researcher-node-1 completed, terminating
...
```

### In WandB Dashboard:
- New runs appear every 2-5 minutes
- Watch nDCG@10 climb in real-time
- Compare against baselines

### In leaderboard.jsonl:
```json
{"timestamp": "2026-03-11T12:00:00Z", "node": "node-1", "name": "baseline-bright-h100", "nDCG@10": 21.5}
{"timestamp": "2026-03-11T14:30:00Z", "node": "node-2", "name": "zelo-bright-oracle", "nDCG@10": 32.8}
```

---

## Troubleshooting

### "prime: command not found"
```bash
uv tool install prime
```

### "API key not found"
```bash
security find-generic-password -s primeintellect-api -w
# If error, re-add:
security add-generic-password -s "primeintellect-api" -a "pierre" -w "pit_YOUR_KEY"
```

### "No pods launching"
```bash
prime availability list --gpu-type H100_80GB
# If H100 unavailable, try:
# - Edit orchestrator_config.yaml: gpu_type: "A100_80GB"
# - Or wait for quota to reset
```

### "Results not appearing"
```bash
# Check pod logs
prime pods logs <pod-id> | grep -i error

# Check agenthub channel
ah read embed-jobs
ah read embed-results
```

---

## Stopping Experiments

```bash
# Graceful shutdown (wait for pods to finish)
Ctrl+C

# Force shutdown (terminate all pods)
prime pods list --format json | jq -r '.[] | .id' | xargs -I {} prime pods delete {}
```

---

## What's Next?

Once experiments are running:

1. **Monitor WandB** — https://wandb.ai/pierretokns/autoresearch-embed
2. **Check leaderboard** — `cat leaderboard.jsonl | jq .`
3. **Phase 2** — Prepare oracle training data for zELO variants
4. **Phase 3** — Scale to 5-10 pods for hyperparameter sweep

---

## Key Files

- `orchestrator_config.yaml` — edit to add/remove experiments
- `CLOUD_RESEARCH.md` — full architecture docs
- `SETUP_CHECKLIST.md` — detailed setup guide
- `scripts/orchestrator.py` — orchestrator source code

---

## For Help

- **Architecture questions** → Read `CLOUD_RESEARCH.md`
- **Setup issues** → Check `SETUP_CHECKLIST.md` troubleshooting section
- **Pod logs** → `prime pods logs <id>`
- **WandB logs** → https://wandb.ai/pierretokns/autoresearch-embed
