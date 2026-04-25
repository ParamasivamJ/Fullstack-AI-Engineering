# Transformer Architecture — Why Transformers Won

## Before Transformers: The Problem with RNNs

RNNs processed text one token at a time, sequentially. This had two fatal flaws:
1. **No parallelization**: Token N must wait for tokens 1 through N-1
2. **Vanishing gradients**: Information from early tokens fades by token 500

## The Transformer (2017, "Attention Is All You Need")

Processes ALL tokens simultaneously using self-attention. No recurrence needed.

```
INPUT: "The cat sat on the mat"
  ↓ (all tokens processed in parallel)
[Embedding Layer]       ← convert tokens to vectors
[Positional Encoding]   ← add position information
[Self-Attention × N]    ← each token attends to all others
[Feed-Forward × N]      ← process each token independently
[Output Layer]          ← predict next token or classify
```

### Key Components
- **Self-Attention**: See `03_attention_mechanism.md`
- **Feed-Forward Network**: Two linear layers with ReLU between
- **Layer Normalization**: Stabilizes training
- **Residual Connections**: Skip connections prevent gradient vanishing
- **Positional Encoding**: Sinusoidal or learned position information

### Encoder vs Decoder

| Component | Sees | Used For | Examples |
|-----------|------|----------|----------|
| Encoder | All tokens (bidirectional) | Understanding | BERT, RoBERTa |
| Decoder | Only past tokens (causal mask) | Generation | GPT, Llama |
| Both | Cross-attention between them | Translation | T5, BART |

## Why Transformers Won
1. **Parallelizable**: Train on GPUs efficiently (100x faster than RNNs)
2. **Long-range dependencies**: Attention connects any two positions directly
3. **Scalable**: More layers + more data = better performance (scaling laws)
4. **Transfer learning**: Pre-train once, fine-tune for many tasks
