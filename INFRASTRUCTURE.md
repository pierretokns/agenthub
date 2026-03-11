# Behind-the-Scenes Infrastructure

**Goal**: Agent focuses 100% on research + coordination. All infrastructure, deployment, monitoring, and operational concerns are automated and transparent.

---

## Architecture Layers

```
┌─────────────────────────────────────────────────────────────┐
│ RESEARCH LAYER                                              │
│ Agent: Experiment design, hypothesis generation             │
│ Code: train_cuda.py, losses_cuda.py (experiment logic)      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ ORCHESTRATION LAYER                                         │
│ Coordinator: Pod lifecycle, job assignment, result agg      │
│ Code: orchestrator.py, experiment.py (job loop)             │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ INFRASTRUCTURE LAYER (Automated, Transparent)               │
│ • launchctl daemon (continuous operation)                   │
│ • Pod management (create, monitor, terminate)               │
│ • Secret injection (environment variables)                  │
│ • Logging aggregation (stdout + stderr)                     │
│ • Result collection (JSONL + WandB)                         │
│ • Git sync (commits, pushes)                                │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ CLOUD LAYER (PrimeIntellect)                                │
│ • H100 / L40 GPU pods                                       │
│ • Persistent storage (disk)                                 │
│ • Network (secure communication)                            │
└─────────────────────────────────────────────────────────────┘
```

---

## Component Responsibility Matrix

### Research Agent (autoresearch-cloud/src/)

**Responsible for**: Experiments, model training, loss functions
**NOT responsible for**: Pod management, logging, git operations

Files:
- `train_cuda.py` — training pipeline (4-stage)
- `model_cuda.py` — embedding model wrapper
- `losses_cuda.py` — loss functions (InfoNCE, EloDistillation)
- `data_cuda.py` — dataset loading

### Orchestrator (agenthub/scripts/)

**Responsible for**: Pod lifecycle, job assignment, result collection
**NOT responsible for**: Actual training (delegates to experiment.py)

Files:
- `orchestrator.py` — main coordinator
  - Launches pods
  - Assigns jobs to nodes
  - Monitors results
  - Aggregates leaderboard

### Cloud Agent (autoresearch-cloud/scripts/)

**Responsible for**: Poll jobs → train → post results → git commit
**NOT responsible for**: Infrastructure, monitoring, logging setup

Files:
- `experiment.py` — infinite loop on pod
  - Polls `embed-jobs` channel
  - Executes training
  - Posts `embed-results`
  - Commits to git
- `setup_node.py` — pod initialization
  - Dependencies installation
  - Model download
  - Agent registration
- `supervisor.sh` — restart handler
  - Context exhaustion recovery

### Infrastructure (agenthub/scripts/)

**Responsible for**: Deployment, monitoring, reliability
**NOT responsible for**: Research logic

Files:
- `install_launchctl.sh` — daemon setup
- `manage_orchestrator.sh` — daemon control
- Plist configuration

---

## Automation Checklist

### ✅ Pod Management (Automated)

- [x] **Creation**: `orchestrator.py` → `prime pods create` with all flags
- [x] **Configuration**: GPU type, CPU, memory, disk passed in pod config
- [x] **Secrets injection**: Environment variables set at creation time
- [x] **Monitoring**: `prime pods status` polled every 30s
- [x] **Logging**: `prime pods logs <id>` collected automatically
- [x] **Termination**: Auto-terminate on experiment completion
- [x] **Cleanup**: Remove old checkpoints on pod

**No manual intervention needed.** Pods are created, monitored, and terminated without user action.

### ✅ Job Assignment (Automated)

- [x] **Queue**: Experiments listed in `orchestrator_config.yaml`
- [x] **Assignment**: `ah post embed-jobs` broadcasts job to available nodes
- [x] **Polling**: Cloud nodes poll `ah read embed-jobs` every 30s
- [x] **Deduplication**: Node ID in job prevents conflicts
- [x] **Retry**: Failed jobs re-assigned automatically

**No manual intervention needed.** Jobs flow from queue → pods → execution.

### ✅ Result Collection (Automated)

- [x] **Experiment output**: Results JSON from `train_cuda.py`
- [x] **WandB logging**: Every 50 steps logged automatically
- [x] **Channel posting**: `ah post embed-results` after completion
- [x] **Leaderboard aggregation**: Orchestrator reads channel and merges JSONL
- [x] **Git commits**: Cloud nodes auto-commit results + checkpoints
- [x] **Cleanup**: Old checkpoints removed automatically

**No manual intervention needed.** Results flow: model → WandB → channel → leaderboard → git.

### ✅ Continuous Operation (Automated)

