# LLM Output Issues — Bias, Toxicity, Hallucination

## Hallucination

The model generates confident, plausible-sounding text that is **factually wrong**. This is the #1 production risk.

### Types
- **Intrinsic**: contradicts the provided context
- **Extrinsic**: adds information not in any source

### Mitigation
1. **RAG**: ground answers in retrieved documents
2. **Low temperature**: reduce creativity (T=0.1-0.3)
3. **Citation requirements**: force model to cite sources
4. **Faithfulness checking**: LLM-as-judge on outputs
5. **Explicit refusal**: "If you don't know, say so"

---

## Overconfidence

Models state uncertain things with absolute certainty. They don't say "I think" or "possibly."

### Mitigation
- Ask model to rate its confidence: `"Score your confidence 0-1"`
- Calibrate: if model says 0.9 but is wrong 30% of the time, adjust
- Show confidence to users: "High confidence" vs "Low confidence"

---

## Bias

Models reflect biases in training data. Gender, racial, cultural biases can appear in outputs.

### Detection
- Test with demographic variations: "Write a recommendation for [name]"
- Use bias evaluation datasets (BBQ, WinoBias)
- Monitor output patterns across demographic groups

### Mitigation
- Balanced prompt examples
- Output scanning for biased language
- Human review for high-stakes decisions

---

## Toxicity

Harmful, offensive, or inappropriate outputs.

### Tools
| Tool | What It Does |
|------|-------------|
| Perspective API | Toxicity scoring (0-1) |
| Detoxify | HuggingFace toxicity classifier |
| OpenAI Moderation | Content policy checking |
| Guardrails-AI | Custom safety validators |

---

## Prompt Injection

Users manipulate the model to bypass safety instructions.

See: `06_Prompt_Engineering/01_prompt_engineering_discipline.md` for full coverage.

---

## Refusal Issues

Models sometimes refuse valid requests ("I can't help with that") when they shouldn't. Over-safety.

### Mitigation
- Test refusal rate on valid queries
- Tune system prompt: be specific about what IS allowed, not just what isn't
- Log refusals for review and prompt adjustment
