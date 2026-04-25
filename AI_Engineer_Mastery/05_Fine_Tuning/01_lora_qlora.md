# LoRA and QLoRA — Efficient Fine-Tuning

## The Problem

Full fine-tuning GPT-3 (175B params) = update all 175B weights = ~700GB VRAM. Impossible on most hardware.

## LoRA — Low-Rank Adaptation

### Core Math
```
Original weight: W ∈ ℝ^(d×k)  (e.g., 4096×4096 = 16M params)
LoRA update: ΔW = B × A
  A ∈ ℝ^(r×k)  — "down" projection
  B ∈ ℝ^(d×r)  — "up" projection
  r = rank (8 or 16) ≪ d

Output: h = (W₀ + BA)x

Trainable params: r(d+k) ≈ 0.1% of original
```

### Key Hyperparameters

| Param | Controls | Typical Values |
|-------|----------|---------------|
| `r` (rank) | Capacity of update | 4, 8, 16, 32 |
| `alpha` | Scaling factor (alpha/r × BA) | 16, 32 |
| `target_modules` | Which layers to apply LoRA | ["q_proj", "v_proj"] |
| `dropout` | Regularization | 0.05-0.1 |

## QLoRA — Quantization + LoRA

1. **Quantize base model to 4-bit** (NF4 format): 7B model: 14GB → 4GB
2. **Double quantization**: Quantize the quantization constants
3. **Train LoRA adapters in 16-bit**: Only tiny matrices in full precision

## Comparison

| Method | VRAM (7B) | Quality | Speed | Use When |
|--------|-----------|---------|-------|----------|
| Full fine-tune | ~120GB | Best | Slowest | Unlimited resources |
| LoRA | ~14GB | Near-full | Fast | 1-2 A100 GPUs |
| QLoRA | ~6GB | Near-LoRA | Slower | Consumer GPU (RTX 3090) |

## Tools
- **HuggingFace PEFT**: `LoraConfig` + `get_peft_model()`
- **bitsandbytes**: 4-bit quantization
- **Axolotl / LLaMA Factory**: Managed training pipelines
- **Merge**: `merge_and_unload()` before deployment
