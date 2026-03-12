# Prime Lab: Research Online - Free Tier Guide

**Official Prime Intellect Lab for running embedding research experiments online**

---

## What is Prime Lab?

Prime Lab is PrimeIntellect's **open research platform for post-training**:
- Host RL training runs (no infrastructure management)
- Create & share environments
- Run evaluations at scale
- Sandbox code execution
- Multi-model inference
- **Free tier for research**

---

## Quick Start: Train Your First Model

### 1. Initialize Project
```bash
# Set up verifiers development environment
prime lab setup

# This creates:
# - Python project with prime-rl
# - Environment templates
# - Training configs
# - Documentation
```

### 2. Create Training Config
```bash
# Generate training config template
prime rl init embedding_training.toml
```

Edit `embedding_training.toml`:
```toml
model = "PrimeIntellect/Qwen3-1.5B-Instruct"
max_steps = 5000
batch_size = 256

# Choose environment for research
[[env]]
id = "primeintellect/bright-retrieval"
args = { split = "train" }

# Optional: Add W&B logging
[wandb]
project = "autoresearch-embed"
entity = "your-username"

# Optional: Online evaluation
[eval]
interval = 500
[[eval.env]]
id = "primeintellect/bright-retrieval"
args = { split = "test" }
```

### 3. Launch Training
```bash
prime rl run embedding_training.toml
```

Output:
```
✓ Training run started
  Run ID: run-abc123xyz
  Model: PrimeIntellect/Qwen3-1.5B-Instruct
  Max steps: 5000
  Monitoring: https://lab.primeintellect.ai/runs/run-abc123xyz
```

### 4. Monitor Training
```bash
# Watch logs in real-time
prime rl logs run-abc123xyz --follow

# Check metrics
prime rl metrics run-abc123xyz

# List all your runs
prime rl list
```

---

## Free Tier Details

### What's Included
- ✅ Hosted RL training (up to 10 concurrent runs)
- ✅ Inference API (free models)
- ✅ Sandbox code execution
- ✅ Environment hub (create, share)
- ✅ Evaluations (basic tier)
- ✅ WandB integration
- ✅ Checkpointing & resume

### Limits
- Max 10 concurrent training runs
- Standard compute (L40S GPUs)
- Up to 10 hours per training run
- 100 GB storage for checkpoints

### Upgrade to Paid
- Unlimited concurrent runs
- H100 GPUs available
- Longer training duration (24h+)
- Dedicated resources

---

## Training Configs for Embedding Research

### Baseline: BRIGHT Retrieval
```toml
# bright_baseline.toml
model = "PrimeIntellect/Qwen3-1.5B-Instruct"
max_steps = 10000
batch_size = 512
learning_rate = 2e-5
rollouts_per_example = 8

[[env]]
id = "primeintellect/bright-retrieval"
args = { split = "train" }

[wandb]
project = "autoresearch-embed"
entity = "pierretokns"
name = "bright-baseline-$(date +%Y%m%d)"

[eval]
interval = 1000
[[eval.env]]
id = "primeintellect/bright-retrieval"
args = { split = "test" }

[checkpoints]
interval = 1000
keep_cloud = 3
```

Launch:
```bash
prime rl run bright_baseline.toml
```

### Multi-Task: BRIGHT + FollowIR + MIRACL
```toml
# multi_task.toml
model = "PrimeIntellect/Qwen3-1.5B-Instruct"
max_steps = 15000
batch_size = 384
learning_rate = 1.5e-5

# Train on all three benchmarks
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
env_ratios = [0.5, 0.3, 0.2]

[wandb]
project = "autoresearch-embed"
name = "multi-task-baseline"

[eval]
interval = 1500
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

### Advanced: Curriculum Learning
```toml
# curriculum.toml
model = "PrimeIntellect/Qwen3-1.5B-Instruct"
max_steps = 20000
batch_size = 256

[[env]]
id = "primeintellect/bright-retrieval"
args = { split = "train" }

[buffer]
# Start with hard examples only
hard_threshold = 0.2
hard_fraction = 1.0
online_difficulty_filtering = true

[wandb]
project = "autoresearch-embed"
name = "curriculum-learning"

[eval]
interval = 2000
[[eval.env]]
id = "primeintellect/bright-retrieval"
args = { split = "test" }
```

---

## Available Environments for Retrieval Research

```bash
# List all available environments
prime rl models

# Available benchmark environments:
primeintellect/bright-retrieval          # BRIGHT benchmark
primeintellect/followir-retrieval        # FollowIR benchmark
primeintellect/miracl-retrieval          # MIRACL cross-lingual
primeintellect/code-search               # Code search
primeintellect/math-reasoning            # Math problem solving
```

Each environment has splits:
- `split: "train"` — Training data
- `split: "test"` — Test/eval data
- `split: "val"` — Validation data (if available)

---

## CLI Commands Reference

### Configuration & Setup
```bash
prime lab setup                          # Initialize lab project
prime rl init <config.toml>              # Generate config template
prime rl init <config.toml> --force      # Overwrite existing
```

### Launch & Monitor Training
```bash
prime rl run <config.toml>               # Start training run
prime rl list                            # List all runs
prime rl get <run-id>                    # Run details
prime rl logs <run-id>                   # View logs
prime rl logs <run-id> --follow          # Follow logs (tail -f)
prime rl metrics <run-id>                # Training metrics
```

### Training Control
```bash
prime rl stop <run-id>                   # Stop running experiment
prime rl delete <run-id>                 # Delete run
prime rl restart <run-id>                # Resume from checkpoint
```

### Advanced Monitoring
```bash
prime rl progress <run-id>               # Current progress & ETA
prime rl checkpoints <run-id>            # Saved checkpoints
prime rl rollouts <run-id>               # Sample model outputs
prime rl distributions <run-id>          # Reward distribution
```

---

## Running Multiple Experiments

### Sequential Runs
```bash
#!/bin/bash

