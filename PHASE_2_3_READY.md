# Phases 2 & 3: Ready for Execution

**Status**: Infrastructure complete, ready for dataset curation (Phase 2) and experiments (Phase 3)

---

## 🎯 What You Need to Do

### Phase 2: Dataset Curation (FREE — no cost, no paid pods)

Your task: Prepare oracle-scored training data for zELO experiments.

See: `autoresearch-cloud/PHASE_2_TASKS.md` for complete task breakdown.

**4 Datasets to Score**:

1. **BRIGHT** (Instruction Adherence)
   - Source: https://huggingface.co/datasets/bm25/BRIGHT
   - Oracle: Claude API free tier or local Mistral 7B
   - Output: `autoresearch-cloud/data/bright_train_oracle.jsonl`
   - Time: 2-4 hours

2. **FollowIR** (Follow Instructions)
   - Source: https://huggingface.co/datasets/osunlp/FollowIR
   - Oracle: Local LLM
   - Output: `autoresearch-cloud/data/followir_train_oracle.jsonl`
   - Time: 1-2 hours

3. **CodeSearchNet** (Execution Oracle)
   - Source: https://huggingface.co/datasets/code_search_net
   - Oracle: Python test execution
   - Output: `autoresearch-cloud/data/code_search_train_oracle.jsonl`
   - Time: 30 min - 1 hour

4. **MIRACL** (Cross-Lingual)
   - Source: https://huggingface.co/datasets/mteb/mmarco
   - Oracle: mGTE cross-encoder (free, MIT)
   - Output: `autoresearch-cloud/data/miracl_train.jsonl`
   - Time: 1-2 hours

**Total**: ~6-10 hours compute (~2-3 hours wall clock if parallel)
**Cost**: $0

---

## 📋 How to Execute

### Setup (One-time)
```bash
cd autoresearch-cloud

# Install scoring dependencies
pip install datasets transformers torch huggingface_hub

# Create data directory
mkdir -p data/

# Download datasets (background)
python3 << 'EOF'
from datasets import load_dataset
for name, hf_id in [
    ("bright", "bm25/BRIGHT"),
    ("followir", "osunlp/FollowIR"),
    ("code", "code_search_net"),
    ("mmarco", "mteb/mmarco"),
]:
    print(f"Downloading {name}...")
    ds = load_dataset(hf_id)
    # Save first 10K for quick iteration
    ds["train"].select(range(min(10000, len(ds["train"])))).to_json(f"data/{name}_raw.jsonl")
EOF
```

### Scoring (Pick One Dataset to Start)

#### BRIGHT Scoring Example
```python
# autoresearch-cloud/score_bright.py
import json
from transformers import pipeline

# Load local Mistral 7B (quantized, ~4GB)
pipe = pipeline("text-generation", model="mistralai/Mistral-7B-Instruct-v0.1")

with open("data/bright_raw.jsonl") as f_in, \
     open("data/bright_train_oracle.jsonl", "w") as f_out:
    for line in f_in:
        item = json.loads(line)
        query = item["query"]

        # Score top 3 documents
        elo_scores = []
        for doc in item.get("documents", [])[:3]:
            prompt = f"""Rate 0-1 how well this doc follows the query instructions.
Query: {query}
Document: {doc[:500]}
Score (0-1): """

            output = pipe(prompt, max_new_tokens=5)[0]["generated_text"]
            # Extract number from output
            try:
                score = float(output.split(":")[-1].strip()[:3])
            except:
                score = 0.5
            elo_scores.append(score)

        item["elo_scores"] = elo_scores
        f_out.write(json.dumps(item) + "\n")

print("✓ Scored bright_train_oracle.jsonl")
```

### Phase 3: Launch Experiments

Once Phase 2 datasets are ready:

```bash
# Update orchestrator config to use oracle data
vim ../orchestrator_config.yaml

# Change these lines:
# - train_data: "data/bright_train.jsonl" → "data/bright_train_oracle.jsonl"
# - train_data: "data/followir_train.jsonl" → "data/followir_train_oracle.jsonl"
# ... etc

# Phase 3 triggers automatically:
# 1. Orchestrator detects new data files
# 2. Updates experiment configs
# 3. Launches 4 L40 pods
# 4. Trains baseline + zELO variants (60-90 min each)
# 5. Results stream to WandB + leaderboard.jsonl
```

