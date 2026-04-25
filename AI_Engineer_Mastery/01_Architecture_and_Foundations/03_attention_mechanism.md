# Attention Mechanism — Complete Intuition

## The Core Intuition

Attention answers one question: **"When processing this word, how much should I focus on every other word in the sentence?"**

Before attention, models processed words left-to-right, gradually forgetting earlier words. Attention lets the model look at ALL words simultaneously and decide which ones matter most for the current word.

```
"The cat sat on the mat because it was tired"

When processing "it":
  → "cat" gets HIGH attention (it refers to the cat)
  → "mat" gets LOW attention (it doesn't refer to the mat)
  → "tired" gets MEDIUM attention (related to the state of "it")
```

---

## Self-Attention Step by Step

### The Three Vectors: Query, Key, Value

For every token in the input, we create three vectors:

```
Token: "cat"
  Query (Q): "What am I looking for?"     → [0.2, 0.8, -0.1, ...]
  Key (K):   "What do I contain?"          → [0.9, 0.3, 0.5, ...]
  Value (V): "What information do I carry?" → [0.1, 0.7, 0.4, ...]
```

These are created by multiplying the token's embedding by three learned weight matrices: Wq, Wk, Wv.

### The Computation

```
Step 1: Compute attention scores
  score(i,j) = Qᵢ · Kⱼ / √dₖ
  
  This dot product measures how well Query i "matches" Key j.
  Division by √dₖ prevents scores from getting too large (dₖ = key dimension).

Step 2: Softmax to get weights
  weights = softmax(scores)
  
  Converts raw scores to probabilities that sum to 1.
  High score → high weight → "pay attention to this token"

Step 3: Weighted sum of Values
  output = Σ(weightⱼ × Vⱼ)
  
  Each token's output is a weighted combination of ALL value vectors.
  Tokens with high attention weight contribute more.
```

### Full Equation

```
Attention(Q, K, V) = softmax(Q × Kᵀ / √dₖ) × V

Where:
  Q = queries matrix (all tokens' queries stacked)
  K = keys matrix
  V = values matrix
  dₖ = dimension of keys (e.g., 64)
  
Output: same shape as input, but each token now "knows about" all other tokens.
```

---

## Why √dₖ Scaling?

Without scaling, the dot products grow with dimension size:

```
If dₖ = 64:
  Random dot products have variance ≈ 64
  Some scores become very large (e.g., 20+)
  softmax(20) ≈ 1.0, softmax(-20) ≈ 0.0
  → Attention becomes one-hot (only looks at ONE token)
  → Gradients vanish for all other tokens

With scaling (÷ √64 = ÷ 8):
  Scores stay in reasonable range (-3 to +3)
  softmax produces distributed weights
  → Attention can focus on MULTIPLE tokens
  → Gradients flow to all relevant tokens
```

---

## Multi-Head Attention

Instead of one set of Q, K, V, use **multiple heads** (typically 8-96) running in parallel:

```
HEAD INTUITION:
  Head 1: focuses on syntactic relationships (subject-verb)
  Head 2: focuses on co-reference ("it" → "cat")
  Head 3: focuses on adjacent tokens (local context)
  Head 4: focuses on semantic similarity
  ...each head learns a different "type" of attention

COMPUTATION:
  For each head h:
    Qₕ = X × Wqₕ    (project to smaller dimension: d_model/num_heads)
    Kₕ = X × Wkₕ
    Vₕ = X × Wvₕ
    headₕ = Attention(Qₕ, Kₕ, Vₕ)
  
  Concatenate all heads: MultiHead = [head₁; head₂; ...; headₙ]
  Final projection: output = MultiHead × Wₒ
```

### Why Multiple Heads?

One head can only attend to one "pattern." Multiple heads attend to different patterns simultaneously:

```
"The animal didn't cross the street because it was too tired"

Head 1 (co-reference): "it" → high attention on "animal"
Head 2 (causal):       "tired" → high attention on "didn't cross"
Head 3 (positional):   each word → high attention on adjacent words
```

---

## Attention Patterns in Practice

| Pattern | What It Looks Like | Why It Matters |
|---------|-------------------|----------------|
| Diagonal | Each token attends to itself | Self-identity (baseline) |
| Vertical stripes | All tokens attend to a few key tokens | Important structural tokens (e.g., [CLS], punctuation) |
| Block diagonal | Tokens attend to nearby tokens | Local context / phrase structure |
| Long-range | Distant tokens attend to each other | Co-reference, long-range dependencies |

---

## Attention in Different Architectures

```
ENCODER (BERT): Bidirectional self-attention
  Every token can attend to EVERY other token (past AND future).
  Used for: classification, NER, embeddings.

DECODER (GPT): Causal (masked) self-attention
  Each token can only attend to PREVIOUS tokens (not future).
  Used for: text generation (can't peek at what comes next).

ENCODER-DECODER (T5): Cross-attention
  Decoder tokens attend to ENCODER outputs.
  Used for: translation, summarization.
```

### Causal Masking

```
For "The cat sat":

         The  cat  sat
  The  [  ✓    ✗    ✗  ]   ← "The" can only see itself
  cat  [  ✓    ✓    ✗  ]   ← "cat" sees "The" and itself
  sat  [  ✓    ✓    ✓  ]   ← "sat" sees everything before it

Future tokens are masked with -∞ before softmax → attention weight = 0.
```

---

## KV Cache — The Speed Trick

During generation, previously computed keys and values don't change. Caching them avoids recomputation:

```
WITHOUT KV CACHE (naive):
  Generate token 1: compute attention over [token1]
  Generate token 2: recompute attention over [token1, token2]
  Generate token 3: recompute attention over [token1, token2, token3]
  ...token 1000: recompute over all 1000 tokens. O(n²) total.

WITH KV CACHE:
  Generate token 1: compute K1, V1, cache them
  Generate token 2: compute K2, V2, look up K1,V1 from cache
  Generate token 3: compute K3, V3, look up K1-2 from cache
  ...only compute attention for the NEW token against cached K,V.
  
  Speedup: ~10-50x for long sequences.
  Cost: memory for storing all cached K,V vectors.
```

---

## Production Concerns

### Memory Usage

Attention has O(n²) memory complexity where n = sequence length:
- 4K context: manageable
- 32K context: significant
- 128K context: requires specialized techniques (Flash Attention, sliding window)

### Flash Attention

A memory-efficient implementation that reduces attention from O(n²) memory to O(n):

```
Standard attention: materialise the full n×n attention matrix → huge memory
Flash Attention: compute attention in blocks, never materialise the full matrix
  → Same result, 2-4x faster, 5-20x less memory
  → Used by virtually all modern LLM serving frameworks
```

### Grouped Query Attention (GQA)

Modern optimisation used in Llama 2/3, Mistral:

```
Standard: each head has its own Q, K, V
GQA: multiple query heads share the same K, V
  → Reduces KV cache size by 4-8x
  → Minimal quality loss
  → Enables longer context at lower cost
```

---

## Tradeoffs

| Concern | Impact | Mitigation |
|---------|--------|------------|
| O(n²) complexity | Limits context length | Flash Attention, sliding window |
| KV cache memory | Grows linearly with context | GQA, quantized KV cache |
| Attention quality degrades with distance | Long-range dependencies weaker | RoPE, ALiBi positional encodings |
| Computational cost | Dominates inference latency | Speculative decoding, attention pruning |
