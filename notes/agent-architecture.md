# Agent Architecture Propositions

## Intended architecture

Papyri has two parallel, interchangeable agent implementations:

```text
                       FastAPI / frontend
                              │
                    AgentConnectorBase
                       ┌──────┴──────┐
                       │             │
                 PiConnector   LangChainConnector
                       │             │
                       └──────┬──────┘
                              │ MCP
                      Shared FastMCP tools
                              │
                    Papyri domain services
```

The implementations are peers:

- **PiConnector** uses Pi as a complete agent harness.
- **LangChainConnector** uses LangChain agents, Deep Agents, or custom Python agent logic.
- **FastMCP** exposes the same Papyri capabilities to either implementation.
- **FastAPI** selects one connector and calls its common interface.

Pi must not be wrapped as a LangChain model or treated as a LangChain subcomponent.

## Common connector contract

The existing `AgentConnectorBase` can become the shared application-facing contract. Initially, it only needs the operations the application actually uses:

```python
class AgentConnectorBase(ABC):
    @abstractmethod
    async def answer_with_chat(
        self,
        messages: list[Any],
    ) -> dict[str, str]:
        ...

    @abstractmethod
    def teardown(self) -> int | None:
        ...
```

The exact names and return types can be refined during implementation. Avoid adding speculative session managers, event hierarchies, or deployment abstractions before they are needed.

FastAPI should hold one selected connector instance:

```python
connector = create_connector_from_settings()

@app.post("/chat")
async def chat(request: ChatRequest):
    return await connector.answer_with_chat(request.messages)
```

## Role of each branch

### Pi branch

Pi already provides the agent harness, including its agent loop, session behavior, tools, streaming events, steering, extensions, and model management.

Most Papyri work therefore sits at the integration boundary:

- adapt Pi RPC events to the HTTP response
- collect the final assistant response
- manage the Pi subprocess lifecycle
- make synchronous RPC handling safe inside FastAPI
- connect Pi to the shared FastMCP server

### LangChain branch

The current `chat_langchain.py` is a chat-model chain:

```text
prompt template → ChatOpenAI → AIMessage
```

It is not yet an agent. The LangChain branch becomes an agent when it gains an agent loop and tool access through LangChain/Deep Agents.

Most work in this branch sits inside the Python agent implementation:

- choose or implement the agent loop
- load shared MCP tools through `langchain-mcp-adapters`
- manage conversation state
- configure tool use, retries, and limits
- translate the result into the shared connector response

## Shared FastMCP capability layer

Papyri-specific operations should live behind FastMCP tools, for example:

```text
search_collection
read_document
find_citations
create_annotation
export_results
```

Both branches consume the same MCP contracts independently:

```text
Pi → MCP client → FastMCP
LangChain → langchain-mcp-adapters → FastMCP
```

FastMCP standardizes tool discovery, input schemas, invocation, and results. It does not make the two agents reason or call tools identically.

Tool contracts should therefore have:

- explicit typed inputs and outputs
- clear descriptions
- bounded result sizes
- structured errors
- idempotency where practical
- safeguards around mutating operations

## Temporary session model

Until the frontend has users and persistent thread identities, the application can use one process-wide agent session.

```text
all frontend requests → one connector → one agent session
```

This is an intentional temporary limitation, not a final user-session architecture.

## Pitfalls

### Do not place Pi under LangChain

Wrapping `PiConnector` as a LangChain `BaseChatModel` would invert the intended architecture. Pi and LangChain are alternative agent runtimes, not parent and child.

### Do not overdesign the shared interface

Only add abstractions required by current behavior. A large event model, user-session manager, checkpoint system, or deployment-aware session resolver can be introduced when the frontend and deployment model require them.

### The current Pi API path is unfinished

`chat_pi.py` contains an ellipsis stub, and `PiMessageProcessorAPI` does not collect events into a final response. Enabling `USE_PI` therefore does not yet produce the response expected by FastAPI.

### The current LangChain path is not an agent

`prompt | model` performs one model invocation. Merely loading MCP tools will not cause tool use; it requires a LangChain/Deep Agents agent loop or custom equivalent.

### A shared session is not concurrency-safe automatically

The current `PiConnector` has mutable request IDs and one stdin/stdout stream. Concurrent requests could mix events. While using one session, requests should be serialized or otherwise protected.

Multiple browser tabs will also share history. Multiple Uvicorn workers would each create a separate process-local session.

### Environment-variable backend selection is error-prone

The current check treats every non-empty `USE_PI` value as true, including `"false"` and `"0"`. Backend selection should parse an explicit configured value.

### Lifecycle must be explicit

Long-lived connector resources should be initialized once and torn down when FastAPI stops:

- Pi subprocesses
- MCP client connections or sessions
- persistent LangChain agent resources

### MCP does not define authorization policy

Sharing tools does not determine which operations are safe for a request. Authentication, authorization, approvals, and credentials must be handled deliberately as the application matures.

## Summary

The target design is two sibling agent connectors behind one small application contract. Pi supplies an established agent harness; LangChain/Deep Agents supplies a Python-native customizable alternative. Both reuse the same Papyri capabilities through FastMCP, while FastAPI and the frontend remain independent of the selected agent runtime.
