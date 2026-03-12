# Retrieval Benchmark Datasets

## Production Datasets (Verified for Training)

### BRIGHT (Baseline)
- **Source:** google-research-datasets/BRIGHT
- **Config:** gpt4_reason
- **Type:** Dense retrieval with reasoning
- **Size:** 1,384 queries × 12 domains
- **Status:** ✅ Primary baseline

### FollowIR
- **Source:** jhu-clsp/FollowIR-train
- **Split:** train
- **Type:** Instruction-following retrieval
- **Size:** 1,780 examples
- **Status:** ✅ Secondary baseline

### MIRACL (English)
- **Source:** miracl/miracl
- **Language:** en
- **Split:** train
- **Type:** Multilingual cross-lingual retrieval
- **Size:** ~31K queries in English
- **Status:** ✅ Tertiary baseline

---

## Exploration Candidates (for autonomous agent)

### Tier 1: High-Signal Retrieval Benchmarks

#### ArxivQA (Mistral)
- **Source:** mistral-embed/ArxivQA
- **Size:** ~10K Q&A from arXiv papers
- **Signal:** Technical retrieval quality
- **Recommendation:** Try after BRIGHT achieves >50 reward
- **Notes:** Requires handling long documents (abstract + content)

#### NFCorpus
- **Source:** nfcorpus (via MTEB)
- **Size:** 3.2K queries
- **Signal:** Health/medical domain retrieval
- **Recommendation:** Domain-specific signal
- **Notes:** Part of MTEB evaluation suite

#### SciFact
- **Source:** scifact (via MTEB)
- **Size:** 1.1K queries
- **Signal:** Scientific fact verification
- **Recommendation:** High-quality semantic matching
- **Notes:** Part of MTEB evaluation suite

#### TREC-COVID
- **Source:** trec-covid
- **Size:** 50 queries
- **Signal:** COVID research retrieval
- **Recommendation:** Domain specialist signal
- **Notes:** Small but high-quality

### Tier 2: Synthetic/LLM-Generated

#### GPT-4 Generated (Custom)
- **Source:** Generate with Claude Haiku 4.5
- **Generator:** Query + document pairs from domain
- **Signal:** Synthetic diversity
- **Recommendation:** Fill gaps in domain coverage
- **Cost:** 1K pairs ≈ $0.01 (Haiku tier)

#### Mistral-Synthetic
- **Source:** Various Mistral-generated datasets
- **Size:** Variable
- **Signal:** Instruction-following diverse queries
- **Recommendation:** For instruction-tuned embeddings

### Tier 3: Cross-Lingual (Multilingual Signal)

#### MIRACL (Additional Languages)
- **Languages:** [ar, bn, de, en, es, fa, fi, fr, hi, id, it, ja, ko, nl, pt, ru, sw, te, th, zh]
- **Recommendation:** After English >60 reward, try high-resource languages (de, es, fr, pt, zh)
- **Notes:** Tests embedding quality in multilingual setting

#### XLWIC
- **Source:** xlwic
- **Type:** Cross-lingual word-in-context
- **Recommendation:** Low priority (WIC vs ranking)

---

## Contamination-Safe Datasets

| Dataset | MTEB Overlap Check | Status |
|---------|------------------|--------|
| BRIGHT | Already evaluated | ✅ Safe |
| FollowIR | Already evaluated | ✅ Safe |
| MIRACL | Already evaluated | ✅ Safe |
| ArxivQA | ⚠️ Check before use | Pending |
| NFCorpus | ✅ Part of MTEB test | Unsafe (circular) |
| SciFact | ✅ Part of MTEB test | Unsafe (circular) |

**Rule:** Any dataset used for training MUST be checked against MTEB test sets (see: `src/eval/contamination.py`).

---

## Agent Decision Logic

The autonomous dataset exploration agent should follow this priority:

```python
# Pseudo-code for agent
def select_next_dataset(current_score, iteration):
    if current_score < 50:
        return BRIGHT  # Optimize baseline first
    elif current_score < 60:
        return FollowIR  # Add instruction signal
    elif current_score < 70:
        return MIRACL_EN  # Add multilingual signal
    elif iteration < 10:
        return MIRACL_RANDOM_LANG  # Explore other languages
    elif current_score < 80:
        return GPT4_SYNTHETIC  # Fill gaps with synthetic
    else:
        # SOTA push: cherry-pick high-value examples from top performers
        return ENSEMBLE_BALANCED
```

---

## Example: Adding a New Dataset

To add a new dataset for autonomous exploration:

1. **Create dataset loader** in `configs/datasets/new_dataset.yaml`:
   ```yaml
   name: "new-dataset"
   source: "hf-org/dataset-name"
   split: "train"
   language: "en"  # if applicable
   contamination_check: true
   ```

2. **Register with agent** in `DATASET_INVENTORY.md` (this file)

3. **Agent runs:**
   ```bash
   export BRIGHT_DATASET=hf-org/dataset-name
   prime rl run configs/bright_baseline.toml
   ```

4. **Contamination check** happens automatically in Prime Labs RL pipeline (if integrated)

5. **Results logged** to `results.jsonl` with dataset name and contamination status

---

## Data Format Contract

All datasets must conform to this structure for the environments:

### BRIGHT-style
```json
{
  "query": "string",
  "gold_ids": ["passage_id1", ...],
  "gold_answer": "text answer",
  "reasoning": "optional"
}
```

### FollowIR-style
```json
{
  "query": "string",
  "instruction": "constraint string",
  "document": "target doc",
  "label": true/false,
  "score": 0.0-1.0
}
```

### MIRACL-style
```json
{
  "query": "string",
  "query_id": "id",
  "positive_passages": [{"docid": "...", "title": "...", "text": "..."}],
  "negative_passages": [...]
}
```

---

## Future Additions

- [ ] OpenAIEmbeddings benchmark (proprietary, reference only)
- [ ] HotpotQA multi-hop retrieval
- [ ] BEIR tasks (standardized)
- [ ] Custom domain datasets (e.g., medical, legal)
- [ ] Synthetic hard negatives via teacher model
