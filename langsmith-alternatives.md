# Open-Source Alternatives to LangSmith for Agentic-RAG Evaluation

Context: evaluating agentic RAG applications built with LangChain **deepagents** (LangGraph
underneath). The landscape splits into two layers — you want both.

## Tracing / observability (the LangSmith replacement proper)

### Langfuse
- MIT licensed, self-hostable via Docker/K8s.
- Closest 1:1 swap: ships a LangChain `CallbackHandler` that you pass in
  `config={"callbacks": [handler]}`. Since deepagents is LangGraph underneath, you get the full
  graph trajectory — subagent calls, tool calls, the filesystem/todo middleware steps — as nested
  spans.
- Also has datasets, LLM-as-judge evaluators, human annotation queues, and CI experiment gates.

### Arize Phoenix
- Elastic 2.0, OpenTelemetry-native via OpenInference's LangChain instrumentor.
- Better than Langfuse if you want to sit on OTel and ship spans anywhere; its trace UI for agent
  trajectories is strong.
- Weaker on prompt/dataset management.

### Opik (Comet)
- Apache 2.0, self-hostable.
- Tracing + LLM-judge scoring in one, plus an Agent Optimizer that tunes prompts/retrieval configs
  automatically.

## RAG/agent metrics (what you actually score with)

### Ragas
- The standard for retrieval metrics: faithfulness, context precision/recall, answer relevancy.
- Now has agent metrics too — `ToolCallAccuracy` and `AgentGoalAccuracy` — which are the ones that
  matter for deepagents' planning/subagent behavior.
- Integrates directly with Langfuse, Phoenix, and Opik as the scoring layer.

### DeepEval
- pytest-style assertions. Good if you want evals to live in your existing test suite rather than a
  platform.

## Recommendation for this project

**Langfuse self-hosted for tracing + Ragas for metrics**, with the Ragas runs written against
Langfuse datasets.

That gets you the LangSmith workflow — trace → curate dataset from real traces → run experiment →
compare — with no vendor. Ragas' agent metrics cover the deepagents-specific parts that LangSmith's
generic evaluators don't.

**Caveat:** deepagents' subagent spawning can produce deep, wide traces. Langfuse and Phoenix both
handle nesting fine, but budget for trace volume if you self-host on a small Postgres.

## Sources

- [Langfuse vs. LangSmith](https://langfuse.com/resources/engineering/langsmith-alternative)
- [Ragas × Phoenix integration](https://docs.ragas.io/en/v0.1.21/howtos/integrations/arize.html)
- [Ragas × Opik integration](https://docs.ragas.io/en/v0.3.9/howtos/integrations/_opik/)
- [Open Source and Free AI Agent Evaluation Tools – DataTalks.Club](https://datatalks.club/blog/open-source-free-ai-agent-evaluation-tools.html)
- [LangSmith Alternatives: Open Source Options](https://openobserve.ai/blog/langsmith-alternatives/)
