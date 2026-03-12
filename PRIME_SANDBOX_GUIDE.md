# Prime Sandbox Online Execution Guide

**For running cloud research experiments using `prime sandbox` commands**

---

## Overview

`prime sandbox` provides online code execution environment for cloud research:

```bash
prime sandbox create              # Create a sandbox (online VM)
prime sandbox run <id> <command>  # Execute code in sandbox
prime sandbox upload <id> <file>  # Upload files to sandbox
prime sandbox download <id> <file># Download results
prime sandbox ssh <id>            # SSH access
prime sandbox expose <id> <port>  # Expose ports for services
```

---

## Full Command Reference

### Create Sandbox
```bash
# Create a new sandbox
prime sandbox create

# Creates and returns:
# - Sandbox ID (e.g., sb-abc123xyz)
# - SSH connection info
# - Ready for commands via prime sandbox run
```

### Run Commands
```bash
# Execute single command
prime sandbox run <sandbox-id> "python3 script.py"

# Execute with output
prime sandbox run <sandbox-id> "pip install -r requirements.txt && python3 train.py"

# Multiple commands
prime sandbox run <sandbox-id> "cd /tmp && python3 populate_disk.py"
```

### File Operations
```bash
# Upload file to sandbox
prime sandbox upload <sandbox-id> ./scripts/populate_disk.py /tmp/populate_disk.py

# Upload directory (tar + upload)
tar czf scripts.tar.gz scripts/
prime sandbox upload <sandbox-id> ./scripts.tar.gz /tmp/scripts.tar.gz

# Download results
prime sandbox download <sandbox-id> /tmp/embed-data/contamination_report.json ./results/

# Download all results
prime sandbox run <sandbox-id> "tar czf /tmp/results.tar.gz /tmp/embed-data/"
prime sandbox download <sandbox-id> /tmp/results.tar.gz ./results/
```

### SSH Access
```bash
# Direct SSH terminal
prime sandbox ssh <sandbox-id>

# Execute command via SSH
ssh <sandbox-ssh-host> "python3 /tmp/populate_disk.py"

# SSH tunneling (expose ports)
prime sandbox expose <sandbox-id> 8080
# Port 8080 inside sandbox → accessible externally
```

### Monitor & Cleanup
```bash
# List all sandboxes
prime sandbox list

# Get sandbox details
prime sandbox get <sandbox-id>

# View sandbox logs
prime sandbox logs <sandbox-id>

# Delete sandbox
prime sandbox delete <sandbox-id>

# Delete all
prime sandbox delete --all
```

---

## Cloud Research Workflow Using Sandboxes

### Step 1: Create Sandbox for Data Population

```bash
# Create sandbox
SANDBOX_ID=$(prime sandbox create | grep -oE 'sb-[a-z0-9]+' | head -1)

# Upload populate_disk.py
prime sandbox upload "$SANDBOX_ID" ./autoresearch-cloud/scripts/populate_disk.py /tmp/populate_disk.py

# Install dependencies in sandbox
prime sandbox run "$SANDBOX_ID" "pip install -q datasets transformers huggingface-hub mteb pyyaml"

# Run population
prime sandbox run "$SANDBOX_ID" "EMBED_DATA_DIR=/tmp/embed-data python3 /tmp/populate_disk.py"

# Download contamination report
prime sandbox download "$SANDBOX_ID" /tmp/embed-data/contamination_report.json ./data/

# Cleanup
prime sandbox delete "$SANDBOX_ID"
```

### Step 2: Create Sandbox for Training Pod Manager

```bash
# Create persistent sandbox for orchestrator
ORCH_SANDBOX=$(prime sandbox create | grep -oE 'sb-[a-z0-9]+' | head -1)
echo "Orchestrator sandbox: $ORCH_SANDBOX" > /tmp/orch_sandbox.id

# Upload orchestrator code
prime sandbox upload "$ORCH_SANDBOX" ./agenthub/scripts/orchestrator.py /tmp/orchestrator.py

# Install dependencies
prime sandbox run "$ORCH_SANDBOX" "pip install -q pyyaml wandb"

# Expose metrics port (optional WandB streaming)
prime sandbox expose "$ORCH_SANDBOX" 8000

# Start orchestrator (long-running in background)
prime sandbox run "$ORCH_SANDBOX" "nohup python3 /tmp/orchestrator.py &"
```

