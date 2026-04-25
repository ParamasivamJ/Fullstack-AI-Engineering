# Generative vs Discriminative Models

## Core Difference
- **Discriminative**: Learns the boundary between classes. P(label | input). "Is this spam?"
- **Generative**: Learns the data distribution. P(input, label) or P(output | input). "Write an email."

## In LLM Context

| Type | What It Does | Examples | Use Case |
|------|-------------|----------|----------|
| Discriminative | Classifies, scores, ranks | BERT, classifiers | Sentiment, NER, spam detection |
| Generative | Creates new content | GPT-4, Claude, Llama | Chat, writing, code generation |
| Embedding | Maps text to vectors | BGE, E5 | Search, similarity, clustering |

## When to Use Each

### Use Discriminative (Classifier) When:
- Fixed set of categories (spam/not-spam, intent classification)
- Need speed and low cost (fine-tuned BERT runs in 10ms)
- Need interpretable confidence scores
- High-volume classification tasks (millions/day)

### Use Generative (LLM) When:
- Output is free-form text (answers, summaries, code)
- Task requires reasoning or creativity
- Categories are fluid or complex
- Need to explain the classification reasoning

## Hybrid Pattern
```
Step 1: Discriminative model classifies intent (fast, cheap)
Step 2: Route to specialized generative model per intent
  "refund" → RAG pipeline for refund policies
  "technical" → Agent with diagnostic tools
  "general" → Simple LLM response
```
