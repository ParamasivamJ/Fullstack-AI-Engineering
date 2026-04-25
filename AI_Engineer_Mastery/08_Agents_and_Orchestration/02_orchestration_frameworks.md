# Orchestration Frameworks — LangChain, LangGraph, CrewAI, AutoGen

## What Orchestration Means

An LLM call is one step. A production AI feature is 5-15 steps: retrieve, call LLM, validate, maybe retry, maybe route to a different model. **Orchestration** connects these steps into reliable pipelines.

---

## The Four Frameworks Compared

| Framework | Mental Model | Best For | Complexity |
|-----------|-------------|----------|------------|
| **LangChain** | Sequential chains | RAG, prototyping | Medium |
| **LangGraph** | State machine / graph | Complex agents, retries, HITL | High |
| **CrewAI** | Team of role-based agents | Research, content generation | Medium |
| **AutoGen** | Conversational agents | Code execution, data analysis | Medium-High |

---

## LangChain

### Core Abstractions

| Concept | What It Does |
|---------|-------------|
| LLM/ChatModel | Wraps any model provider (OpenAI, Anthropic, HF) |
| PromptTemplate | Parameterized prompts with variables |
| OutputParser | Parse LLM text into structured objects |
| Chain | Connect prompt → LLM → parser |
| Retriever | Fetch relevant documents |
| Tool | External function the LLM can call |
| Memory | Conversation history management |
| Callback | Hooks for logging, tracing, streaming |

### LCEL (LangChain Expression Language)

```python
chain = (
    {"context": retriever, "question": RunnablePassthrough()}
    | prompt
    | llm
    | StrOutputParser()
)
answer = chain.invoke("What is our refund policy?")
```

### When to Use / Not Use

✅ RAG pipelines, prototyping, provider abstraction (swap OpenAI ↔ Anthropic)

✗ Complex branching (use LangGraph), simple single calls (use SDK directly)

---

## LangGraph

### The Key Idea: Workflows as State Graphs

```
Nodes = functions (each does one thing)
Edges = transitions (including conditional)
State = shared dictionary passed through the graph
```

### Example: Agent with Retry Loop

```python
from langgraph.graph import StateGraph, END

class AgentState(TypedDict):
    query: str
    draft: str
    quality_score: float

graph = StateGraph(AgentState)
graph.add_node("research", do_research)
graph.add_node("draft", draft_answer)
graph.add_node("review", review_quality)

graph.add_edge("research", "draft")
graph.add_edge("draft", "review")
graph.add_conditional_edges("review", quality_router,
    {"pass": END, "fail": "research"})  # ← retry loop!

graph.set_entry_point("research")
app = graph.compile()
```

### Why LangGraph Over LangChain

- Conditional branching (if/else routing)
- Cycles (retry loops, reflection)
- Human-in-the-loop (pause and wait)
- Persistent state (save/resume)
- Deterministic control mixed with LLM reasoning

---

## CrewAI

### The Key Idea: Teams of Specialist Agents

```python
from crewai import Agent, Task, Crew

researcher = Agent(role="Researcher", goal="Find data on {topic}", tools=[web_search])
writer = Agent(role="Writer", goal="Write clear report")
editor = Agent(role="Editor", goal="Ensure accuracy")

crew = Crew(
    agents=[researcher, writer, editor],
    tasks=[research_task, write_task, edit_task],
    process=Process.sequential  # or hierarchical
)
result = crew.kickoff(inputs={"topic": "AI in healthcare"})
```

✅ Content generation, research workflows, multi-step analysis

✗ Real-time chat, low-latency APIs, simple tasks

---

## AutoGen (Microsoft)

### The Key Idea: Agents That Talk + Execute Code

```python
from autogen import AssistantAgent, UserProxyAgent

assistant = AssistantAgent("assistant", llm_config=llm_config)
user_proxy = UserProxyAgent("user_proxy",
    code_execution_config={"work_dir": "coding"})

user_proxy.initiate_chat(assistant, message="Analyze this CSV")
# Assistant writes Python → executes → sees errors → fixes → re-runs
```

✅ Coding assistants, data analysis, iterative problem-solving

✗ Production customer-facing apps (hard to control, unpredictable cost)

---

## Decision Framework

| Your Situation | Use This | Why |
|---------------|----------|-----|
| Simple RAG | LangChain or plain Python | No overhead needed |
| Complex agent with retries | LangGraph | Graph-based control |
| Multi-step content workflow | CrewAI | Role-based agents |
| Coding/data analysis | AutoGen | Code execution loop |
| Production API, strict latency | Plain Python + SDK | Full control |

---

## Testing & Debugging

1. **Trace every step**: Use LangSmith/Langfuse for input → output → latency per node
2. **Unit test each node**: Mock LLM responses, test each function independently
3. **Integration test**: Run full graph with golden dataset, assert expected results
4. **Set hard limits**: Max iterations, max tokens per step, max cost per request

---

## ⚠️ The Orchestration Trap

If your workflow is: call LLM → parse JSON → save to DB — you do NOT need LangChain. Write 20 lines of Python. Frameworks add value for retrieval abstraction, provider switching, complex control flow, or tracing. If you don't need those, skip the framework.
