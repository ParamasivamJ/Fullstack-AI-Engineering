# Agentic Workflow Design — When and How

## When an Agent Is Actually Needed

Agents are powerful but complex. Before building one, ask: "Can a simpler workflow solve this?"

| Scenario | Right Approach | Why |
|----------|---------------|-----|
| Answer questions from docs | RAG pipeline | Predictable, fast, cheap |
| Classify and route tickets | LLM chain | Sequential, no tool use |
| Summarize a document | Map-reduce chain | No iteration needed |
| Research a topic from the web | Agent with search tool | Needs to decide what to search, iterate |
| Write and test code | Agent with code execution | Must see results and self-correct |

**Decision rule**: If the steps are ALWAYS the same → use a deterministic workflow. If steps VARY based on intermediate results → use an agent.

---

## Agent Architecture

```
┌─────────────────────────────────────────────────┐
│  USER QUERY                                      │
│  "Find recent papers on RAG and summarize them" │
└──────────────┬──────────────────────────────────┘
               ▼
┌──────────────────────────────────────────────────┐
│  PLANNING: What steps do I need?                  │
│  1. Search for recent RAG papers                  │
│  2. Read the top 5 results                        │
│  3. Extract key findings from each                │
│  4. Synthesize into a summary                     │
└──────────────┬───────────────────────────────────┘
               ▼
┌──────────────────────────────────────────────────┐
│  EXECUTION LOOP (ReAct pattern):                  │
│                                                   │
│  Thought: I need to search for recent RAG papers  │
│  Action:  web_search("RAG retrieval augmented     │
│           generation 2024 papers")                │
│  Observation: [results list]                      │
│                                                   │
│  Thought: I found 10 results. Let me read top 5.  │
│  Action:  read_url("https://arxiv.org/...")        │
│  Observation: [paper content]                     │
│                                                   │
│  ... continues until task complete                │
│                                                   │
│  STOP CONDITION: all 5 papers read + summary done │
└──────────────────────────────────────────────────┘
```

---

## Tool Design

### Tool Selection & Routing
The agent chooses which tool based on the current need:

```python
tools = [
    {"name": "web_search", "description": "Search the web for information"},
    {"name": "read_url", "description": "Read content from a URL"},
    {"name": "calculate", "description": "Perform mathematical calculations"},
    {"name": "database_query", "description": "Query the company database"},
]
```

### Tool Result Validation
Never trust tool outputs blindly:

```
1. Check for errors (HTTP 500, empty results)
2. Validate format (is the result parseable?)
3. Check relevance (did the tool return what we asked for?)
4. Set timeouts (tools can hang)
5. Retry with modified input on failure
```

---

## Planning vs Execution

| Approach | How It Works | Best For |
|----------|-------------|----------|
| **ReAct** | Thought → Action → Observation loop | Simple agents, single tool use |
| **Plan-then-Execute** | Create full plan, then execute steps | Multi-step tasks, predictable workflows |
| **Reflection** | Execute → evaluate → revise → re-execute | Quality-critical outputs |

### Reflection Loop
```
Draft answer → Self-critique ("Is this complete? Accurate?")
  → If good: return
  → If bad: identify weakness → re-research → redraft
  → Max 3 iterations (prevent infinite loops)
```

---

## Single-Agent vs Multi-Agent

### Single Agent
One LLM with multiple tools. Simple, predictable, debuggable.

### Multi-Agent Patterns

```
PATTERN 1: Pipeline (sequential)
  Researcher → Writer → Editor
  Each agent has one role, passes output to next.

PATTERN 2: Debate (parallel)
  Agent A proposes → Agent B critiques → Agent A revises
  Better quality through adversarial review.

PATTERN 3: Hierarchical (manager + workers)
  Manager decomposes task → assigns to specialist agents
  Manager synthesizes results.

PRODUCTION ADVICE: Start with single agent.
Only go multi-agent when single agent demonstrably fails.
Multi-agent = more cost, more latency, harder to debug.
```

---

## Guardrails for Agents

```
1. MAX ITERATIONS: agent stops after N steps (prevent infinite loops)
2. MAX COST: track token usage, stop if budget exceeded
3. ALLOWED TOOLS: whitelist tools the agent can use
4. HUMAN-IN-THE-LOOP: pause for approval before destructive actions
5. OUTPUT VALIDATION: check final output against requirements
6. SANDBOXING: code execution in isolated containers
7. DATA ACCESS: restrict to authorized data only
```

---

## Human-in-the-Loop

```
WHEN TO REQUIRE HUMAN APPROVAL:
  ✗ Deleting data
  ✗ Sending emails/messages
  ✗ Making purchases
  ✗ Modifying production systems
  ✗ Actions above a cost threshold

IMPLEMENTATION (LangGraph):
  graph.add_node("approve", human_approval_node)
  graph.add_conditional_edges("plan", 
    lambda s: "approve" if s["risk"] > 0.7 else "execute")
```

---

## Production Concerns

| Concern | Impact | Mitigation |
|---------|--------|------------|
| Unpredictable cost | Agent may loop 20 times | Max iterations + cost cap |
| Latency | Multi-step = 5-30 seconds | Stream intermediate results |
| Debugging | Hard to reproduce failures | Full trace logging (LangSmith) |
| Tool hallucination | Agent invents non-existent tools | Strict tool whitelist |
| Data leakage | Agent exposes internal data | Least-privilege tool access |
