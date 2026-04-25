# Model Selection & Routing — Choosing the Right LLM

## The Core Principle

No single model is best for all tasks. Production systems route different queries to different models based on complexity, cost, and latency requirements.

---

## Model Comparison (2024-2025)

| Model | Strength | Cost (input/1M) | Latency | Best For |
|-------|----------|-----------------|---------|----------|
| GPT-4o | Strongest reasoning | $5.00 | Medium | Complex tasks |
| GPT-4o-mini | Good quality, cheap | $0.15 | Fast | High-volume tasks |
| Claude 3.5 Sonnet | Long context, coding | $3.00 | Medium | Analysis, code |
| Gemini 1.5 Pro | 1M+ context window | $3.50 | Medium | Long documents |
| Llama 3.1 70B | Self-hosted, private | Free* | Varies | Privacy-critical |
| Mistral Large | European compliance | $4.00 | Medium | EU data residency |

*Hardware cost for self-hosting

---

## Routing Strategies

### Rule-Based Routing
```python
if len(query) < 50 and is_faq(query):
    model = "gpt-4o-mini"
elif contains_code(query):
    model = "claude-3.5-sonnet"
elif query_language != "english":
    model = "gpt-4o"  # best multilingual
else:
    model = "gpt-4o-mini"  # default cheap
```

### LLM Classifier Routing
```
Small LLM rates complexity 1-5:
  Score 1-2 → GPT-4o-mini ($0.15/1M)
  Score 3-4 → GPT-4o ($5.00/1M)
  Score 5   → GPT-4o with CoT
```

### Embedding-Based Routing
Cluster historical queries by complexity. Route new queries to their cluster's assigned model.

---

## Self-Hosted vs API Models

| Factor | API (OpenAI, Anthropic) | Self-Hosted (Llama, Mistral) |
|--------|------------------------|------------------------------|
| Setup time | Minutes | Days-weeks |
| Cost at low volume | Cheaper | Expensive (GPU idle) |
| Cost at high volume | Expensive | Cheaper |
| Data privacy | Data leaves your network | Stays on-premise |
| Compliance | Varies by provider | Full control |
| Model updates | Provider controls | You control |
| Latency | Network dependent | Local = fast |
| Scaling | Auto-scales | You manage |

---

## Safety Validation Before Deployment

1. Run evaluation suite — check for regressions
2. Compare against baseline on held-out test set
3. Check for memorization (privacy risk)
4. Red team testing for safety bypasses
5. A/B test with 5% traffic before full rollout
