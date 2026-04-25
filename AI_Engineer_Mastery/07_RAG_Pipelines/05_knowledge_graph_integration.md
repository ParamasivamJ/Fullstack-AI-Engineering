# Knowledge Graph Integration with RAG

## What Is a Knowledge Graph?
A structured representation of entities and relationships:
```
(Apple, is_a, Company) → (Apple, CEO, Tim_Cook) → (Tim_Cook, nationality, American)
```

## Why Combine KG + RAG?
- RAG retrieves text chunks (unstructured) — good for natural language
- KGs store facts (structured) — good for precise relationships
- Together: richer context, more accurate answers, less hallucination

## Architecture
```
User Query → [Entity Extraction] → [KG Lookup] → structured facts
          → [Vector Search]    → text chunks
          → [Merge Context]    → LLM → Answer
```

## When to Use
- ✅ Medical/legal domains with precise relationships
- ✅ When you need to traverse relationships ("Who reports to X's manager?")
- ✅ When facts must be exact (dates, amounts, names)
- ✗ When text search alone is sufficient
- ✗ When maintaining the KG is too expensive

## Tools
- Neo4j (graph database)
- Amazon Neptune
- RDFLib (Python)
- LangChain GraphQA chains
