# PrimeIntellect Cloud Platform Reference

Comprehensive guide for working with PrimeIntellect GPU cloud for autonomous embedding research.

## Quick Start

### 1. API Authentication
```bash
# Store API key in Keychain
security add-generic-password -s "primeintellect-api" -a "pierre" -w "pit_32209..."

# Configure prime CLI
prime config set-api-key "$(security find-generic-password -s primeintellect-api -w)"

# Verify
prime availability list
```

### 2. Create Persistent Disk
```bash
# Create 500GB disk for embedding data
prime disks create --name embed-data --size 500 --cloud-id gpu_1x_l40s

# Note the disk ID returned, update orchestrator_config.yaml:
# disk_id: "<disk-id>"
```

### 3. Populate Disk
```bash
# Launch cheap setup pod with disk attached, run populate_disk.py
python3 autoresearch-cloud/scripts/populate_disk.py

# Verifies on local machine:
# - /mnt/embed-data/data/*.jsonl exist (training data)
# - /mnt/embed-data/hf_cache/ contains cached model
# - /mnt/embed-data/contamination_report.json exists
```

### 4. Launch Training Pods
```bash
# Start orchestrator (assigns experiments to pods)
python3 agenthub/scripts/orchestrator.py

# Monitors:
# - Pod launch and status
# - Job assignment via embed-jobs channel
# - Results collection via embed-results channel
# - Pod cleanup on completion
```

---

## Python SDK Usage

### Import and Initialize
```python
from prime_cli.core import APIClient
from prime_cli.api.pods import PodsClient
from prime_cli.api.disks import DisksClient
import os

api_key = os.environ["PRIME_INTELLECT_API_KEY"]
client = APIClient(api_key=api_key)
pods_client = PodsClient(client)
disks_client = DisksClient(client)
```

### Pod Creation Payload

```python
pod_payload = {
    "pod": {
        "name": "researcher-node-1",
        "cloudId": "gpu_1x_l40s",           # massedcompute US L40S
        "gpuType": "L40S 48GB",             # Exact GPU type
        "socket": "PCIe",
        "gpuCount": 1,
        "diskSize": 200,                     # Ephemeral OS disk (GB)
        "vcpus": 14,                         # CPU cores
        "memory": 128,                       # Memory (GB)
        "image": "cuda_12_4_pytorch_2_5",   # Correct PrimeIntellect image name
        "dataCenterId": None,                # Let Prime pick optimal location
        "autoRestart": False,
        "envVars": [                         # Must be array of {key, value}
            {"key": "NODE_ID", "value": "node-1"},
            {"key": "AGENTHUB_ADDR", "value": "http://cloud.example.com:8000"},
            {"key": "EMBED_DATA_DIR", "value": "/mnt/embed-data"},
            {"key": "HF_DATASETS_CACHE", "value": "/mnt/embed-data/hf_cache"},
            {"key": "TRANSFORMERS_CACHE", "value": "/mnt/embed-data/hf_cache"},
        ],
    },
    "provider": {"type": "massedcompute"},  # Must match disk provider
    "disks": ["disk-id-here"],               # Flat array of disk IDs
    "team": None,
}

# Launch pod
result = pods_client.create(pod_payload)
pod_id = result["id"]  # Real pod ID from API
```

### Pod Status and Cleanup
```python
# Get pod status
status = pods_client.get(pod_id)
print(status["status"])  # "pending", "running", "succeeded", "failed"

# Terminate pod
pods_client.delete(pod_id)
```

### Disk Management
```python
# Create disk
disk_payload = {
    "name": "embed-data",
    "size": 500,
    "cloud_id": "gpu_1x_l40s",
    "provider": "massedcompute",
}
disk_result = disks_client.create(disk_payload)
disk_id = disk_result["id"]

# List disks
disks = disks_client.list()
for disk in disks:
    print(f"{disk['name']}: {disk['size']}GB, status={disk['status']}")

# Delete disk (only if unused)
disks_client.delete(disk_id)
```

---

## Available Cloud Resources

