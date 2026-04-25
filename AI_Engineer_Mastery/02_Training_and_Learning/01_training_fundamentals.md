# Training & Learning Fundamentals

## Masked Language Modeling (MLM) — BERT's Training
Randomly mask 15% of tokens. Model predicts the masked words from context.
"The [MASK] sat on the mat" → "cat". Learns bidirectional context.

## Autoregressive vs Masked Models
- **Autoregressive** (GPT): Predict next token. Left-to-right only. Best for generation.
- **Masked** (BERT): Fill in blanks. Sees both directions. Best for understanding.

## Next Sentence Prediction (NSP)
BERT's secondary objective: given two sentences, predict if B follows A.
"[CLS] The cat sat [SEP] On the mat [SEP]" → IsNext / NotNext.
Later research showed NSP provides minimal benefit. RoBERTa removed it.

## Overfitting — Detection and Prevention
Model memorizes training data, fails on new data. Training loss drops, validation loss rises.
Prevention: dropout, early stopping, data augmentation, regularization (L1/L2), more data.

## Catastrophic Forgetting
Fine-tuning on Task B destroys performance on Task A.
Solutions: LoRA (only update small adapters), EWC (penalize changing important weights), multi-task training.

## Vanishing Gradient Problem
In deep networks, gradients shrink exponentially through layers. Early layers barely update.
Solutions: residual connections (skip connections), layer normalization, ReLU/GELU activations, gradient clipping.

## Hyperparameters Reference
| Param | Range | Effect |
|-------|-------|--------|
| Learning rate | 1e-5 to 5e-4 | Too high: diverge. Too low: slow. |
| Batch size | 16-512 | Larger = smoother gradients, more VRAM |
| Epochs | 1-10 | More = risk overfitting |
| Warmup steps | 100-2000 | Gradual LR increase prevents early instability |
| Weight decay | 0.01-0.1 | Regularization to prevent overfitting |
| Gradient clipping | 0.5-1.0 | Prevents exploding gradients |
