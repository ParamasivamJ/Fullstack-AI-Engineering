# Math & Theory for LLMs

## Softmax — The Probability Gate
Converts raw scores (logits) into probabilities that sum to 1.
```
softmax(zᵢ) = exp(zᵢ) / Σ exp(zⱼ)
```
Used in: attention weights, final token prediction layer.
Temperature scaling: `softmax(z/T)` — higher T = flatter distribution.

## Dot Product in Self-Attention
Measures how well a Query matches a Key:
```
score(Q, K) = Q · K / √dₖ
```
High dot product = vectors point same direction = high attention.
Scaling by √dₖ prevents large values that push softmax to extremes.

## Cross-Entropy Loss
Measures how different the model's predicted distribution is from the true label.
```
L = -Σ yᵢ log(ŷᵢ)
```
For next-token prediction: y is one-hot (the correct next token), ŷ is the model's probability distribution. Minimizing cross-entropy = maximizing the probability of the correct token.

## Backpropagation & Gradient Descent
Backprop: compute gradients of loss w.r.t. each weight using chain rule.
Gradient descent: update weights in the direction that reduces loss.
```
w_new = w_old - η × ∂L/∂w
η = learning rate
```
Variants: SGD, Adam (momentum + adaptive LR, most popular for LLMs), AdamW (Adam + weight decay).

## KL Divergence
Measures how one probability distribution differs from another.
```
KL(P || Q) = Σ P(x) × log(P(x) / Q(x))
```
Used in: RLHF (penalize fine-tuned model from deviating too far from base), VAEs, knowledge distillation.

## ReLU Activation
```
ReLU(x) = max(0, x)
```
Simple, fast, prevents vanishing gradients for positive inputs.
Modern LLMs use GELU: smooth approximation that allows small negative gradients.

## Eigenvalues, Eigenvectors, PCA
- **Eigenvectors**: directions that don't change under a transformation (only scale)
- **Eigenvalues**: how much each eigenvector is scaled
- **PCA**: find directions of maximum variance → dimensionality reduction
Used in: embedding visualization (reduce 384D to 2D), understanding attention patterns.

## Jacobian Matrix
Matrix of all first-order partial derivatives. In deep learning:
represents how changing each input dimension affects each output dimension.
Important for understanding gradient flow through layers.