### GPU Tiers
| Cloud ID | GPU | VRAM | Free Tier | Price |
|----------|-----|------|-----------|-------|
| `gpu_1x_l40s` | L40S | 48GB | 4x parallel | $0.60/hr |
| `gpu_1x_h100` | H100 | 80GB | 2x parallel | $1.98/hr |
| `gpu_1x_a100` | A100 | 80GB | Limited | $1.45/hr |

**Recommended for embedding research**: L40S (48GB) — sufficient for batch size 512, excellent cost/performance.

### Image Names
- `cuda_12_4_pytorch_2_5` — PyTorch 2.5 + CUDA 12.4 (recommended)
- `cuda_11_8_pytorch_2_1` — PyTorch 2.1 + CUDA 11.8 (older)

### Environment Variables
Required in all training pods:
- `NODE_ID` — unique node identifier (e.g., "node-1")
- `AGENTHUB_ADDR` — coordinator address (must be reachable from pod, **NOT localhost**)
- `AGENTHUB_API_KEY` — auth token for coordinator
- `EMBED_DATA_DIR` — path to persistent disk (default: `/mnt/embed-data`)
- `HF_DATASETS_CACHE` — HuggingFace datasets cache directory
- `TRANSFORMERS_CACHE` — HuggingFace models cache directory
- `WANDB_API_KEY` — Weights & Biases API key (optional)
- `HF_TOKEN` — HuggingFace token for private models (optional)

---

## Contamination Prevention

### Pattern: Build Hash Sets from MTEB Eval
```python
import hashlib

def hash_pair(query: str, document: str) -> str:
    """SHA256 hash of (query, document) pair."""
    pair_text = f"{query.lower().strip()}|{document.lower().strip()}"
    return hashlib.sha256(pair_text.encode()).hexdigest()

# Download MTEB eval queries
eval_hashes = set()
for task in ["BRIGHT", "FollowIR", "MTEB-Code", "MIRACL"]:
    # Load task eval data from MTEB
    for query, document in eval_pairs:
        eval_hashes.add(hash_pair(query, document))

# Filter training data
clean_pairs = []
for pair in train_pairs:
    if hash_pair(pair["query"], pair["positive"]) not in eval_hashes:
        clean_pairs.append(pair)
```

### Implementation in `populate_disk.py`
- Runs once on setup pod with persistent disk mounted
- Downloads all MTEB eval queries/docs
- Builds contamination hash set
- Filters training JSONL files in-place
- Saves `contamination_report.json` with per-dataset drop counts
- Idempotent — safe to re-run

---

## Persistent Disk Workflow

### Lifecycle
1. **Create disk**: `prime disks create --name embed-data --size 500 --cloud-id gpu_1x_l40s`
   - Disk is created empty, persists across pod terminations
   - Shared read-only by all pods in same provider/location

2. **Populate disk**: Launch cheap setup pod with disk attached, run `populate_disk.py`
   - Downloads datasets from HF Hub + Kaggle
   - Builds contamination hashes, filters training data
   - Caches model weights
   - Saves to `/mnt/embed-data/` (mount point discovered from prime API)

3. **Attach to training pods**: All experiment pods include `"disks": ["disk-id"]` in payload
   - Disk automatically mounted at `/mnt/embed-data/`
   - Data instantly available — zero download time per experiment
   - Multiple pods can read disk simultaneously

4. **Cleanup**: Delete disk only after all pods complete
   - `prime disks delete <disk-id>`

### Mount Path Discovery
Prime API mount point is `/mnt/embed-data/` by default for `gpu_1x_l40s` provider.
Verify in pod logs:
```bash
# Inside pod:
ls -la /mnt/embed-data/
  → should show: data/ hf_cache/ contamination_report.json
```

---

## Training Pipeline Integration

### experiment.py Flow
1. Polls `embed-jobs` channel for experiment assignment
2. Config specifies `train_data` and `eval_data` paths (relative filenames)
3. `experiment.py` resolves paths:
   ```python
   train_data_full = f"{EMBED_DATA_DIR}/data/{config['train_data']}"
   ```
4. Calls `train(config)` with resolved paths
5. Posts result to `embed-results` channel with `nDCG@10` scores

