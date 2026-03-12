# Prime RL: Hosted Research Training Online

**Complete guide for `prime rl` — PrimeIntellect's hosted training platform**

---

## Overview

`prime rl` is PrimeIntellect's **hosted training system** for online research:

```bash
prime rl init config.toml           # Create training config
prime rl run config.toml            # Launch training run
prime rl list                       # View all runs
prime rl get <run-id>               # Run details
prime rl logs <run-id>              # View logs
prime rl metrics <run-id>            # Training metrics
prime rl stop <run-id>              # Stop run
prime rl restart <run-id>           # Resume from checkpoint
```

---

## Quick Start

### 1. Create Config
```bash
# Generate template
prime rl init embedding_training.toml

# Edit with your settings
```

### 2. Configure Training
```toml
# embedding_training.toml
model = "PrimeIntellect/Qwen3-0.6B-Reverse-Text-SFT"
max_steps = 1000
batch_size = 256

[[env]]
id = "primeintellect/embedding-train"

[wandb]
project = "autoresearch-embed"
entity = "pierretokns"
```

### 3. Launch
```bash
prime rl run embedding_training.toml
```

### 4. Monitor
```bash
prime rl logs <run-id> --follow
prime rl metrics <run-id>
```

---

## Full Command Reference

### Initialization
```bash
# Create template config
prime rl init                               # Creates rl.toml
prime rl init my_training.toml              # Custom filename
prime rl init my_training.toml --force      # Overwrite existing
```

### Running
```bash
# Launch training
prime rl run config.toml                    # Start training run

# Launch with overrides (from command line)
prime rl run config.toml --max-steps 2000
prime rl run config.toml --batch-size 512

# Resume from checkpoint
prime rl run config.toml --checkpoint-id <id>
```

### Monitoring & Results
```bash
# List all runs
prime rl list
prime rl ls                                 # Alias

# Get run details
prime rl get <run-id>

# View training logs (real-time with --follow)
prime rl logs <run-id>
prime rl logs <run-id> --follow             # Tail -f style

# Training metrics
prime rl metrics <run-id>

# Rollout samples from run
prime rl rollouts <run-id>

# Training progress
prime rl progress <run-id>

# Reward/advantage distributions
prime rl distributions <run-id>

# Checkpoints saved
prime rl checkpoints <run-id>
```

### Control
```bash
# Stop running training
prime rl stop <run-id>

# Delete completed run
prime rl delete <run-id>

# Restart from latest checkpoint
prime rl restart <run-id>
```

---

## Config Reference

### Minimal Config
```toml
model = "PrimeIntellect/Qwen3-0.6B-Reverse-Text-SFT"
max_steps = 100

[[env]]
id = "primeintellect/reverse-text"
```

### Full Config Example
```toml
# Model & Training
model = "PrimeIntellect/Qwen3-0.6B-Reverse-Text-SFT"
max_steps = 10000
batch_size = 256
rollouts_per_example = 8
learning_rate = 1e-6
lora_alpha = 16

# Optional: Warm-start from checkpoint
checkpoint_id = "ckpt-12345"

# Sampling
[sampling]
max_tokens = 2048
temperature = 0.7

# Training environments
[[env]]
id = "primeintellect/reverse-text"

[[env]]
id = "primeintellect/code-generation"
args = { split = "train" }

# W&B Logging
[wandb]
project = "autoresearch-embed"
entity = "pierretokns"
name = "baseline-embedding-v1"

# Online Evaluation (during training)
[eval]
interval = 100                # Evaluate every N steps
num_examples = -1             # -1 = all examples
rollouts_per_example = 1

[[eval.env]]
id = "primeintellect/embedding-eval"
args = { split = "test" }
num_examples = 500            # Override for this env

# Validation (during training)
[val]
num_examples = 64
rollouts_per_example = 1
interval = 5

# Difficulty Filtering
[buffer]
easy_threshold = 0.8
hard_threshold = 0.2
easy_fraction = 0.0           # 0% easy examples
hard_fraction = 1.0           # 100% hard examples
online_difficulty_filtering = true

# Checkpoint Saving
[checkpoints]
interval = 100                # Save every 100 steps
keep_cloud = 5                # Keep 5 checkpoints in cloud

# Adapter Upload
[adapters]
interval = 100                # Upload every 100 steps
keep_last = 3                 # Keep 3 adapters

# Infrastructure
[infrastructure]
compute_size = "M"            # S, M (default), L

# Secrets (optional)
# env_files = ["secrets.env"]
```

---

## Embedding Research Workflow

