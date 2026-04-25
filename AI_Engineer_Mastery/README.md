# AI Engineer Mastery — Complete Deep Dive Guide

> 65+ concepts from beginner intuition to expert-level production design.  
> Every file is a standalone deep-dive. Read in order or jump to any topic.

## Directory Structure

```
AI_Engineer_Mastery/
│
├── 01_Architecture_and_Foundations/
│   ├── 01_tokenization.md
│   ├── 02_embeddings.md
│   ├── 03_attention_mechanism.md
│   ├── 04_multi_head_attention.md
│   ├── 05_positional_encodings.md
│   ├── 06_encoder_vs_decoder.md
│   ├── 07_transformer_architecture.md
│   ├── 08_context_windows.md
│   ├── 09_foundation_models.md
│   ├── 10_mixture_of_experts.md
│   └── 11_llm_complete_overview.md
│
├── 02_Training_and_Learning/
│   ├── 01_masked_language_modeling.md
│   ├── 02_autoregressive_vs_masked.md
│   ├── 03_next_sentence_prediction.md
│   ├── 04_overfitting.md
│   ├── 05_catastrophic_forgetting.md
│   ├── 06_vanishing_gradients.md
│   └── 07_hyperparameters.md
│
├── 03_Math_and_Theory/
│   ├── 01_softmax.md
│   ├── 02_dot_product_attention.md
│   ├── 03_cross_entropy_loss.md
│   ├── 04_backpropagation.md
│   ├── 05_gradient_descent.md
│   ├── 06_kl_divergence.md
│   ├── 07_relu_activation.md
│   └── 08_eigenvalues_pca.md
│
├── 04_Generation_and_Decoding/
│   ├── 01_greedy_vs_beam_search.md
│   ├── 02_temperature_topk_topp.md
│   └── 03_sampling_deep_dive.md
│
├── 05_Fine_Tuning/
│   ├── 01_lora_qlora.md
│   ├── 02_peft.md
│   ├── 03_model_distillation.md
│   ├── 04_fine_tuning_vs_rag.md
│   └── 05_model_selection_routing.md
│
├── 06_Prompt_Engineering/
│   ├── 01_prompt_engineering_discipline.md
│   ├── 02_chain_of_thought.md
│   ├── 03_zero_shot_learning.md
│   ├── 04_few_shot_learning.md
│   └── 05_structured_outputs_injection_defense.md
│
├── 07_RAG_Pipelines/
│   ├── 01_rag_complete_deep_dive.md
│   ├── 02_ingestion_pipeline.md
│   ├── 03_advanced_rag_techniques.md
│   ├── 04_vector_database_internals.md
│   └── 05_knowledge_graph_integration.md
│
├── 08_Agents_and_Orchestration/
│   ├── 01_agentic_workflows.md
│   └── 02_orchestration_frameworks.md
│
├── 09_Evaluation_and_Ops/
│   ├── 01_ai_quality_metrics.md
│   ├── 02_monitoring_observability.md
│   ├── 03_guardrails.md
│   ├── 04_cost_latency_optimization.md
│   ├── 05_fallback_degradation.md
│   └── 06_ragas_deepeval.md
│
├── 10_Production_and_Design/
│   ├── 01_llm_challenges_production.md
│   ├── 02_bias_toxicity_hallucination.md
│   ├── 03_generative_vs_discriminative.md
│   └── 04_business_to_ai_solution_design.md
│
└── README.md (this file)
```

## How to Use This Guide

1. **Beginners**: Start with `01_Architecture_and_Foundations/` → read files 01-07 in order
2. **Intermediate**: Jump to `06_Prompt_Engineering/` and `07_RAG_Pipelines/`
3. **Advanced**: Focus on `08_Agents_and_Orchestration/`, `09_Evaluation_and_Ops/`, `10_Production_and_Design/`
4. **Interview Prep**: Read `05_Fine_Tuning/04_fine_tuning_vs_rag.md` and `10_Production_and_Design/04_business_to_ai_solution_design.md`

## Total Coverage

| Section | Files | Focus |
|---------|-------|-------|
| Architecture & Foundations | 11 | How LLMs work internally |
| Training & Learning | 7 | How models learn and what can go wrong |
| Math & Theory | 8 | The math behind transformers |
| Generation & Decoding | 3 | How text is actually generated |
| Fine-Tuning | 5 | LoRA, PEFT, when to fine-tune vs RAG |
| Prompt Engineering | 5 | Production prompting, structured outputs, injection defense |
| RAG Pipelines | 5 | End-to-end RAG from ingestion to advanced techniques |
| Agents & Orchestration | 2 | Agentic patterns, LangChain/LangGraph/CrewAI/AutoGen |
| Evaluation & Ops | 6 | Metrics, monitoring, guardrails, cost optimization |
| Production & Design | 4 | Real-world challenges, business → architecture decisions |
