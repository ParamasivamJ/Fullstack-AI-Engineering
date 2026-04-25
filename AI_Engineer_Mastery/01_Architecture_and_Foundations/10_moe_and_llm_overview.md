# Mixture of Experts (MoE) & LLM Overview

## Mixture of Experts

Instead of using ALL parameters for every token, route each token to a subset of specialized "expert" networks.

```
Token → Router (small network) → selects top-2 experts out of 8
  Expert 1: processes token
  Expert 3: processes token
  Output: weighted combination of both expert outputs
```

### Why MoE Matters
- GPT-4 is rumored to be 8×220B MoE = 1.76T total params, but only ~220B active per token
- Mixtral 8x7B: 47B total params, 13B active per token
- **Result**: Large model quality at small model inference cost

### Tradeoffs
- ✅ Better quality per FLOP
- ✅ Faster inference (only subset of params active)
- ✗ More total memory (all experts in VRAM)
- ✗ Load balancing: some experts get overused
- ✗ Harder to fine-tune

---

## Large Language Models — Complete Overview

### What Makes an LLM "Large"?
- Parameters: 7B to 1T+
- Training data: 1T to 15T+ tokens
- Training compute: thousands of GPU-hours

### The Scaling Laws
```
Performance improves predictably with:
  1. More parameters (model size)
  2. More training data
  3. More compute

Chinchilla insight (2022):
  Optimal: train a SMALLER model on MORE data
  Rather than: train a HUGE model on less data
  
  70B model trained on 1.4T tokens > 280B model trained on 300B tokens
```

### LLM Failure Modes

| Failure | Description | Mitigation |
|---------|-------------|------------|
| Hallucination | Generates false facts confidently | RAG, citations, low temp |
| Overconfidence | No uncertainty expression | Calibration, confidence scoring |
| Refusal | Over-refuses valid requests | Prompt tuning, safety threshold |
| Prompt injection | User manipulates system behavior | Input/output guardrails |
| Context overflow | Input too long, content truncated | Token counting, chunking |
| Inconsistency | Different answers to same question | Temperature=0, caching |
