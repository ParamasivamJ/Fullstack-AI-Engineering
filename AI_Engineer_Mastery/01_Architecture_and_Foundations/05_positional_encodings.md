# Positional Encodings — How Models Know Word Order

## The Problem
Self-attention treats input as a **set** — it has no notion of order. "The cat sat on the mat" and "mat the on sat cat the" produce identical attention patterns without positional information.

## Sinusoidal (Original Transformer)
```
PE(pos, 2i) = sin(pos / 10000^(2i/d))
PE(pos, 2i+1) = cos(pos / 10000^(2i/d))
```
Unique pattern for each position. Fixed. Works for any sequence length.

## Learned Positional Embeddings (BERT, GPT-2)
Train a separate embedding for each position (1, 2, 3, ..., max_seq).
Simple but limited to max trained sequence length.

## RoPE — Rotary Position Embedding (Llama, Mistral) ⭐
Rotates query and key vectors by their position angle. Relative position encoded in the dot product.
**Why dominant**: extends naturally to longer sequences, captures relative distance.

## ALiBi — Attention with Linear Biases (BLOOM)
Subtracts a linear penalty from attention scores based on distance. Closer tokens → higher attention. No extra parameters.

---

## Comparison

| Method | Extends Beyond Training Length? | Relative Position? | Used By |
|--------|-------------------------------|-------------------|---------|
| Sinusoidal | ✅ Yes | ❌ No | Original Transformer |
| Learned | ❌ No | ❌ No | BERT, GPT-2 |
| RoPE | ✅ Yes (with NTK scaling) | ✅ Yes | Llama, Mistral, Qwen |
| ALiBi | ✅ Yes | ✅ Yes | BLOOM, MPT |