### Config Keys
```python
{
    "name": "baseline-bright-l40",
    "model_name": "answerdotai/ModernBERT-base",
    "train_data": "bright_train.jsonl",          # Filename only (resolved relative to EMBED_DATA_DIR)
    "eval_data": "bright_eval.jsonl",
    "batch_size": 512,
    "epochs_warmup": 1,
    "epochs_contrastive": 2,
    "epochs_finetune": 1,
    "use_elo": true,                             # Enable zELO oracle loss
    "eval_dataset": "BRIGHT",                    # MTEB task for final evaluation
    "mixed_precision": "bf16",                   # Enable bfloat16
}
```

---

## Pod Status Polling

### Status Values
- `"pending"` — pod launching, waiting for resources
- `"running"` — pod is active, script executing
- `"succeeded"` — training completed, exit code 0
- `"failed"` — training failed, exit code != 0
- `"timeout"` — exceeded timeout_minutes, pod killed

### Polling Pattern
```python
import time

def wait_for_pod_completion(pods_client, pod_id, timeout_sec=7200):
    """Poll pod status with timeout."""
    start_time = time.time()
    while time.time() - start_time < timeout_sec:
        status = pods_client.get(pod_id)
        state = status["status"]

        if state == "running":
            print(f"Pod {pod_id} still running...")
            time.sleep(30)
        elif state == "succeeded":
            print(f"Pod {pod_id} completed successfully")
            return True
        elif state == "failed":
            print(f"Pod {pod_id} failed: {status.get('error', 'unknown')}")
            return False
        else:
            time.sleep(10)

    print(f"Pod {pod_id} timeout")
    return False
```

---

## Known Gotchas & Debugging

### 1. Pod Can't Reach Coordinator
**Symptom**: `connection refused` / `timeout` in pod logs when polling `embed-jobs`

**Cause**: `AGENTHUB_ADDR` is `localhost` or `127.0.0.1` — pods on cloud can't reach local machine

**Fix**: Use publicly reachable address:
```python
agenthub_addr = os.getenv("AGENTHUB_ADDR")
if "localhost" in agenthub_addr:
    raise ValueError(f"AGENTHUB_ADDR must be reachable from cloud: {agenthub_addr}")
```

### 2. Data Not Found on Pod
**Symptom**: `FileNotFoundError: data/bright_train.jsonl` in pod logs

**Cause**: Persistent disk not attached, or incorrect mount path

**Fix**:
- Verify `disk_id` in `orchestrator_config.yaml` is not "FILL_IN_AFTER_DISK_CREATE"
- Verify `"disks": [disk_id]` is in pod payload (not inside `"pod"` dict — top-level)
- Check pod env vars include `EMBED_DATA_DIR=/mnt/embed-data`

### 3. GPU Memory Exhausted
**Symptom**: `RuntimeError: CUDA out of memory` mid-training

**Cause**: Batch size too large for GPU, or model doesn't fit in memory

**Fix**:
- L40S (48GB): reduce batch size from 512 to 256
- H100 (80GB): can handle batch 1024
- Enable gradient checkpointing: `model.gradient_checkpointing_enable()`
- Enable bf16: `config["mixed_precision"] = "bf16"`

### 4. Secrets Leaking in Logs
**Symptom**: API keys visible in pod stdout/stderr

**Cause**: Printing env vars or config dicts without filtering

**Fix**: Never log `PRIME_INTELLECT_API_KEY`, `AGENTHUB_API_KEY`, `HF_TOKEN`, `WANDB_API_KEY`

### 5. Disk Mount Path Wrong
**Symptom**: Pod sees `/mnt/disk-...` instead of `/mnt/embed-data/`

**Cause**: Prime API auto-assigns mount point based on disk provider/location

**Fix**: Pod must discover mount point from Prime API at startup:
```python
# Inside pod:
disks = pods_client.get_disks()  # Get mounted disks for this pod
mount_point = disks[0]["mount_path"]  # Use actual path, not hardcoded
os.environ["EMBED_DATA_DIR"] = mount_point
```

---

## Secrets Management

### 1. Store in Keychain (Local Machine)
```bash
security add-generic-password -s "primeintellect-api" -a "pierre" -w "pit_..."
security add-generic-password -s "wandb-api" -a "pierre" -w "wandb_..."
security add-generic-password -s "hf-token" -a "pierre" -w "hf_..."

# Retrieve:
security find-generic-password -s "primeintellect-api" -w
```

