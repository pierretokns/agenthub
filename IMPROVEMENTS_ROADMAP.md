# Improvements Roadmap: OpenEnv RL + MTEB Optimization

**Status:** Phase 1-2 implementation complete. Phase 3-6 planning.

---

## Phase 4: Quick Wins (Week 2-3)

### 4.1: Enhanced Logging & Observability
```python
# Already in autonomous_researcher.py but can enhance:
- Add structured logging (JSON) for easy parsing
- Export metrics to Prometheus/Grafana endpoint
- Real-time Slack/Discord notifications on plateau or contamination
- Leaderboard web dashboard (simple Flask app)
```

**Time:** 4-6 hours
**Impact:** Better visibility into autonomous runs
**Owner:** Claude Code agent

### 4.2: Leaderboard Dashboard
Simple web UI showing:
- Current score per dataset
- Historical trend (plot)
- Contamination status (green/red)
- Estimated time to next run
- Latest git commits

**Time:** 6-8 hours
**Implementation:**
```bash
# Quick Flask + plotly app
flask app at: scripts/leaderboard_server.py
Run: python3 scripts/leaderboard_server.py
Access: http://localhost:5000/leaderboard
```

### 4.3: Metrics Export
Export to wandb/tensorboard for long-term tracking:
```python
# In autonomous_researcher.py:
- Log each run to wandb
- Export leaderboard as wandb artifact
- Compare runs with wandb parallel coordinates
```

**Time:** 2-3 hours
**Setup:** `wandb login` with HF API key

### 4.4: Ablation Testing Framework
When plateau detected, automatically test small variations:
```python
# Add to autonomous_researcher.py:
- Lower learning rate (-20%)
- Different batch size
- Different LoRA alpha
- Different sampling temperature
# Just set env vars, no code changes needed
```

**Time:** 3-4 hours
**Impact:** Escape plateaus without manual intervention

---

## Phase 5: Medium-Term Improvements (Week 3-4)

### 5.1: Multi-Environment Orchestration
Run multiple environments in parallel:
```bash
# Start 3 concurrent runs (one per dataset)
prime rl run configs/bright_baseline.toml &
prime rl run configs/followir_baseline.toml &
prime rl run configs/miracl_baseline.toml &
wait
```

**Time:** 4 hours (mostly orchestration logic)
**Impact:** 3x faster exploration (12h → 4h per full cycle)
**Risk:** Higher cost (3x compute)

### 5.2: Dataset Augmentation Pipeline
Automatically create new training data from top-performing models:
```python
# Process:
1. Train model on BRIGHT → score 65
2. Use that model to generate synthetic queries on FollowIR
3. Use those synthetic queries for next run on MIRACL
4. Measure improvement (synthetic data boosts signal?)
```

**Time:** 8-10 hours
**Impact:** Potential +5-10 points on plateau
**Reference:** jxmo blog on synthetic data quality

### 5.3: Contamination Deep Dive
If any run hits contamination, investigate root cause:
```python
# Add to autonomous_researcher.py:
- Extract exact overlapping documents
- Analyze which MTEB test sets are problematic
- Mark specific data regions as risky
- Exclude those regions from training
```

**Time:** 6 hours
**Impact:** Safety + learning which datasets are truly clean

### 5.4: Checkpoint Management
Save model checkpoints at key milestones:
```bash
# After each run, export model:
prime rl checkpoints <run-id> --save-model model-v{N}.safetensors
# Track which checkpoint achieved highest score
```

**Time:** 2 hours
**Impact:** Can rollback to best model, resume from checkpoint

---

## Phase 6: Advanced Improvements (Week 4+)

### 6.1: Ensemble Methods
Combine multiple model architectures:
```python
# Train on different:
- Learning rates (1e-5, 2e-5, 5e-5)
- Model sizes (0.6B, 0.9B, 1.3B)
- Datasets (BRIGHT + FollowIR + MIRACL)
# Then ensemble predictions at eval time
```

**Time:** 12-16 hours (spread over 2 weeks)
**Impact:** Potential +10-15 points (SOTA territory)
**Reference:** EmbeddingGemma uses ensembles

### 6.2: Hard Negative Mining
Actively select the hardest negative examples:
```python
# For each query, find hardest negative:
1. Rank all passages by model score
2. Take top-k (95-99th percentile) as hard negatives
3. Use those for next training iteration
```

**Time:** 8 hours
**Impact:** Better convergence, +5-8 points
**Reference:** Arctic-Embed paper