- [x] **launchctl daemon**: `com.agenthub.cloud-orchestrator` runs 24/7
- [x] **Auto-start on boot**: `RunAtLoad = true`
- [x] **Crash recovery**: Restarts on exit with 60s throttle
- [x] **Log rotation**: Logs written to `~/.local/var/log/agenthub/`
- [x] **Status monitoring**: `launchctl list` shows PID and status
- [x] **Manual control**: Start/stop/restart via `manage_orchestrator.sh`

**No manual intervention needed.** Daemon runs continuously; logs rotate; restarts on failure.

### ✅ Secret Management (Automated)

- [x] **API keys**: Stored in Keychain (secure)
- [x] **Pod injection**: Keys passed as environment variables at pod creation
- [x] **No hardcoding**: Keys never stored in git or configs
- [x] **Rotation**: Can update keys in launchctl plist without changing code

**No manual intervention needed.** Secrets injected automatically at pod startup.

### ✅ Monitoring (Automated)

- [x] **Pod status**: `prime pods list` shows all active pods
- [x] **Experiment progress**: WandB dashboard updates live
- [x] **Results posting**: `ah read embed-results` shows all completions
- [x] **Leaderboard**: `leaderboard.jsonl` updated in real-time
- [x] **Error logs**: Stderr logged to `orchestrator.stderr.log`

**No manual intervention needed.** Monitor via `tail -f logs` or WandB dashboard.

---

## Operational Flows (Automated)

### Flow 1: Pod Launch Sequence

```
orchestrator.py startup
  ↓
Read orchestrator_config.yaml (max_pods=4)
  ↓
For each empty pod slot:
  • Create pod config (GPU=L40, CPU=14, memory=128Gi, disk=625Gi)
  • Inject env vars: PRIME_INTELLECT_API_KEY, WANDB_API_KEY, etc.
  • Call: prime pods create --name researcher-node-N ...
  ↓
prime CLI communicates with PrimeIntellect API
  ↓
Pod allocated on cloud infrastructure
  ↓
Cloud node runs: supervisor.sh → setup_node.py → experiment.py
  ↓
experiment.py starts polling embed-jobs
```

**Total time**: 5-10 minutes (automated)

### Flow 2: Experiment Execution

```
experiment.py polling
  ↓
orchestrator.py: ah post embed-jobs '{"node": "node-1", "config": {...}}'
  ↓
experiment.py receives job (poll-based)
  ↓
Call: train_cuda.train(config)
  ↓
4-stage pipeline:
  • Warmup (InfoNCE)
  • Contrastive (hard negatives)
  • Fine-tune (optional EloDistillation)
  • Evaluation (MTEB benchmark)
  ↓
WandB logging every 50 steps (automatic)
  ↓
Results computed
  ↓
Post to embed-results: ah post embed-results '{"name": "...", "nDCG@10": 31.2}'
  ↓
Git commit: git add -A && git commit -am "exp: experiment-name" && git push
  ↓
experiment.py polls for next job
```

**Total time per experiment**: ~60-90 minutes (fully automated on pod)

### Flow 3: Result Aggregation

```
orchestrator.py polling results
  ↓
ah read embed-results (reads all postings)
  ↓
For each result:
  • Parse JSON
  • Log to leaderboard.jsonl
  • Print to console
  ↓
Check if pod completed:
  • prime pods status <pod-id>
  • If status = "completed", terminate pod
  ↓
If experiments remain in queue:
  • Launch new pods to refill slot
  ↓
Continue monitoring
```

**Frequency**: Every 30 seconds (automated)

---

## Error Handling (Automated)

### Scenario: Pod Crashes During Training

```
orchestrator.py: prime pods status <pod-id> → "failed"
  ↓
Orchestrator logs error
  ↓
Pod automatically terminated
  ↓
Experiment marked incomplete (if job was assigned)
  ↓
Job can be re-assigned to next pod (or manually)
  ↓
orchestrator.py launches new pod to refill slot
```

**No manual intervention**: Orchestrator automatically recovers

### Scenario: Cloud Node Context Exhaustion

```
experiment.py running → token limit reached
  ↓
Process receives SIGKILL (pod timeout)
  ↓
supervisor.sh detects exit (not code 0)
  ↓
Wait 5 seconds
  ↓
Restart experiment.py (max 10 retries)
  ↓
experiment.py resumes polling (idempotent)
```

**No manual intervention**: supervisor.sh automatically handles restarts

### Scenario: API Connection Loss

```
experiment.py: ah read embed-jobs → network timeout
  ↓
Catch exception, log warning
  ↓
Sleep 30 seconds
  ↓
Retry polling
```

