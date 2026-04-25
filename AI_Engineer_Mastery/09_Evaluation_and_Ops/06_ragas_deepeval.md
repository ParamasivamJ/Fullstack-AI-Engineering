# RAGAS & DeepEval — Evaluation Frameworks in Depth

## Why You Need Evaluation Frameworks

Manual evaluation doesn't scale. With 500 test queries, you can't manually judge each response. RAGAS and DeepEval automate the evaluation of RAG pipelines with standardized, reproducible metrics.

---

## RAGAS (Retrieval Augmented Generation Assessment)

### Core Metrics

| Metric | What It Measures | How |
|--------|-----------------|-----|
| **Faithfulness** | Is the answer supported by the context? | LLM checks if each claim maps to context |
| **Answer Relevancy** | Does the answer address the question? | Generate questions from answer, compare to original |
| **Context Precision** | Are retrieved chunks relevant? | LLM judges each chunk's relevance |
| **Context Recall** | Does context cover the full answer? | Compare context coverage against gold answer |

### Usage

```python
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_precision

# Prepare test data
dataset = {
    "question": ["What is the return policy?"],
    "answer": ["Items can be returned within 30 days."],
    "contexts": [["Return policy: 30-day refund for all items..."]],
    "ground_truth": ["30-day return policy for full refund."]
}

result = evaluate(dataset, metrics=[faithfulness, answer_relevancy, context_precision])
print(result)  # {"faithfulness": 0.92, "answer_relevancy": 0.88, ...}
```

---

## DeepEval

### Advantages over RAGAS
- More metrics out of the box (hallucination, bias, toxicity)
- Built-in test runner (pytest-style)
- Dashboard for tracking scores over time

```python
from deepeval import assert_test
from deepeval.metrics import FaithfulnessMetric, AnswerRelevancyMetric

metric = FaithfulnessMetric(threshold=0.8)
test_case = LLMTestCase(
    input="What's the refund policy?",
    actual_output="30-day refund on all items.",
    retrieval_context=["Refund policy: 30 days..."]
)
assert_test(test_case, [metric])  # Passes if faithfulness >= 0.8
```

---

## Building Test Sets

```
1. COLLECT REAL QUERIES: 200-500 from production logs
2. CREATE GOLD ANSWERS: domain experts write correct answers
3. IDENTIFY SOURCE DOCS: which documents contain each answer
4. CATEGORIZE: easy/medium/hard, single-hop/multi-hop
5. INCLUDE EDGE CASES: unanswerable, ambiguous, multi-document
```

---

## Regression Testing Workflow

```
On every pipeline change (new chunking, new model, new prompt):
  1. Run evaluation suite against test set
  2. Compare scores to baseline
  3. If ANY metric drops > 5% → block deployment
  4. Store scores with version tag for trend analysis

VERSION TRACKING:
  v1.0: faithfulness=0.85, recall@5=0.78
  v1.1: faithfulness=0.89, recall@5=0.82  ← improved
  v2.0: faithfulness=0.83, recall@5=0.90  ← tradeoff!
```

---

## Tools Comparison

| Feature | RAGAS | DeepEval |
|---------|-------|---------|
| RAG-specific metrics | ✅ Core focus | ✅ Plus more |
| Safety metrics | ❌ | ✅ Toxicity, bias |
| Test runner | ❌ (use pytest) | ✅ Built-in |
| Dashboard | ❌ | ✅ Cloud dashboard |
| Custom metrics | ✅ | ✅ |
| Open source | ✅ | ✅ (core) |
