# LangChain Integration in Papyri Assistant

## What LangChain is

LangChain is a framework for composing LLM-related components such as:

- prompts
- chat models
- message histories
- tools
- retrievers
- output parsers
- tracing and callbacks

LangChain does **not** run an AI model itself. In this project, `ChatOpenAI` sends an HTTP request to an OpenAI-compatible API. LangChain standardizes the inputs and outputs and connects the prompt to that model.

Papyri currently uses only a small portion of LangChain:

```text
chat messages → prompt template → ChatOpenAI → AIMessage
```

It does not currently use LangChain agents, tools, retrieval, LangGraph, or LangServe.

## How `chat_langchain.py` operates

The entry point is:

```python
async def answer_with_chat(raw_messages: list[Any]) -> dict[str, str]:
```

at `backend/src/papyri_backend/chat_langchain.py:17`.

### 1. Normalize frontend messages

```python
messages = normalize_messages(raw_messages)
```

`normalize_messages()` is defined in `backend/src/papyri_backend/utils/messages.py:18`. It accepts loosely typed frontend data and retains only valid, non-empty messages with these roles:

- `system`
- `user`
- `assistant`

It also converts structured content blocks into plain text. This normalization is Papyri code, not LangChain functionality.

### 2. Find the most recent user message

```python
last_user_message_index = _find_last_user_message_index(messages)
```

If no user message exists, the function raises:

```python
ValueError("No user message found.")
```

Anything after the final user message is ignored.

### 3. Limit the context window

```python
start_index = max(0, last_user_message_index - (_MAX_CONTEXT_MESSAGES - 1))
window = messages[start_index : last_user_message_index + 1]
```

`_MAX_CONTEXT_MESSAGES` is 9, so at most nine messages are sent to the model. This is a message-count limit rather than a token limit.

The backend is stateless in this path: the frontend sends the conversation on every request, and the backend selects the latest nine messages.

### 4. Convert messages into LangChain objects

```python
conversation = [_to_langchain_message(message) for message in window]
```

The project-specific messages become:

| Papyri role | LangChain class |
|---|---|
| `user` | `HumanMessage` |
| `assistant` | `AIMessage` |
| `system` | `SystemMessage` |

LangChain chat models operate on these structured objects rather than arbitrary dictionaries.

### 5. Construct the model adapter

```python
model = ChatOpenAI(
    model=...,
    temperature=0.2,
    **_provider_kwargs(),
)
```

Configuration comes from:

- `LLM_MODEL`
- `LLM_API_KEY`
- optionally `LLM_API_URL`

If `LLM_API_URL` is supplied, it becomes `base_url`. This permits communication with another provider if that provider implements the relevant OpenAI-compatible API.

A new `ChatOpenAI` object is constructed for each `/chat` request. It does not hold conversation state; the conversation is passed explicitly.

### 6. Define the prompt

```python
prompt = ChatPromptTemplate.from_messages(
    [
        ("system", "You are a concise, helpful assistant."),
        MessagesPlaceholder("messages"),
    ]
)
```

Conceptually, this means:

```text
System: You are a concise, helpful assistant.

Insert the supplied conversation here.
```

`MessagesPlaceholder("messages")` requires invocation to provide a value named `messages`.

Frontend system messages can also appear inside the inserted conversation, in addition to Papyri's fixed system prompt.

### 7. Compose the prompt and model

```python
chain = prompt | model
```

The `|` operator is part of LangChain Expression Language (LCEL). It is approximately equivalent to:

```python
formatted_prompt = prompt.invoke({"messages": conversation})
response = model.invoke(formatted_prompt)
```

The resulting `chain` is a LangChain `Runnable`:

```text
dictionary input
    ↓
ChatPromptTemplate
    ↓
ChatPromptValue / structured messages
    ↓
ChatOpenAI
    ↓
AIMessage
```

### 8. Invoke the chain asynchronously

```python
response = await chain.ainvoke({"messages": conversation})
```

Papyri uses `ainvoke()` because the FastAPI endpoint is asynchronous.