configs=(
    "bright_baseline.toml"
    "followir_baseline.toml"
    "miracl_baseline.toml"
)

for config in "${configs[@]}"; do
    echo "Starting: $config"
    prime rl run "$config"
    sleep 60  # Wait before next launch
done
```

### Parallel Runs (free tier: up to 10)
```bash
#!/bin/bash

# Launch multiple training runs in parallel
prime rl run bright_baseline.toml &
prime rl run followir_baseline.toml &
prime rl run miracl_baseline.toml &

# Wait for all to complete
wait

# Collect results
prime rl list | grep "completed"
```

---

## W&B Integration (Live Metrics)

Your training runs automatically log to W&B:

```toml
[wandb]
project = "autoresearch-embed"
entity = "pierretokns"
name = "baseline-bright"
```

Then view at: **https://wandb.ai/pierretokns/autoresearch-embed**

Logged metrics:
- Loss per step
- Reward per step
- Evaluation scores (nDCG@10)
- Throughput (steps/sec)
- Learning rate schedule
- Model checkpoint sizes

---

## Checkpointing & Resuming

### Automatic Checkpointing
```toml
[checkpoints]
interval = 500              # Save every 500 steps
keep_cloud = 5              # Keep last 5 checkpoints
```

Then:
```bash
# List saved checkpoints
prime rl checkpoints <run-id>

# Resume from checkpoint
prime rl restart <run-id>
```

### Warm-start from Previous Run
```toml
# In new config, specify checkpoint from old run
checkpoint_id = "ckpt-xyz123"
```

---

## Troubleshooting

### Run Won't Start
```bash
# Validate config syntax
prime rl init test.toml
# Edit test.toml, try again

# Check available environments
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

### Training Too Slow
```bash
# Check infrastructure
prime rl get <run-id>

# If on slow GPU, restart with upgrade:
prime rl restart <run-id>  # Uses available H100 if paid tier
```

### Lost Logs
```bash
# Retrieve saved logs from run
prime rl logs <run-id> > logs.txt

# Metrics are in W&B (check wandb.ai)
```

---

## Cost Estimation (Free Tier)

| Resource | Limit | Cost |
|----------|-------|------|
| Training runs | 10 concurrent | Free |
| Compute | L40S GPU | Free |
| Storage | 100 GB checkpoints | Free |
| Runtime | 10 hours per run | Free |
| Inference API | Included | Free |

For **unlimited runs** and **H100 GPUs**, upgrade to paid tier.

---

## Complete Example: Run 3 Baselines

```bash
#!/bin/bash
set -e

echo "Setting up Prime Lab research"

# 1. Initialize project
prime lab setup --no-interactive

# 2. Create baseline configs
mkdir -p configs

cat > configs/bright.toml << 'EOF'
model = "PrimeIntellect/Qwen3-1.5B-Instruct"
max_steps = 10000
batch_size = 512
[[env]]
id = "primeintellect/bright-retrieval"
args = { split = "train" }
[wandb]
project = "autoresearch-embed"
name = "bright-baseline"
[eval]
interval = 1000
[[eval.env]]
id = "primeintellect/bright-retrieval"
args = { split = "test" }
EOF

cat > configs/followir.toml << 'EOF'
model = "PrimeIntellect/Qwen3-1.5B-Instruct"
max_steps = 10000
batch_size = 512
[[env]]
id = "primeintellect/followir-retrieval"
args = { split = "train" }
[wandb]
project = "autoresearch-embed"
name = "followir-baseline"
[eval]
interval = 1000
[[eval.env]]
id = "primeintellect/followir-retrieval"
args = { split = "test" }
EOF

cat > configs/miracl.toml << 'EOF'
model = "PrimeIntellect/Qwen3-1.5B-Instruct"
max_steps = 10000
batch_size = 512
[[env]]
id = "primeintellect/miracl-retrieval"
args = { split = "train" }
[wandb]
project = "autoresearch-embed"
name = "miracl-baseline"
[eval]
interval = 1000
[[eval.env]]
id = "primeintellect/miracl-retrieval"
args = { split = "test" }
EOF

# 3. Launch all three in parallel
echo "Launching training runs..."
prime rl run configs/bright.toml &
prime rl run configs/followir.toml &
prime rl run configs/miracl.toml &

# 4. Wait for completion and collect results
wait

# 5. View results
echo "Training complete! View results:"
prime rl list
echo "Dashboard: https://wandb.ai/pierretokns/autoresearch-embed"
```

Run it:
```bash
bash run_experiments.sh
```

---

## Next Steps

1. **Install prime lab**: Already done via `uv tool install prime`
2. **Create config**: `prime rl init my_experiment.toml`
3. **Edit config**: Add your benchmark, model, hyperparameters
4. **Launch**: `prime rl run my_experiment.toml`
5. **Monitor**: `prime rl logs <run-id> --follow`
6. **View results**: https://wandb.ai/pierretokns/autoresearch-embed

---

## Official Resources

- **Docs**: https://docs.primeintellect.ai
- **Lab Blog**: https://primeintellect.ai/blog/lab
- **GitHub**: https://github.com/PrimeIntellect-ai
- **Environments Hub**: https://lab.primeintellect.ai/environments