### Step 3: Monitor Execution

```bash
# Check orchestrator logs
prime sandbox logs "$ORCH_SANDBOX"

# Check active sandboxes
prime sandbox list

# SSH into sandbox for debugging
prime sandbox ssh "$ORCH_SANDBOX"
```

---

## Environment Setup in Sandbox

### Initial Setup Script

```bash
#!/bin/bash
# setup_sandbox.sh - run in sandbox

# 1. Install Python deps
pip install -q torch torchvision transformers datasets wandb huggingface-hub mteb pyyaml

# 2. Set environment
export EMBED_DATA_DIR=/mnt/embed-data
export HF_DATASETS_CACHE=/mnt/embed-data/hf_cache
export TRANSFORMERS_CACHE=/mnt/embed-data/hf_cache
export WANDB_PROJECT=autoresearch-embed

# 3. Clone repo (if needed)
git clone https://github.com/pierretokns/agenthub.git /tmp/agenthub
cd /tmp/agenthub

# 4. Ready for training
echo "Sandbox ready for cloud research"
```

Upload and run:
```bash
prime sandbox upload "$SANDBOX_ID" ./setup_sandbox.sh /tmp/setup.sh
prime sandbox run "$SANDBOX_ID" "bash /tmp/setup.sh"
```

---

## Data Persistence Between Sandboxes

**Important**: Sandboxes are ephemeral (data lost when deleted)

### Pattern: Use External Storage

```bash
# 1. Populate data in sandbox
prime sandbox run "$DATA_SANDBOX" "python3 /tmp/populate_disk.py"

# 2. Download before deleting sandbox
prime sandbox download "$DATA_SANDBOX" /tmp/embed-data /local/data/

# 3. Re-upload to training sandbox
prime sandbox upload "$TRAIN_SANDBOX" /local/data /mnt/embed-data

# 4. Clean up
prime sandbox delete "$DATA_SANDBOX"
```

Or use external persistent storage service (S3, GCS, etc.)

---

## Monitoring Sandboxes

### Real-time Logs
```bash
# Watch logs as they stream
prime sandbox logs <sandbox-id> --follow

# Get logs with timestamps
prime sandbox logs <sandbox-id> | tail -50
```

### Resource Monitoring
```bash
# Get sandbox details (CPU, memory, etc.)
prime sandbox get <sandbox-id>

# Check all active sandboxes
prime sandbox list --json | jq '.[] | {id, status, created_at}'
```

### Health Checks
```bash
# Test connectivity
prime sandbox run <sandbox-id> "echo 'OK'"

# Check Python available
prime sandbox run <sandbox-id> "python3 --version"

# Check installed packages
prime sandbox run <sandbox-id> "pip list | grep -E 'torch|transformers|mteb'"
```

---

## Troubleshooting

### Sandbox Creation Failed
```bash
# Check API key
echo $PRIME_INTELLECT_API_KEY

# Verify auth
prime whoami

# List available sandboxes
prime sandbox list
```

### Command Timeout
```bash
# Use nohup for long-running commands
prime sandbox run <id> "nohup python3 long_script.py > /tmp/output.log 2>&1 &"

# Check if still running
prime sandbox run <id> "ps aux | grep python3"
```

### File Upload Failed
```bash
# Verify file exists
ls -lh ./scripts/populate_disk.py

# Try smaller test upload
prime sandbox upload <id> /etc/hosts /tmp/test.txt

# Check sandbox disk space
prime sandbox run <id> "df -h /tmp"
```