The result is normally an `AIMessage`. Papyri flattens its content into a string and returns:

```python
{"text": _stringify_model_content(response.content)}
```

The frontend consequently receives:

```json
{
  "text": "The model's answer"
}
```

## How LangChain interacts with FastAPI

The FastAPI integration is in `backend/src/papyri_backend/server.py`.

### Backend selection

At module import time:

```python
if os.getenv("USE_PI"):
    answer_with_chat = answer_with_chat_pi
else:
    answer_with_chat = answer_with_chat_langchain
```

Therefore:

- if `USE_PI` is absent or empty, `/chat` uses LangChain
- if `USE_PI` contains any non-empty string, `/chat` uses Pi

Values such as `"false"` and `"0"` are non-empty and therefore also select Pi. The selection happens when `server.py` is imported; changing the variable while the server is running does not switch the backend.

### Request and response models

FastAPI expects:

```json
{
  "messages": [...]
}
```

The array must contain at least one item:

```python
class ChatRequest(BaseModel):
    messages: list[Any] = Field(min_length=1)
```

Detailed message validation happens later in `normalize_messages()`.

The endpoint is:

```python
@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    return await answer_with_chat(request.messages)
```

The complete request flow is:

```text
assistant-ui frontend
    │ POST /chat {"messages": [...]}
    ▼
FastAPI /chat
    ▼
answer_with_chat_langchain()
    ▼
normalize messages
    ▼
ChatPromptTemplate | ChatOpenAI
    ▼
OpenAI-compatible HTTP API
    ▼
AIMessage
    ▼
{"text": "..."}
    ▼
FastAPI validates ChatResponse
    ▼
frontend renders the text
```

The frontend call is in `frontend/src/assistantRuntime.tsx:17`.

FastAPI is not using LangServe here. It calls an ordinary Python function that happens to use LangChain.

## LangChain's interface versus `PiConnector`

### Minimal interface required by the existing chain

Because the model appears here:

```python
prompt | model
```

the object on the right must be a LangChain-compatible `Runnable`. Important Runnable operations include:

```python
invoke(input)
await ainvoke(input)
stream(input)
astream(input)
batch(inputs)
abatch(inputs)
```

This file specifically relies on asynchronous invocation. `PiConnector` is not a Runnable and does not implement `ainvoke()`.

### Native LangChain chat-model interface

To make Pi a native LangChain chat model, an adapter would normally derive from `BaseChatModel`. Its required pieces include:

```python
@property
def _llm_type(self) -> str:
    ...

def _generate(
    self,
    messages: list[BaseMessage],
    stop: list[str] | None = None,
    ...
) -> ChatResult:
    ...
```

LangChain supplies much of the public Runnable interface around those methods.

For proper asynchronous and streaming support, an implementation would normally also provide:

```python
async def _agenerate(...) -> ChatResult
def _stream(...) -> Iterator[ChatGenerationChunk]
async def _astream(...) -> AsyncIterator[ChatGenerationChunk]
```

Tool-enabled agents may additionally expect `bind_tools(...)`, although the current `chat_langchain.py` does not use tools.

## What `PiConnector` provides instead

`PiConnector`, defined at `backend/src/papyri_backend/pi_agent.py:275`, is a low-level, stateful subprocess client. It:

1. starts `pi --mode rpc`
2. writes newline-delimited JSON commands to stdin
3. reads newline-delimited JSON events from stdout
4. dispatches streaming and tool events to a message processor
5. keeps the Pi process and its session alive

Its main interface is:

```python
send(input: str)
process_events()
chat()
teardown()
```

This differs substantially from LangChain:

| Concern | LangChain chat model | Current `PiConnector` |
|---|---|---|
| Input | `list[BaseMessage]` / prompt value | one plain string |
| Output | returned `AIMessage` or `ChatResult` | events sent to a processor |
| Async API | `ainvoke()` / `_agenerate()` | none |
| Streaming | iterator of structured chunks | synchronous stdout event loop |
| Composition | implements `Runnable` | not composable |
| Completion | method returns a result | waits for `agent_settled` |
| Errors | raised through model call | mostly printed or processed |
| Configuration | model/provider fields | CLI arguments and RPC commands |
| State | context usually supplied per call | subprocess maintains a session |
| Concurrency | independent model calls | one mutable process/stdout reader |