### 6.3: Multi-Stage Training Pipeline
Replicate pplx-embed's approach:
```
Stage 1: Warmup (random contrastive) - 100 steps
Stage 2: Main training (hard negatives) - 5000 steps
Stage 3: Fine-tuning (in-batch negatives) - 5000 steps
```

**Time:** 6 hours (orchestration)
**Impact:** Smoother convergence, +3-5 points
**Note:** Requires modifying config/reward logic

### 6.4: Multilingual Optimization
Explore all MIRACL languages in parallel:
```python
# When score >= 70:
for lang in ["es", "fr", "de", "pt", "zh", "ar", "ja", "ko"]:
    os.environ["MIRACL_LANGUAGE"] = lang
    prime rl run configs/miracl_baseline.toml &
# Run 8 languages concurrently
```

**Time:** 4 hours (logic)
**Impact:** Find best multilingual signal, +2-5 points per lang

### 6.5: Publication-Ready Pipeline
Document findings for arxiv/conference:
```markdown
# Expected paper structure:
1. Abstract (SOTA: 77.3 on MTEB v0.3)
2. Methods (RL-driven dataset selection)
3. Results (leaderboard_final.tsv with 50+ runs)
4. Ablations (phase 4-5 experiments)
5. Reproducibility (configs, docker, code)
```

**Time:** 8-10 hours
**Deliverables:**
- `paper.md` → PDF with tables/plots
- `leaderboard_final.tsv` (all runs)
- `ablations.md` (systematic study)
- Code committed + tagged as v1.0-sota

---

## Timeline & Milestones

| Phase | Target | Effort | Expected Score | Dependencies |
|-------|--------|--------|-----------------|--------------|
| **1** | Today | 2h | — | Podman setup |
| **2** | Tomorrow | 1-4h | 55-65 | Phase 1 ✅ |
| **3** | Week 1 | 48h | 60-70 | Phase 2 ✅ |
| **4** | Week 2-3 | 20-25h | 65-72 | Phase 3 ✅ |
| **5** | Week 3-4 | 30-40h | 70-76 | Phase 4 ✅ |
| **6** | Week 4+ | 40-50h | 76-80+ | Phase 5 ✅ |

---

## Priority Ranking

### High (Do ASAP)
1. **Phase 3:** Autonomous agent running 24/7 (critical path)
2. **Phase 4.2:** Leaderboard dashboard (visibility)
3. **Phase 4.4:** Ablation testing (escape plateaus)
4. **Phase 5.2:** Synthetic data generation (unlock better signal)

### Medium (Do when plateau detected)
1. **Phase 5.3:** Contamination investigation (safety)
2. **Phase 6.2:** Hard negative mining (efficiency)
3. **Phase 6.1:** Ensemble methods (accuracy)

### Low (Nice to have)
1. **Phase 4.3:** Metrics export (observability)
2. **Phase 6.3:** Multi-stage training (fine-tuning)
3. **Phase 6.4:** Multilingual sweep (exploration)
4. **Phase 6.5:** Publication pipeline (documentation)

---

## Success Criteria

- [ ] **Phase 4:** Score ≥65 on ≥1 dataset, all runs < 2h turnaround
- [ ] **Phase 5:** Score ≥72 from 20+ clean runs, no contamination
- [ ] **Phase 6:** Score ≥76+ SOTA territory, publication-ready ablations

---

## Estimated Cost

| Phase | GPU Hours | Approx Cost |
|-------|-----------|------------|
| 1-2 | 6 | $12 |
| 3 | 48 | $96 |
| 4 | 20 | $40 |
| 5 | 100 | $200 |
| 6 | 200+ | $400+ |
| **Total** | **374+** | **$748+** |

*Assuming $2/GPU-hour on Prime Intellect. Might be lower with credits/partnership.*

---

## Next Step: Phase 4 Quick Wins

Once Phase 2-3 are complete:

```bash
# Start Phase 4.1: Enhanced logging
python3 -c "
import scripts.autonomous_researcher as ar
# Add JSON logging format
# Add slack integration
"

# Start Phase 4.2: Leaderboard dashboard
python3 scripts/leaderboard_server.py &
open http://localhost:5000/leaderboard

# Start Phase 4.4: Ablation testing
# Modify autonomous_researcher.py to trigger ablations on plateau
```

---

## Notes

- All phases assume no major bugs in Prime Labs RL infrastructure
- Timeline assumes 1 human developer (Claude Code agent)
- Costs are estimate; actual may be lower with optimization
- SOTA target of 76+ is ambitious; 72+ is realistic/achievable
- Publication assumes results are truly novel (not just reproducing existing work)

See: `AUTONOMOUS_RESEARCH_PROTOCOL.md` for Phase 3 detailed roadmap.
