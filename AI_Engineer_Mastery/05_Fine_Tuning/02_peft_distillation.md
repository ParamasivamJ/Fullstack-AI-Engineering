# PEFT & Model Distillation

## PEFT (Parameter-Efficient Fine-Tuning)
Family of methods that fine-tune a tiny fraction of model parameters.

| Method | Trainable Params | VRAM | Quality |
|--------|-----------------|------|---------|
| Full fine-tuning | 100% | 120GB+ | Best |
| LoRA | 0.1-1% | 14GB | 95-99% |
| QLoRA | 0.1-1% + 4-bit | 6GB | 90-97% |
| Prefix Tuning | < 0.1% | 8GB | 85-95% |
| Adapters | 1-5% | 16GB | 93-98% |

LoRA is the dominant approach. See `01_lora_qlora.md` for details.

---

## Model Distillation

Transfer knowledge from a large "teacher" model to a small "student" model.

```
TEACHER: GPT-4 (huge, expensive, slow)
  ↓ generates training data
STUDENT: Llama-8B (small, cheap, fast)
  ↓ trained on teacher's outputs
RESULT: 8B model with 80-90% of GPT-4's quality at 1/100th cost
```

### How Distillation Works
1. Run teacher on 10,000-50,000 examples → collect outputs
2. Fine-tune student on (input, teacher_output) pairs
3. Evaluate student against teacher on held-out test set
4. Iterate until quality meets threshold

### When to Use
- High-volume tasks where cost matters (classification, routing)
- Latency-critical applications (need fast inference)
- Edge deployment (model must run on limited hardware)
- Privacy (can't send data to external API)

### Tradeoffs
- ✅ 10-100x cheaper inference
- ✅ 2-10x faster inference
- ✗ Lower quality ceiling
- ✗ Requires teacher API access for training data generation
- ✗ Must re-distill when teacher updates