### Config for BRIGHT Baseline
```toml
# bright_baseline.toml
model = "PrimeIntellect/Qwen3-1.5B-Instruct"
max_steps = 5000
batch_size = 512
learning_rate = 2e-5

[[env]]
id = "primeintellect/bright-retrieval"
args = { split = "train" }

[wandb]
project = "autoresearch-embed"
entity = "pierretokns"
name = "bright-baseline"

[eval]
interval = 500
[[eval.env]]
id = "primeintellect/bright-retrieval"
args = { split = "test" }

[checkpoints]
interval = 500
keep_cloud = 3
```

Launch:
```bash
prime rl run bright_baseline.toml
```

Monitor:
```bash
# Get run ID from output or
prime rl list | grep "bright-baseline"

# Watch training in real-time
prime rl logs <run-id> --follow

# Check metrics
prime rl metrics <run-id>
```

### Config for Multi-Env Training
```toml
# multi_env.toml
model = "PrimeIntellect/Qwen3-1.5B-Instruct"
max_steps = 10000
batch_size = 256

# Train on multiple benchmarks
[[env]]
id = "primeintellect/bright-retrieval"
args = { split = "train" }

[[env]]
id = "primeintellect/followir-retrieval"
args = { split = "train" }

[[env]]
id = "primeintellect/miracl-retrieval"
args = { split = "train" }

[buffer]
env_ratios = [0.5, 0.3, 0.2]  # Sample ratio per env

[wandb]
project = "autoresearch-embed"
name = "multi-env-baseline"

[eval]
interval = 500
[[eval.env]]
id = "primeintellect/bright-retrieval"
args = { split = "test" }

[[eval.env]]
id = "primeintellect/followir-retrieval"
args = { split = "test" }

[[eval.env]]
id = "primeintellect/miracl-retrieval"
args = { split = "test" }
```

---

## Monitoring Training

### Real-time Logs
```bash
# Follow logs as they stream
prime rl logs <run-id> --follow

# Example output:
# [2026-03-11 17:35:00] Step 100/10000
# [2026-03-11 17:35:15] Reward: 0.523 | Loss: 0.234
# [2026-03-11 17:35:30] Evaluation: nDCG@10 = 0.42
```

### Metrics
```bash
# Get all metrics
prime rl metrics <run-id>

# Returns JSON with:
# - avg_reward
# - loss
# - learning_rate
# - tokens_per_second
# - eval_metrics (if eval_interval set)
```

### Progress Tracking
```bash
# Current step, ETA, etc.
prime rl progress <run-id>

# Shows:
# - Current step / total steps
# - Time elapsed / estimated remaining
# - Throughput (steps/sec)
# - Status (running, paused, completed)
```

### Checkpoints
```bash
# List all checkpoints for run
prime rl checkpoints <run-id>

# Returns:
# - Checkpoint ID
# - Step number
# - Size
# - Timestamp
```

### Rollouts
```bash
# Get sample rollouts from training
prime rl rollouts <run-id>

# Shows examples of:
# - Input prompt
# - Model output
# - Reward score
# - Environment feedback
```

---

## Training Control

### Pause & Resume
```bash
# Stop current run
prime rl stop <run-id>

# Resume from latest checkpoint
prime rl restart <run-id>

# This saves checkpoint every N steps and resumes from there
```

### Modify During Training
```bash
# Update learning rate (via config + restart)
# Edit config file, change learning_rate, then:
prime rl restart <run-id>

# Note: Will resume from last checkpoint with new settings
```

---

## W&B Integration

### Automatic Logging
Configure in your config:
```toml
[wandb]
project = "autoresearch-embed"
entity = "pierretokns"
name = "run-name-{timestamp}"
```

Then:
```bash
prime rl run config.toml
```

All metrics automatically logged to WandB:
- Loss, reward per step
- Evaluation metrics (nDCG@10, etc.)
- Model checkpoint sizes
- Training throughput
- Difficulty distribution

View at: https://wandb.ai/pierretokns/autoresearch-embed

---

## Available Models

```bash
prime rl models
```

Returns list of available base models:
- `PrimeIntellect/Qwen3-0.6B-Reverse-Text-SFT`
- `PrimeIntellect/Qwen3-1.5B-Instruct`
- `PrimeIntellect/Llama3.1-8B-Instruct`
- (And others)

---

## Available Environments

Common research environments:
- `primeintellect/reverse-text` — Text reversal task
- `primeintellect/bright-retrieval` — BRIGHT benchmark
- `primeintellect/followir-retrieval` — FollowIR benchmark
- `primeintellect/miracl-retrieval` — MIRACL benchmark
- `primeintellect/code-generation` — Code synthesis
- `primeintellect/math-reasoning` — Math problem solving

