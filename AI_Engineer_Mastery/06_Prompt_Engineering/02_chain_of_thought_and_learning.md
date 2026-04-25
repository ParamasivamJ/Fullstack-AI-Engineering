# Chain-of-Thought Prompting & Zero/Few-Shot Learning

## Chain-of-Thought (CoT)
Force the model to show reasoning step by step before answering.

```
WITHOUT CoT:
  Q: "If a shirt costs $25 and is 20% off, what do I pay?"
  A: "$20" ← sometimes wrong with complex math

WITH CoT:
  Q: "...Let's think step by step."
  A: "Step 1: 20% of $25 = $5. Step 2: $25 - $5 = $20. Answer: $20" ← reliable
```

### Variants
- **Zero-shot CoT**: Add "Let's think step by step" (no examples needed)
- **Few-shot CoT**: Show 2-3 worked examples with reasoning chains
- **Self-consistency**: Generate 5 CoT chains, take majority vote answer

### Cost: 2-4x more output tokens. Quality: dramatically better for reasoning.

---

## Zero-Shot Learning
No examples provided. Relies on model's pre-training knowledge.
```
"Classify this email as: refund, complaint, question, or praise.
 Email: 'I love your product!'
 Classification:"
```
Works for: simple tasks, strong models, well-defined categories.

## Few-Shot Learning
Provide 3-5 input/output examples to show desired format.
```
"Email: 'I want my money back!' → refund
 Email: 'Your service is terrible' → complaint
 Email: 'I love your product!' → ???"
```
Works for: complex formatting, ambiguous categories, specific styles.

## When to Use Each

| Approach | Cost | Quality | Use When |
|----------|------|---------|----------|
| Zero-shot | Low | Good for simple | Task is straightforward |
| Few-shot | Medium | Better consistency | Need specific format/style |
| CoT | High (2-4x) | Best for reasoning | Math, logic, multi-step |
| Few-shot CoT | Highest | Best overall | Complex tasks needing both examples and reasoning |