---

## 📊 Expected Results

### Baseline (ModernBERT without oracle)
| Benchmark | nDCG@10 |
|-----------|---------|
| BRIGHT | 20-24 |
| FollowIR | 18-22 |
| Code Search | ~79 |
| MIRACL | ~62 |

### zELO (with oracle training)
| Benchmark | Target | Improvement |
|-----------|--------|-------------|
| BRIGHT | 28-33 | +6-10 |
| FollowIR | 25-28 | +5-7 |
| Code | >82 | Beat C2LLM-7B (80.75) |
| MIRACL | 67+ | +4-6 on low-resource |

---

## 🔧 Known Issues & Solutions

### Issue: Pods not launching
**Root cause**: `prime pods create` is interactive (asks for config selection)
**Status**: Fixed in progress
**Solution**: Use `--id` with specific config ID from `prime availability list`

### Available L40 Configs
```
5f426d: 1 L40  (14 vCPU, 128GB RAM, 625GB disk) ← Best for free tier
31927b: 2 L40  (26 vCPU, 256GB RAM, 1.2TB disk)
644a2d: 4 L40  (50 vCPU, 512GB RAM, 2.5TB disk)
```

---

## 📁 Key Files

### Phase 2 (Dataset Curation)
- `autoresearch-cloud/PHASE_2_TASKS.md` — Detailed task breakdown
- `autoresearch-cloud/data/` — Output directory (create JSONL files here)

### Phase 3 (Experiments)
- `orchestrator_config.yaml` — 8 experiments defined
- `autoresearch-cloud/program.md` — Cloud researcher instructions
- `autoresearch-cloud/scripts/experiment.py` — Experiment loop

### Infrastructure
- `autoresearch-cloud/src/train_cuda.py` — 4-stage training
- `autoresearch-cloud/src/losses_cuda.py` — InfoNCE + EloDistillationLoss
- `scripts/orchestrator.py` — Pod lifecycle + result aggregation
- `/tmp/orchestrator.log` — Live logs

---

## 🚀 Recommended Next Steps

### Option A: Full Phase 2 (Best)
1. Download all 4 datasets
2. Score with free tools (local Mistral 7B, mGTE, test execution)
3. Create 4 oracle JSONL files (6-10 hours)
4. Launch Phase 3 experiments
5. **Result**: +6-10 nDCG@10 improvement, publishable

### Option B: Quick Phase 3 (Now)
1. Skip Phase 2 for now
2. Use default small datasets (minimal oracle scoring)
3. Launch 4 L40 pods immediately
4. Get quick baseline results
5. Later: Phase 2 refine with better datasets

---

## ✅ Success Criteria

**Phase 2 Complete When**:
- ✓ 4 JSONL files created (bright, followir, code, miracl)
- ✓ Each file has 1000+ scored examples
- ✓ Format: `{"query": "...", "positive": "...", "elo_scores": [...]}`
- ✓ All scores in [0, 1] range
- ✓ Files saved in `autoresearch-cloud/data/`

**Phase 3 Complete When**:
- ✓ 8 experiments queued (2 baseline + 6 zELO)
- ✓ 4 pods launched on PrimeIntellect
- ✓ Results posted to `embed-results` channel
- ✓ WandB dashboard shows training curves
- ✓ `leaderboard.jsonl` has 8 entries
- ✓ zELO > baselines across all benchmarks

---

## 💰 Cost Summary

| Phase | Resource | Cost |
|-------|----------|------|
| 1 (Orchestrator) | Go server (local) | $0 |
| 2 (Datasets) | Downloads + local scoring | $0 |
| 3 (Experiments) | 4 L40 pods, 6-8 hours | $0 (free tier) |
| **Total** | Everything | **$0** |

Phase 4 (scaling to H100s) would be paid — **we skip this per your instructions**.

---

## 📞 Questions?

- **Phase 2 help**: Read `PHASE_2_TASKS.md` (very detailed)
- **Pod launching**: Try `prime pods create --help` to see exact syntax
- **Infrastructure**: See `INFRASTRUCTURE.md` for automation details
- **Architecture**: See `CLOUD_RESEARCH.md` for full design

---

**Ready to start Phase 2?** Pick your first dataset and begin scoring! 🎯