Check available:
```bash
prime rl models
```

---

## Integration with Orchestrator

Update `orchestrator.py` to use `prime rl` instead of `prime pods`:

```python
import subprocess
import json

def launch_rl_training(config_path: str, run_name: str):
    """Launch training via prime rl."""
    config = {
        "model": "PrimeIntellect/Qwen3-1.5B-Instruct",
        "max_steps": 5000,
        "batch_size": 512,
        "wandb": {
            "project": "autoresearch-embed",
            "name": run_name,
        },
        # ... more config
    }

    # Write config to file
    with open(config_path, "w") as f:
        toml.dump(config, f)

    # Launch via prime rl
    result = subprocess.run(
        ["prime", "rl", "run", config_path],
        capture_output=True,
        text=True,
    )

    # Parse run ID from output
    run_id = extract_run_id(result.stdout)
    return run_id

def monitor_training(run_id: str):
    """Monitor training run."""
    # Get metrics
    metrics = subprocess.run(
        ["prime", "rl", "metrics", run_id],
        capture_output=True,
        text=True,
    )

    return json.loads(metrics.stdout)
```

---

## Troubleshooting

### Run Won't Start
```bash
# Check config syntax
prime rl init test.toml
# Edit and try again

# Verify environment exists
prime rl models
```

### Out of Memory
```toml
# Reduce batch size
batch_size = 128

# Reduce rollouts
rollouts_per_example = 4

# Use smaller model
model = "PrimeIntellect/Qwen3-0.6B-Reverse-Text-SFT"
```

### Slow Training
```toml
# Increase batch size
batch_size = 512

# Reduce evaluation frequency
[eval]
interval = 1000  # Evaluate less often

# More GPU resources
[infrastructure]
compute_size = "L"
```

### Checkpoint Issues
```bash
# List available checkpoints
prime rl checkpoints <run-id>

# Restart from specific checkpoint
prime rl run config.toml --checkpoint-id <ckpt-id>
```

---

## Performance Tips

### Multi-Environment Training
```toml
[[env]]
id = "primeintellect/bright-retrieval"
[[env]]
id = "primeintellect/followir-retrieval"

[buffer]
env_ratios = [0.7, 0.3]  # Weighted sampling
online_difficulty_filtering = true  # Hard example mining
```

### Efficient Checkpointing
```toml
[checkpoints]
interval = 500              # Save every 500 steps (not too frequent)
keep_cloud = 5              # Keep last 5 (save space)

[adapters]
interval = 1000
keep_last = 2
```

### Cost Optimization
```toml
[infrastructure]
compute_size = "M"          # Smaller = cheaper
max_steps = 5000            # Shorter runs
batch_size = 256            # Smaller batches = lower memory
```

---

## Complete Example: End-to-End

```bash
#!/bin/bash
set -e

# 1. Create config for BRIGHT baseline
cat > bright_training.toml << 'EOF'
model = "PrimeIntellect/Qwen3-1.5B-Instruct"
max_steps = 10000
batch_size = 512
learning_rate = 2e-5

[[env]]
id = "primeintellect/bright-retrieval"
args = { split = "train" }

[wandb]
project = "autoresearch-embed"
entity = "pierretokns"
name = "bright-baseline-$(date +%Y%m%d-%H%M%S)"

[eval]
interval = 1000
[[eval.env]]
id = "primeintellect/bright-retrieval"
args = { split = "test" }

[checkpoints]
interval = 1000
keep_cloud = 3
EOF

# 2. Launch training
echo "Launching training run..."
prime rl run bright_training.toml | tee /tmp/run_id.log

# Extract run ID
RUN_ID=$(grep -oE 'run-[a-z0-9]+' /tmp/run_id.log | head -1)
echo "Run ID: $RUN_ID"

# 3. Monitor training
echo "Watching training progress..."
prime rl logs "$RUN_ID" --follow &
LOGS_PID=$!

# Wait for completion (or manual stop)
while true; do
    status=$(prime rl get "$RUN_ID" | grep -oE 'completed|failed|stopped' || echo "running")
    if [ "$status" != "running" ]; then
        kill $LOGS_PID
        break
    fi
    sleep 30
done

# 4. Collect final metrics
echo "Final metrics:"
prime rl metrics "$RUN_ID"

# 5. Get checkpoints
echo "Saved checkpoints:"
prime rl checkpoints "$RUN_ID"
```

---

## See Also

- `prime availability` — Check resource availability
- `prime sandbox` — Alternative for custom code execution
- `prime pods` — Lower-level compute control
- WandB dashboard: https://wandb.ai/pierretokns/autoresearch-embed
