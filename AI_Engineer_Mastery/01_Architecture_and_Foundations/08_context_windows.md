# Context Windows — Engineering and Limitations

## What Is a Context Window?

The context window is the **total number of tokens** an LLM can process in a single request — including your system prompt, retrieved context, conversation history, user query, AND the model's response.

```
┌─────────────────────── CONTEXT WINDOW (128K tokens) ───────────────────────┐
│                                                                             │
│  [System Prompt]  [Retrieved Context]  [Chat History]  [User Query]  [Response]
│     ~500 tokens     ~3000 tokens       ~2000 tokens    ~100 tokens    ~2000 tokens
│                                                                             │
│  Total used: ~7,600 tokens out of 128,000 available                        │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Context Window Sizes (2024-2025)

| Model | Context Window | ~English Pages | Cost Impact |
|-------|---------------|----------------|-------------|
| GPT-4o | 128K | ~200 pages | Full price per token |
| GPT-4o-mini | 128K | ~200 pages | 1/30th the cost of GPT-4o |
| Claude 3.5 Sonnet | 200K | ~320 pages | Competitive pricing |
| Gemini 1.5 Pro | 1M-2M | ~1600-3200 pages | Largest available |
| Llama 3.1 | 128K | ~200 pages | Free (self-hosted) |
| Mistral Large | 128K | ~200 pages | Competitive pricing |

---

## Why Long-Context Quality Can Degrade

### The "Lost in the Middle" Problem

Research (Liu et al., 2023) showed that LLMs perform worst when relevant information is in the **middle** of a long context:

```
RECALL ACCURACY BY POSITION (10-document retrieval):

Position 1 (start):   ████████████████████  95%
Position 2:           ████████████████████  92%
Position 3:           ███████████████       78%
Position 4:           ██████████████        72%
Position 5 (middle):  ██████████            55%  ← WORST
Position 6:           ██████████████        70%
Position 7:           ███████████████       75%
Position 8:           ████████████████      80%
Position 9:           ████████████████████  90%
Position 10 (end):    ████████████████████  93%

KEY INSIGHT: Models strongly prefer information at the START and END.
Middle content is partially "forgotten."
```

### Attention Dilution

With 128K tokens, each token's attention is distributed across 128,000 positions. Even with multi-head attention, finding the 50 relevant tokens among 128,000 is hard.

```
Short context (2K tokens):   attention per token ≈ 1/2000 = 0.05%
Long context (128K tokens):  attention per token ≈ 1/128000 = 0.0008%

The "signal" of relevant tokens gets diluted 64x.
```

### Quality vs Length Tradeoff

```
RULE OF THUMB:
  - 0-4K tokens:   Full quality. Model processes everything well.
  - 4K-32K tokens: Good quality. Minor attention dilution.
  - 32K-128K:      Noticeable degradation for precise tasks.
  - 128K+:         Useful for scanning/summarization, but
                   don't rely on it for finding specific facts.
```

---

## Production Strategies

### Strategy 1: Don't Fill the Context Window

```
WRONG approach:
  "We have a 128K context window, so let's stuff all 50 retrieved chunks in!"
  
RIGHT approach:
  "Retrieve 50 candidates, rerank to top 5, send only the top 5."
  
Quality is better with 5 highly relevant chunks than 50 mixed-quality chunks.
```

### Strategy 2: Put Important Content First

```
PROMPT STRUCTURE (optimized for attention):

  [System prompt]           ← Start (high attention)
  [Most important context]  ← Near the start
  [Supporting context]      ← Middle (lower attention)
  [User query]              ← End (high attention)

  Some teams repeat the key instruction at the END:
  "Remember: answer ONLY based on the provided context."
```

### Strategy 3: Context Compression

Instead of sending 10,000-token chunks, compress them:

```
BEFORE compression (3000 tokens):
  "The company was founded in 1992 by John Smith in a small office in 
   San Francisco. Over the years, it grew to become one of the largest...
   [2500 tokens of history]...
   The return policy allows returns within 30 days of purchase for a 
   full refund. Software products are excluded from this policy."

AFTER compression (50 tokens):
  "Return policy: 30-day full refund. Software products excluded."

Same answer quality, 98% fewer tokens.
```

### Strategy 4: Sliding Window for Long Documents

```
For a 500-page book (600K tokens):

  DON'T: try to fit it all in one context window
  
  DO: Process in overlapping windows:
    Window 1: pages 1-100 + query → partial answer
    Window 2: pages 80-180 + query → partial answer
    Window 3: pages 160-260 + query → partial answer
    ...
    Final: combine all partial answers → synthesize
    
  This is the "map-reduce" pattern for long documents.
```

---

## Token Budget Management

### The Calculation

```python
MAX_CONTEXT = 128000  # model limit

system_tokens = count_tokens(system_prompt)      # fixed: ~300
few_shot_tokens = count_tokens(examples)         # fixed: ~500
history_tokens = count_tokens(conversation)      # variable: 0-5000
context_tokens = count_tokens(retrieved_chunks)  # variable: 0-10000
query_tokens = count_tokens(user_query)          # variable: 50-500

used = system_tokens + few_shot_tokens + history_tokens + context_tokens + query_tokens
available_for_response = MAX_CONTEXT - used

# SAFETY MARGIN: leave 10% buffer
max_response = min(4096, int(available_for_response * 0.9))
```

### Conversation History Management

```
Problem: conversation history grows unbounded.
After 50 messages, history = 15,000 tokens → eating into context budget.

Solutions:
  1. Sliding window: keep only last N messages
  2. Summarization: periodically summarize old messages into ~200 tokens
  3. Hybrid: keep last 5 messages + summary of older ones
  4. Hard cap: truncate history when it exceeds budget
```

---

## When to Use Large Context vs RAG

| Scenario | Large Context | RAG |
|----------|--------------|-----|
| Analyze a single long document | ✅ Better | ❌ Over-engineered |
| Search across 10,000 documents | ❌ Can't fit | ✅ Designed for this |
| Maintain conversation history | ✅ Natural | ❌ Awkward |
| Need citations / sources | ❌ No built-in tracking | ✅ Chunks = sources |
| Summarize a book | ✅ If it fits | ⚠️ Possible with map-reduce |
| Answer specific questions | ⚠️ Lost-in-middle risk | ✅ Precise retrieval |

> **Production rule**: Use RAG for precision. Use large context for analysis. Use both when you need precision + broad understanding.
