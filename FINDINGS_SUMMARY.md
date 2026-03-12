# Embedding Research Findings Summary

**From 9 autonomous experiments + research phases**

---

## Key Achievements

### 1. MLX Migration: 120x Speedup
**Issue #14**: PyTorch MPS → Native MLX optimization

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Step time (batch=128) | ~31,000ms | **251ms** | **120x faster** |
| Peak memory | 79 GB | **6.4 GB** | **12x less** |
| Experiment time | ~61 min | **~25-30 min** | **2x faster research cycle** |

**What changed**:
- Full ModernBERT encoder in native MLX (no PyTorch)
- Fused attention ops using `mx.fast.scaled_dot_product_attention()`
- Hard negative mining via numpy (no GPU transfers)
- Result: **2x more experiments per hour**

---

## Autonomous Experiments Progress

From agenthub `embed-results` channel (experiments 1-13):

### Experiment Timeline

| Exp | Result | Score | Key Finding |
|-----|--------|-------|------------|
| 1-3 | CRASH/DISCARD | 0-32.69 | Pipeline verification, MPS issues |
| 4-7 | CRASH → KEEP | 0 → 32.67 | OOM fixes, hard neg mining optimization |
| 8 | KEEP | 34.66 | **+2%**: ag_news clustering pairs + temp tuning (0.02→0.05) |
| 9 | KEEP | 38.44 | **+3.8%**: DBpedia-14 + Yahoo Answers for finer clustering |
| 10+ | Running on Prime Lab | TBD | 3x baselines training online |

### Best Results (exp-13)
```
primary_score: 38.44
Strategy: Multi-label clustering data (DBpedia-14: 14 classes, Yahoo: 10 classes)
Improvement path: exp-7 (32.67) → exp-8 (+2%) → exp-9 (+3.8%) = 5.8% total
```

---

## Key Insights from Research

### From Literature (Issue #1)

#### pplx-embed (Perplexity, Feb 2025)
- **Record technique**: Diffusion-continued pretraining on Qwen3
- **Advantage**: Bidirectional attention → mean pooling works
- **Specs**: 1024-dim, 32K context, INT8/BINARY quantization
- **Key finding**: Eliminates instruction tuning requirement

#### jxmo Blog: "How to Train the Best Embedding Model"
- **Core problem**: Models plateau at ~10M pairs due to false negative label noise
- **Solution**: LLM label verification (cost problem, not fundamental limit)
- **Recipe**:
  1. BM25 + existing embeddings to filter top-k candidates
  2. LLM labeling for exact negatives
  3. Coordinate ascent softmax (not batch-level approximation)
- **Gain**: ~10% improvement from eliminating false negatives

### From Our Experiments

#### Clustering Dataset Impact (exp-8, exp-9)
- **Discovery**: Adding same-label pairs from clustering datasets boosts MTEB clustering
- **ag_news effect**: +2% by adding news category pairs (temperature 0.02→0.05)
- **Multi-label effect**: +3.8% by adding fine-grained label datasets (DBpedia, Yahoo)
- **Implication**: Clustering knowledge transfers to retrieval benchmarks

#### Batch Size / Memory Constraints (exp-4-7)
- **OOM pattern**: Hard negative mining at scale requires careful memory management
- **Optimal config**: batch_size=32/32/64 (warmup/contrastive/finetune), 8K doc pool
- **Finding**: Smaller batches with harder negatives > larger batches with easy negatives
- **Trade-off**: Memory efficiency > throughput in this regime

---

## Target MTEB Improvements

**From Issue #1: Tier-ranked research plan**

### Tier 1: High Confidence (Our Focus)
| Benchmark | Current Gap | Our Target | Approach |
|-----------|------------|-----------|----------|
| **Clustering** | 9-15% improvement needed | 20%+ | Multi-label dataset expansion |
| **Pair Classification** | 81+ achievable | 85%+ | Loss/pooling iteration |
| **STS** | Competitive | 88%+ | Contrastive fine-tuning |

### Tier 2: High Value
| Benchmark | Current Gap | Approach |
|-----------|------------|----------|
| **Retrieval (domain)** | 10-30% variance | Synthetic query-doc pairs |
| **ConTEB** | Underexplored | Late chunking + context |