**No manual intervention**: Automatic retry logic in experiment.py

### Scenario: WandB API Rate Limit

```
training loop: wandb.log(metric)
  ↓
HTTP 429 (rate limit)
  ↓
wandb library: exponential backoff + retry
  ↓
Retry succeeds
```

**No manual intervention**: WandB SDK handles retries

---

## Monitoring & Observability

### 1. Local Orchestrator Logs

```bash
# Real-time
tail -f ~/.local/var/log/agenthub/orchestrator.stderr.log

# Watch pods
watch -n 10 'prime pods list'

# Watch results
watch -n 10 'ah read embed-results | tail -5'
```

### 2. Pod-Level Logs

```bash
# Stream pod logs
prime pods logs <pod-id> --follow

# View last 100 lines
prime pods logs <pod-id> | tail -100
```

### 3. WandB Dashboard

```
https://wandb.ai/pierretokns/autoresearch-embed
```

Live metrics:
- Training loss per stage
- Evaluation nDCG@10
- GPU utilization
- Training time

### 4. Leaderboard (Local)

```bash
# View all results
cat leaderboard.jsonl | jq .

# Sort by nDCG@10
cat leaderboard.jsonl | jq -s 'sort_by(.nDCG@10) | reverse'

# Filter by experiment type
cat leaderboard.jsonl | jq 'select(.eval_dataset == "BRIGHT")'
```

### 5. Git DAG (Cloud Nodes)

```bash
# View all cloud node branches
ah leaves

# View specific node results
git log remote/node-1 --oneline

# Fetch all nodes
git fetch --all
```

---

## Scaling & Limits

### Current (Free Tier)

| Resource | Limit | Current |
|----------|-------|---------|
| Pods | 4 | 4/4 (maxed) |
| GPU Type | L40 | 48GB VRAM |
| CPU per pod | 14 | 14 |
| Memory per pod | 128Gi | 128Gi |
| Disk per pod | 625Gi | 625Gi |
| Experiments queue | Unlimited | 8 queued |
| Duration per experiment | 120 min | 90 min |

### How to Scale (Paid Tier)

1. **Switch GPU**: `gpu_type: "H100"` in orchestrator_config.yaml
2. **Increase pods**: `max_pods: 16` (requires paid tier)
3. **Larger batches**: `batch_size: 1024` (H100 has more VRAM)
4. **Longer timeouts**: `timeout_minutes: 240` (4 hours per experiment)

Everything else (orchestration, monitoring, result collection) scales automatically.

---

## Maintenance

### Daily

- [ ] Monitor WandB dashboard for any NaNs or anomalies
- [ ] Check logs for any persistent errors: `tail -f ~/.local/var/log/agenthub/orchestrator.stderr.log`

### Weekly

- [ ] Rotate logs if size > 1GB: `mv orchestrator.*.log orchestrator.*.log.$(date +%s).bak`
- [ ] Verify daemon is running: `bash scripts/manage_orchestrator.sh status`
- [ ] Check leaderboard for expected improvements: `cat leaderboard.jsonl | jq -s 'length'`

### Monthly

- [ ] Review all experiments on WandB for insights
- [ ] Archive leaderboard: `cp leaderboard.jsonl leaderboard.$(date +%Y-%m-%d).jsonl`
- [ ] Clean up old pod logs: `rm ~/.local/var/log/agenthub/orchestrator.*.log.* 2>/dev/null`
- [ ] Check PrimeIntellect account usage and quota

### Before Major Changes

- [ ] Backup leaderboard: `cp leaderboard.jsonl leaderboard.backup.jsonl`
- [ ] Stop daemon: `bash scripts/manage_orchestrator.sh stop`
- [ ] Test config changes on single pod
- [ ] Restart daemon: `bash scripts/manage_orchestrator.sh restart`

---

## Summary: Zero-Touch Infrastructure

| Concern | Automated? | Manual Action |
|---------|-----------|---------------|
| Pod creation | ✅ | Never |
| Pod monitoring | ✅ | Check status optional |
| Pod termination | ✅ | Never |
| Job assignment | ✅ | Never |
| Training execution | ✅ | Never |
| Result collection | ✅ | View via dashboard |
| Git sync | ✅ | Never |
| Logging | ✅ | Tail logs optional |
| Error recovery | ✅ | Retries automatic |
| Daemon operation | ✅ | Start once, runs 24/7 |
| Leaderboard updates | ✅ | Real-time |
| WandB logging | ✅ | Live updates |

**Result**: Agent can focus 100% on research. Infrastructure handles:
- Deployment
- Monitoring
- Reliability
- Result collection
- Coordination

All transparently and automatically.
