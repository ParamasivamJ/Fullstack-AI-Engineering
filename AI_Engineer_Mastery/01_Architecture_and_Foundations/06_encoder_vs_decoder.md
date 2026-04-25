# Encoder vs Decoder — Full Architecture Comparison

## The Three Architectures

### Encoder-Only (BERT)
- Sees ALL tokens (bidirectional attention)
- Produces fixed-size representations
- **Best for**: classification, NER, embeddings, sentiment
- **Examples**: BERT, RoBERTa, DeBERTa

### Decoder-Only (GPT)
- Sees only PREVIOUS tokens (causal/masked attention)
- Generates one token at a time, autoregressively
- **Best for**: text generation, chat, code, reasoning
- **Examples**: GPT-4, Llama, Mistral, Claude

### Encoder-Decoder (T5)
- Encoder processes full input bidirectionally
- Decoder generates output autoregressively
- Cross-attention: decoder attends to encoder outputs
- **Best for**: translation, summarization, structured output
- **Examples**: T5, BART, Flan-T5

## Which Dominates Today?

**Decoder-only** dominates. GPT-4, Claude, Llama, Mistral — all decoder-only. The insight: with enough scale and data, decoder-only models can do everything (classify, embed, translate, generate) by framing every task as text completion.

## When to Still Use Encoder-Only
- Fast classification (BERT: 10ms vs GPT-4: 500ms)
- High-quality embeddings (dedicated embedding models)
- Edge deployment (small encoder models on mobile)
