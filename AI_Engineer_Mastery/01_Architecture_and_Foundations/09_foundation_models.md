# Foundation Models — Types and Taxonomy

## What Is a Foundation Model?

A model pre-trained on massive data that can be adapted to many downstream tasks. The "foundation" that everything else is built on.

## Taxonomy

| Type | Training Objective | Architecture | Examples | Best For |
|------|-------------------|-------------|----------|----------|
| **Autoregressive** | Predict next token | Decoder-only | GPT-4, Llama, Mistral | Text generation, chat |
| **Masked Language** | Fill in blanks | Encoder-only | BERT, RoBERTa | Classification, NER, embeddings |
| **Seq2Seq** | Input → Output | Encoder-Decoder | T5, BART, Flan-T5 | Translation, summarization |
| **Multimodal** | Text + Image + Audio | Varies | Gemini, GPT-4V, LLaVA | Visual QA, document understanding |
| **Embedding** | Semantic similarity | Encoder | BGE, E5, Voyage | Search, RAG, clustering |
| **Diffusion** | Denoise images | U-Net variants | Stable Diffusion, DALL-E | Image generation |

## Choosing the Right Class

- **Need generation?** → Autoregressive (GPT, Llama)
- **Need classification?** → Encoder (BERT) or fine-tuned autoregressive
- **Need embeddings?** → Dedicated embedding model (BGE, E5)
- **Need translation?** → Seq2Seq (T5) or autoregressive (GPT-4)
- **Need images?** → Diffusion (Stable Diffusion)

## Small vs Large Models

| Category | Examples | Parameters | When to Use |
|----------|---------|-----------|-------------|
| Small | Phi-3, Llama-8B | 1-8B | Classification, simple tasks, low cost |
| Medium | Llama-70B, Mistral Large | 30-70B | Complex reasoning, self-hosted |
| Large | GPT-4, Claude 3.5 | 200B+ | Hardest tasks, highest quality |

## Chat vs Instruct vs Base

- **Base**: Raw pre-trained model. Completes text, doesn't follow instructions.
- **Instruct**: Fine-tuned to follow instructions. Better for single-turn tasks.
- **Chat**: Fine-tuned for multi-turn conversation. RLHF-aligned for safety.