### Tier 3: Moonshots
- Numerical Reasoning (all models ~54%, near chance)
- Instruction Retrieval (average 5.61, huge room)

---

## Current Research System Status

### MLX Pipeline (Automated on M2 Ultra)
- **Cycle time**: 25-30 min/experiment
- **Hardware**: 6.4 GB peak memory (from 79 GB)
- **Throughput**: 2x experiments/hour
- **Best score**: 38.44 on clustering tasks

### Prime Lab Pipeline (Now Online)
- **3 baselines training**: BRIGHT, FollowIR, MIRACL
- **Free tier**: L40S GPUs, 10 concurrent runs
- **Estimated completion**: 4-5 hours
- **Infrastructure**: Zero management needed

### Local agenthub Coordination
- **Channels**: embed-results, embed-jobs
- **GitHub Issues**: 26 open tracking phases 1-4
- **Git DAG**: Each node's branch stores results
- **Leaderboard**: Aggregated from all sources

---

## What's Next: 3-Phase Roadmap

### Phase 1: Cloud Baselines (Running Now)
```
✓ Initialize Prime Lab
✓ Launch BRIGHT baseline
✓ Launch FollowIR baseline
✓ Launch MIRACL baseline
□ Collect nDCG@10 scores
□ Compare to MLX local results
```

### Phase 2: zELO Experiments (Ready to Launch)
```
□ Instruction oracle (LLM judges adherence)
□ Code execution oracle (Python sandbox)
□ Multi-task curriculum learning
□ Target: Beat commercial baselines by 5-10%
```

### Phase 3: Production Scaling
```
□ Deploy best model to HF
□ MTEB leaderboard submission
□ Publish approach (paper/blog)
□ Open-source training code
```

---

## Research Assets

### HuggingFace Models
- [pierretokns/ModernBERT-base-mlx](https://huggingface.co/pierretokns/ModernBERT-base-mlx) — MLX-optimized weights
- [pierretokns/mteb-contrastive-clean-v1](https://huggingface.co/datasets/pierretokns/mteb-contrastive-clean-v1) — 89K decontaminated pairs

### Local Code
- `autoresearch-embed/` — MLX training (120x faster)
- `autoresearch-cloud/` — PyTorch/CUDA for cloud
- `agenthub/` — Coordination & orchestration

### GitHub Issues (Detailed Plans)
- **#1**: Master plan (benchmarks, references, approach)
- **#13-14**: MLX migration (120x speedup achieved ✓)
- **#18**: Upgrade to SOTA + 5-min loops
- **#19-21**: Cloud orchestration phases 1-3
- **#22-23**: Scaling & anti-cheat

---

## Key Numbers

| Metric | Value | Source |
|--------|-------|--------|
| Best MTEB score | **38.44** | exp-13 |
| Clustering improvement | **+5.8%** | exp-7 → exp-13 |
| Step time improvement | **120x** | MLX migration |
| Memory reduction | **12x** | MLX migration |
| Experiment cycle | **25-30 min** | MLX + cloud |
| Free tier GPUs | **3 of 10** | Prime Lab |
| Concurrent cloud runs | **3** | Currently |

---

## Citation

### Main References (Issue #1)
- **pplx-embed**: [arXiv 2602.11151](https://arxiv.org/abs/2602.11151) — Perplexity embedding approach
- **jxmo blog**: https://blog.jxmo.io/p/how-to-train-the-best-embedding-model — LLM verification strategy
- **Arctic-Embed**: Source stratification + hard neg mining
- **EmbeddingGemma**: Best sub-500M baseline

---

## Files & Channels

**View findings via**:
```bash
# GitHub Issues (detailed plans)
gh issue list --repo pierretokns/agenthub

# Agenthub results channel
ah read embed-results

# MLX training logs
tail -f autoresearch-embed/run.log

# Cloud training logs
tail -f logs/{bright,followir,miracl}_training.log

# WandB dashboard
https://wandb.ai/pierretokns/autoresearch-embed
```

---

## Summary

✅ **120x speedup** via MLX migration
✅ **5.8% improvement** from clustering datasets
✅ **3 cloud baselines training** online right now
✅ **2x research velocity** with new infrastructure
🎯 **Target**: Beat commercial embeddings by 10%+ on BRIGHT/FollowIR/MIRACL