### Download Empty Results
```bash
# Verify file exists in sandbox
prime sandbox run <id> "ls -la /tmp/embed-data/"

# Check file size
prime sandbox run <id> "du -sh /tmp/embed-data/"

# Create archive before download
prime sandbox run <id> "tar czf /tmp/results.tar /tmp/embed-data/"
prime sandbox download <id> /tmp/results.tar ./results.tar
tar xzf ./results.tar
```

---

## Performance Tips

### Parallel Sandboxes
```bash
# Create multiple training sandboxes
for i in {1..4}; do
  SANDBOX=$(prime sandbox create | grep -oE 'sb-[a-z0-9]+' | head -1)
  echo "Sandbox $i: $SANDBOX"
  # Upload and run training in parallel
done
```

### Batch Operations
```bash
# Upload to all active sandboxes
for SANDBOX in $(prime sandbox list --json | jq -r '.[].id'); do
  prime sandbox upload "$SANDBOX" ./script.py /tmp/script.py &
done
wait
```

### Optimize Data Transfer
```bash
# Compress before upload
gzip large_file.json
prime sandbox upload <id> large_file.json.gz /tmp/
prime sandbox run <id> "gunzip /tmp/large_file.json.gz"

# Use SSH for large transfers
prime sandbox ssh <id> < large_file_stream
```

---

## Integration with Orchestrator

The orchestrator can manage sandboxes:

```python
import subprocess

def run_in_sandbox(sandbox_id, command):
    """Execute command in sandbox."""
    result = subprocess.run(
        ["prime", "sandbox", "run", sandbox_id, command],
        capture_output=True,
        text=True,
    )
    return result.stdout, result.returncode

def upload_to_sandbox(sandbox_id, local_path, remote_path):
    """Upload file to sandbox."""
    subprocess.run(
        ["prime", "sandbox", "upload", sandbox_id, local_path, remote_path]
    )

def download_from_sandbox(sandbox_id, remote_path, local_path):
    """Download file from sandbox."""
    subprocess.run(
        ["prime", "sandbox", "download", sandbox_id, remote_path, local_path]
    )
```

---

## Complete Example: End-to-End Workflow

```bash
#!/bin/bash
set -e

# 1. Data population
echo "[1/3] Populating data..."
DATA_SANDBOX=$(prime sandbox create | grep -oE 'sb-[a-z0-9]+' | head -1)
prime sandbox upload "$DATA_SANDBOX" ./populate_disk.py /tmp/populate_disk.py
prime sandbox run "$DATA_SANDBOX" "pip install -q datasets transformers huggingface-hub mteb"
prime sandbox run "$DATA_SANDBOX" "EMBED_DATA_DIR=/tmp/data python3 /tmp/populate_disk.py"
prime sandbox download "$DATA_SANDBOX" /tmp/data ./local_data/
prime sandbox delete "$DATA_SANDBOX"

# 2. Training setup
echo "[2/3] Creating training sandbox..."
TRAIN_SANDBOX=$(prime sandbox create | grep -oE 'sb-[a-z0-9]+' | head -1)
prime sandbox upload "$TRAIN_SANDBOX" ./local_data /mnt/embed-data
prime sandbox upload "$TRAIN_SANDBOX" ./train_cuda.py /tmp/train.py
prime sandbox run "$TRAIN_SANDBOX" "pip install -q torch transformers wandb"

# 3. Execute training
echo "[3/3] Running training..."
prime sandbox run "$TRAIN_SANDBOX" "python3 /tmp/train.py"

# 4. Collect results
prime sandbox download "$TRAIN_SANDBOX" /tmp/results.json ./results/
prime sandbox delete "$TRAIN_SANDBOX"

echo "✓ Workflow complete"
```

---

## See Also

- `prime sandbox list` — View all sandboxes
- `prime sandbox get <id>` — Sandbox details
- `prime sandbox ssh <id>` — Direct access
- `prime availability` — Check GPU availability
- `prime pods` — Alternative for persistent GPUs
