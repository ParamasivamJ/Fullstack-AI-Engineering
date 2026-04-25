# Greedy vs Beam Search — Decoding Strategies

## What Is Decoding?
An LLM outputs probabilities over 50,000+ tokens. Decoding picks which token to generate.

## Greedy: Pick the highest probability token at each step.
Fast, simple, often suboptimal. Can get stuck in repetitive loops.

## Beam Search: Keep top-K candidates (beams) at each step.
Better global coherence. K=3-5 typical. Score = log-probability / length^α.

## Sampling: Randomly sample from the distribution.
Add temperature, top-k, top-p for control. Used by chat models.

| Property | Greedy | Beam (k=5) | Sampling |
|----------|--------|-----------|----------|
| Speed | Fastest | k× slower | Fast |
| Quality | Locally optimal | Better coherence | Variable |
| Creativity | Zero | Low | High |
| Best for | Classification | Translation | Chat, creative |

## Modern LLMs (GPT-4, Claude) use sampling, not beam search for chat.
Beam search finds high-probability text, but high probability ≠ natural conversation.
