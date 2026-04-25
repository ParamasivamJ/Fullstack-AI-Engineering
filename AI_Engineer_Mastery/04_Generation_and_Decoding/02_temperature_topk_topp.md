# Temperature, Top-K, Top-P — Sampling Parameters

## The Creativity Dial

An LLM outputs probability distributions. These three parameters reshape that distribution before sampling.

## Temperature (T)
```
P(token_i) = exp(logit_i / T) / Σ exp(logit_j / T)

T → 0:   One-hot (deterministic). Always picks highest.
T = 1:   Raw model distribution. Default.
T > 1:   Flatter. More random, more creative.
```

## Top-K
Hard limit: only consider K most probable tokens. Zero out the rest.
Problem: K=40 is context-independent. May be too many or too few.

## Top-P (Nucleus Sampling) ⭐
Dynamic cutoff: include tokens until cumulative probability ≥ P.
Confident model → few tokens. Uncertain model → many tokens. Context-sensitive.

## Production Guide

| Task | Temp | Top-P | Why |
|------|------|-------|-----|
| JSON/Code generation | 0.0-0.1 | 1.0 | Deterministic, exact |
| Factual Q&A | 0.2-0.4 | 0.9 | Mostly deterministic |
| Chat/Dialogue | 0.7-0.9 | 0.95 | Natural variety |
| Creative writing | 0.9-1.2 | 0.98 | Maximum creativity |
| Classification | 0.0 | 1.0 | Always pick best label |

## Key Rules
- Use EITHER top-k OR top-p, not both (they interact unpredictably)
- Temperature 0 = truly deterministic (same output every time)
- Most APIs default: T=1.0, top_p=1.0 (no modification)
- OpenAI recommends: adjust temperature OR top_p, not both
