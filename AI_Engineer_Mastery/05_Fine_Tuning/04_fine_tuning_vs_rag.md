# Fine-Tuning vs RAG — The Decision That Defines Your Architecture

## The Core Question

Your LLM doesn't know your company's data. Two options:
- **RAG**: Retrieve relevant documents at query time
- **Fine-tuning**: Train the model on your data

---

## Decision Matrix

| Factor | Choose RAG | Choose Fine-Tuning |
|--------|-----------|-------------------|
| Knowledge changes frequently | ✅ Instant updates | ✗ Must retrain |
| Need citations | ✅ Built-in | ✗ Can't cite training sources |
| Need specific output style | ✗ Prompting has limits | ✅ Train on examples |
| Large knowledge base (100K+ docs) | ✅ Scales with vector DB | ✗ Can't fit in training |
| Need factual accuracy | ✅ Grounded in text | ✗ May hallucinate |
| Low latency needed | ✗ Retrieval adds 50-200ms | ✅ Direct inference |
| Privacy (no data to API) | ⚠️ Chunks sent to LLM | ✅ Self-hosted model |

---

## The Real Answer: Use Both

```
BASE MODEL → FINE-TUNED (style, format, tone) → RAG (current facts) → ANSWER

Fine-tune on 5,000 support transcripts → learns your tone
RAG retrieves current product docs → provides accurate facts
Result: correct tone + correct facts
```

---

## Common Misconception

> "I'll fine-tune on our docs so it knows everything."

**Wrong.** Fine-tuning teaches *patterns and style*, not *facts*. The model will sound knowledgeable but hallucinate specific details. For factual accuracy, use RAG.

---

## When Fine-Tuning Helps

1. **Output format**: Consistent JSON schema prompting can't enforce
2. **Style/tone**: Specific writing voice across all responses
3. **Reducing prompt size**: 2000-token instructions → baked into model
4. **Classification**: Fine-tuned small models match GPT-4 at 1/100th cost

---

## LoRA/QLoRA Quick Reference

```
LoRA:  Freeze base model, train tiny adapter matrices
       0.1-1% of params trainable. VRAM: 8-24GB for 7B model.

QLoRA: Quantize base to 4-bit + train LoRA adapters
       VRAM: 4-8GB. Runs on consumer GPUs (RTX 3090).

DEPLOYMENT:
  Option A: Merge LoRA → deploy as single model
  Option B: Keep separate → swap adapters per task
```

---

## Model Routing Pattern

```
Query → Complexity Classifier
           │
  ┌────────┼────────┐
  Simple   Medium   Complex
  ↓        ↓        ↓
  Llama-8B GPT-4o-  GPT-4o +
  (fine-   mini     RAG + CoT
  tuned)
  $0.0001  $0.001   $0.03

80% cheap + 18% medium + 2% expensive = 90% cost reduction
```