The largest mismatch is that `PiConnector` does not return an assistant answer. `send()` writes to stdin, while `process_events()` forwards events to a message processor.

The API-oriented processor currently contains empty placeholders, so nothing collects Pi's message chunks into a final result such as:

```python
{"text": "answer"}
```

## Current state of `chat_pi.py`

`backend/src/papyri_backend/chat_pi.py` is currently a stub:

```python
async def answer_with_chat(raw_messages: list[Any]) -> dict[str, str]: ...
```

An ellipsis used as a function body does not implement anything; the function returns `None`. When `USE_PI` is enabled, the Pi backend therefore does not satisfy FastAPI's expected response:

```python
class ChatResponse(BaseModel):
    text: str
```

The LangChain backend is operational, while the Pi backend integration remains unfinished.

## Integration approaches

### Option A: Integrate Pi directly with FastAPI

This is the simpler option if Papyri does not need LangChain composition around Pi.

Implement `chat_pi.answer_with_chat()` so it:

1. normalizes incoming messages
2. identifies the latest user message
3. obtains a Pi session for the current user or thread
4. sends the message
5. consumes events until `agent_settled`
6. accumulates assistant text
7. returns `{"text": accumulated_text}`

This also requires:

- a real API message processor
- asynchronous or thread-offloaded subprocess I/O
- cancellation handling
- error propagation
- locking or one Pi process per conversation
- process cleanup during FastAPI shutdown

### Option B: Make Pi a LangChain model

Create an adapter such as:

```python
class PiChatModel(BaseChatModel):
    @property
    def _llm_type(self) -> str:
        return "pi"

    def _generate(self, messages, stop=None, **kwargs) -> ChatResult:
        ...
```

The adapter would perform:

```text
LangChain BaseMessage list
    ↓
serialize or select messages for Pi
    ↓
PiConnector.send()
    ↓
consume Pi RPC events
    ↓
assemble assistant text
    ↓
AIMessage + ChatGeneration + ChatResult
```

The existing chain could then use:

```python
model = PiChatModel(...)
chain = prompt | model
response = await chain.ainvoke({"messages": conversation})
```

This requires more work, but permits Pi to participate in LangChain prompts, tracing, callbacks, batching, and potentially tool-oriented chains.

## Conversation-state complication

The LangChain and Pi paths have different state models.

The current LangChain path is effectively stateless:

```text
request contains history → history sent to model → request ends
```

Pi is session-oriented:

```text
persistent subprocess → send new message → Pi remembers earlier interaction
```

Sending the complete frontend history to an existing Pi session on every request could duplicate previous messages. A Pi integration should deliberately choose one model:

- **Stateful Pi:** send only the newest user message and associate each frontend thread with a Pi session.
- **Stateless/reconstructed Pi:** create or reset a session and replay selected history for every request.

The stateful approach is more natural for Pi, but requires session ownership, cleanup, and concurrency management.

The existing global `PI_AGENT` singleton would not safely support multiple simultaneous users. Concurrent FastAPI requests could write to and read from the same subprocess and mix their events.

## Summary

In this project, LangChain is a thin composition layer:

```text
normalized frontend messages
    → LangChain message classes
    → prompt template
    → ChatOpenAI
    → text response
```

FastAPI is independent of LangChain. It calls `answer_with_chat()` and requires a dictionary containing `text`.

`PiConnector` is currently a synchronous, stateful RPC subprocess controller rather than a LangChain model or Runnable. It lacks structured message input, returned model results, asynchronous invocation, LangChain streaming types, and safe concurrent request handling. It can either be adapted directly to FastAPI or wrapped as a LangChain `BaseChatModel`; direct FastAPI integration is the simpler initial approach.