### 2. Store in GitHub Secrets (Repo: pierretokns/agenthub)
```bash
gh secret set PRIME_INTELLECT_API_KEY --body "pit_..."
gh secret set WANDB_API_KEY --body "wandb_..."
gh secret set HF_TOKEN --body "hf_..."
```

### 3. Pass to Pods
Environment variables are **injected plaintext** at pod creation:
```python
"envVars": [
    {"key": "WANDB_API_KEY", "value": os.getenv("WANDB_API_KEY")},
    {"key": "HF_TOKEN", "value": os.getenv("HF_TOKEN")},
]
```

Do NOT use `prime secret` for user API keys — it's for cloud-managed service accounts only.

---

## Result Format

### embed-results Channel Message
```json
{
    "timestamp": "2026-03-11T16:35:00Z",
    "node": "node-1",
    "name": "baseline-bright-l40",
    "model": "answerdotai/ModernBERT-base",
    "batch_size": 512,
    "final_model_path": "checkpoints/baseline-bright-l40_final.pt",
    "wandb_run_id": "abc123def",
    "eval_tasks": "BRIGHT",
    "nDCG@10": 0.42,
    "status": "success"
}
```

### Key Fields
- `nDCG@10` — MTEB benchmark score (higher = better)
- `eval_tasks` — which MTEB task was evaluated
- `final_model_path` — path to saved model weights (on persistent disk)
- `wandb_run_id` — link to WandB dashboard for detailed metrics

---

## Orchestrator Config Example

```yaml
# orchestrator_config.yaml
disk_id: "disk-12345-abcde"  # Created via: prime disks create ...

max_pods: 4  # Free tier limit
timeout_minutes: 90

experiment_queue:
  - name: "baseline-bright-l40"
    config:
      name: "baseline-bright-l40"
      model_name: "answerdotai/ModernBERT-base"
      train_data: "bright_train.jsonl"          # Filename only
      eval_data: "bright_eval.jsonl"
      batch_size: 512
      epochs_warmup: 1
      epochs_contrastive: 2
      epochs_finetune: 1
      use_elo: false
      eval_dataset: "BRIGHT"
      mixed_precision: null

  - name: "zelo-bright-oracle"
    config:
      name: "zelo-bright-oracle"
      model_name: "answerdotai/ModernBERT-base"
      train_data: "bright_train_oracle.jsonl"
      eval_data: "bright_eval.jsonl"
      batch_size: 512
      epochs_warmup: 1
      epochs_contrastive: 2
      epochs_finetune: 1
      use_elo: true
      elo_weight: 0.5
      eval_dataset: "BRIGHT"
      mixed_precision: "bf16"
```

---

## Useful Commands

### CLI
```bash
# List available cloud resources
prime availability list

# List all pods
prime pods list

# Get single pod status
prime pods get <pod-id>

# Delete pod
prime pods delete <pod-id>

# List disks
prime disks list

# Get disk info
prime disks get <disk-id>

# Delete disk
prime disks delete <disk-id>

# View pod logs (if available)
prime pods logs <pod-id>
```

### Local Testing
```bash
# Test setup_node.py locally (will fail on GPU check, but OK)
EMBED_DATA_DIR=/tmp/test-data NODE_ID=local python3 autoresearch-cloud/scripts/setup_node.py

# Test populate_disk.py locally
EMBED_DATA_DIR=/tmp/embed-data python3 autoresearch-cloud/scripts/populate_disk.py

# Test orchestrator config loading
python3 -c "
import yaml
with open('orchestrator_config.yaml') as f:
    cfg = yaml.safe_load(f)
    print(f'Max pods: {cfg[\"max_pods\"]}')
    print(f'Disk ID: {cfg[\"disk_id\"]}')
    print(f'Experiments: {len(cfg[\"experiment_queue\"])}')
"
```

---

## References

- PrimeIntellect API Docs: https://api.primeintellect.ai/docs
- prime_cli GitHub: https://github.com/primeintellect/prime_cli
- MTEB Benchmark: https://github.com/embeddings-benchmark/mteb
- ModernBERT: https://huggingface.co/answerdotai/ModernBERT-base
