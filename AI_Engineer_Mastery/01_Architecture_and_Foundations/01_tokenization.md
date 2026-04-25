# Tokenization — How LLMs Read Text

## The Core Intuition

Computers cannot read English. They understand numbers. **Tokenization is the bridge** — it converts raw text into a sequence of integer IDs that an LLM can process.

But here's what the simple definition misses: how you tokenize fundamentally shapes everything about model performance, cost, vocabulary size, efficiency, and even which languages your model handles well.

---

## The Three Approaches

### 1. Word-Level Tokenization

```
"Hello world" → [Hello] [world]
```

- Simple but vocabulary explodes (every word form = separate token)
- "unbelievably" is unknown if not in vocabulary
- Requires massive vocabulary (300K+ entries)
- **Verdict**: Abandoned by modern LLMs

### 2. Character-Level Tokenization

```
"Hi" → [H] [i]
```

- Tiny vocabulary (256 characters)
- Sequences become impossibly long (1000-word doc = 5000+ tokens)
- No semantic grouping — 'H' means nothing alone
- **Verdict**: Too slow, no semantic meaning

### 3. Subword Tokenization (BPE) ✅

```
"tokenization" → [token] [ization]
```

- Best of both worlds — manageable vocab, handles rare words
- Used by GPT-2, GPT-3, GPT-4, Llama, Mistral, Claude
- Vocabulary size: 32K–100K tokens
- **Verdict**: The industry standard

---

## Byte-Pair Encoding (BPE) — The Algorithm

BPE is the dominant tokenization strategy. Here's how it works:

### Step-by-Step

```
1. START WITH CHARACTERS
   Every character becomes a token.
   "low" = [l][o][w]

2. COUNT ALL ADJACENT PAIRS
   In "low lower lowest", find most common pair.
   Maybe "lo" appears 3 times.

3. MERGE MOST FREQUENT PAIR
   "lo" becomes a single token.
   Repeat on the merged corpus.

4. REPEAT UNTIL VOCAB SIZE REACHED
   GPT-4 stops at ~100,000 tokens.
   You now have a vocabulary of the most useful subwords.
```

### Worked Example

```
TEXT: "lower"
Step 1: [l][o][w][e][r]       — Start with chars
Step 2: [lo][w][e][r]         — Merge "l"+"o" (most frequent)
Step 3: [lo][we][r]           — Merge "w"+"e"
Step 4: [low][er]             — Merge "lo"+"w"
Result: 2 tokens instead of 5!
```

---

## How Tokenization Affects Cost, Context, and Truncation

### Cost Impact

Every API call is billed per token. The same text can cost wildly different amounts depending on the tokenizer:

| Text | Tokens (GPT-4) | Tokens (Llama) | Why Different |
|------|----------------|-----------------|---------------|
| "Hello world" | 2 | 2 | Common words → single tokens |
| "bureaucracy" | 3 | 4 | Rare words → more subwords |
| Python code | ~0.7× English | ~0.8× English | Code has repetitive patterns BPE captures efficiently |
| Thai text | ~3× English | ~4× English | Non-Latin scripts tokenize poorly in English-centric models |
| JSON/XML | ~0.6× English | ~0.7× English | Structural tokens are common in training data |

> **Rule of thumb**: 1 token ≈ 0.75 English words. "The quick brown fox" = 4 words ≈ 4 tokens.

### Context Window Usage

If your context window is 128K tokens:
- English text: ~96K words ≈ ~200 pages
- Chinese text: ~40K characters ≈ ~50 pages (each char = 2-3 tokens)
- Code: more efficient, ~130K words equivalent

### Truncation

When input exceeds the context window, it's **truncated** — the model simply doesn't see the rest. This is why token counting before sending is critical.

```python
import tiktoken

# Always count tokens before sending to API
enc = tiktoken.encoding_for_model("gpt-4o")
tokens = enc.encode(my_text)
if len(tokens) > 125000:
    # Truncate or chunk the text
    my_text = enc.decode(tokens[:125000])
```

---

## Tokenizer Comparison

| Tokenizer | Used By | Vocab Size | Approach |
|-----------|---------|-----------|----------|
| `cl100k_base` | GPT-4, GPT-4o | 100,256 | BPE |
| `o200k_base` | GPT-4o-mini | 200,019 | BPE |
| SentencePiece | Llama, Gemma, T5 | 32,000-256,000 | Unigram/BPE hybrid |
| WordPiece | BERT, DistilBERT | 30,522 | Greedy longest-match |
| Tiktoken | OpenAI models | Varies | Rust BPE implementation |

---

## What Interviewers Actually Test

| Question | Key Point |
|----------|-----------|
| How many tokens is "ChatGPT"? | 2 tokens: "Chat" + "GPT" — not intuitive |
| Why does Python code cost fewer tokens than English? | Code has repetitive patterns BPE captures efficiently |
| Why do APIs charge by token not word? | Token is the compute unit — one forward pass per token generated |
| Why is tokenization bad for arithmetic? | "1000000" may be 1-4 tokens, numbers have no semantic grouping |
| Why do non-English languages cost more? | Underrepresented in training data → less efficient subword merges |

---

## Production Reality

### ✅ Best Practices

- Always use `tiktoken` (OpenAI) or `tokenizers` (HuggingFace) to estimate token counts before sending to API — avoid surprise costs
- Always set `max_tokens` in API calls to prevent runaway generation
- For multilingual apps: test token counts in each target language — costs vary dramatically
- Pre-compute token counts for your prompt templates to budget accurately

### ⚠️ Common Mistakes

- Never count "words" to estimate tokens. "bureaucracy" = 1 word but 3-4 tokens. Use the actual tokenizer.
- Don't assume all models tokenize the same way. GPT-4 and Llama have completely different vocabularies.
- Don't forget that both input AND output tokens count toward cost and context limits.

---

## Tools

| Tool | What It Does |
|------|-------------|
| **tiktoken** | OpenAI's tokenizer library (Python), exact token count for GPT models |
| **HuggingFace tokenizers** | Fast Rust implementation, works for all HF models |
| **platform.openai.com/tokenizer** | Visual tokenizer to see exactly how text splits |
| **SentencePiece** | Used by Google models (T5, PaLM), Llama series |

---

## How It's Used in a Real AI App

In a RAG pipeline:
1. **Ingestion**: Count tokens per chunk to ensure chunks fit within embedding model's max sequence length (512 tokens for most)
2. **Retrieval**: Count tokens of retrieved context to stay within LLM's context window
3. **Generation**: Set `max_tokens` for the response to control cost
4. **Cost tracking**: Log input/output tokens per request for billing dashboards

```python
# Production pattern: budget tokens before LLM call
system_tokens = count_tokens(system_prompt)      # e.g., 200
context_tokens = count_tokens(retrieved_chunks)   # e.g., 3000
user_tokens = count_tokens(user_query)            # e.g., 50
available_for_response = 128000 - system_tokens - context_tokens - user_tokens  # 124,750

response = client.chat.completions.create(
    model="gpt-4o",
    max_tokens=min(4096, available_for_response),  # cap response length
    messages=[...]
)
```
