"""Provide a connector for deepagents agents driven by LangGraph's v3 event stream."""

import json
import os
import re
import uuid
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml
from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend
from langchain.agents.middleware import (
    LLMToolSelectorMiddleware,
    SummarizationMiddleware,
)
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_postgres import PGVector
from langchain_text_splitters import RecursiveCharacterTextSplitter
from typing import Any
from pathlib import Path
import yaml


from .base import BaseAgent
from .exceptions import InvalidDecision, StaleDecision
from .utils import utils


# Models that reason inline mark the trace as ordinary answer text instead of
# emitting reasoning events. The tags are matched leniently because whitespace
# and casing vary between deployments.
_THINK_OPEN = re.compile(r"<\s*think\s*>", re.IGNORECASE)
_THINK_CLOSE = re.compile(r"</\s*think\s*>", re.IGNORECASE)


class RetrievalAgent:
    def __init__(
        self,
        embeddingmodel: str,
        ps_connection: str | None = None,
        embeddings_type: str = "langchain_huggingface.HuggingFaceEmbeddings",
        store_kwargs: dict[str, Any] | None = None,
        embeddings_kwargs: dict[str, Any] | None = None,
        similarity_search_kwargs: dict[str, Any] | None = None,
        mmr_search_kwargs: dict[str, Any] | None = None,
    ):
        """_summary_

        Args:
            embeddingmodel (str): _description_
            ps_connection (str | None, optional): _description_. Defaults to None.
            embeddings_type (str, optional): _description_. Defaults to "langchain_huggingface.HuggingFaceEmbeddings".
            store_kwargs (dict[str, Any] | None, optional): _description_. Defaults to None.
            embeddings_kwargs (dict[str, Any] | None, optional): _description_. Defaults to None.
            similarity_search_kwargs (dict[str, Any] | None, optional): _description_. Defaults to None.
            mmr_search_kwargs (dict[str, Any] | None, optional): _description_. Defaults to None.

        Raises:
            ValueError: _description_
        """
        ps_conn = ps_connection or os.getenv("POSTGRES_URL")

        if ps_conn is None:
            raise ValueError(
                "Error, no connection to postgres database given. Either give 'ps_connection' or set the 'POSTGRES_URL' environment variable. "
            )

        embed_tp = utils.load_type(embeddings_type)
        self.embeddings = embed_tp(
            model_name=embeddingmodel, **(embeddings_kwargs or {})
        )
        self.store = PGVector(
            embeddings=self.embeddings, connection=ps_connection, **(store_kwargs or {})
        )
        self.similarity_search_kwargs = {}
        for k, v in (similarity_search_kwargs or {}).items():
            self.similarity_search_kwargs[k] = utils._process_config(v)

        self.mmr_search_kwargs = {}
        for k, v in (mmr_search_kwargs or {}).items():
            self.mmr_search_kwargs[k] = utils._process_config(v)

    def similarity_search(self, query: str) -> list[Document]:
        return self.store.similarity_search(query, **self.similarity_search_kwargs)

    def mmr_search(self, query: str) -> list[Document]:
        return self.store.max_marginal_relevance_search(query, **self.mmr_search_kwargs)

    def similarity_search_by_vec(self, vec: list[float]) -> list[Document]:
        return self.store.similarity_search_by_vector(
            vec, **self.similarity_search_kwargs
        )

    def mmr_search_by_vec(self, vec: list[float]) -> list[Document]:
        return self.store.max_marginal_relevance_search_by_vector(
            vec, **self.mmr_search_kwargs
        )

    @staticmethod
    def _format_documents(documents: list[Document]) -> str:
        """Render retrieved documents as the text of a chat answer.

        Args:
            documents: The documents a search returned, in the order the store
                ranked them.

        Returns:
            One markdown block per document, carrying its rank, whatever
            identifies its source in the metadata, and its content. An empty
            result is reported as such, because a chat answer cannot be empty.
        """
        if not documents:
            return "No matching passages were found."

        blocks = []
        for rank, document in enumerate(documents, start=1):
            metadata = document.metadata or {}
            source = metadata.get("source") or metadata.get("id") or "unknown source"
            blocks.append(f"**{rank}. {source}**\n\n{document.page_content.strip()}")

        return "\n\n---\n\n".join(blocks)

    def run_single_turn(self, message) -> dict[str, Any]:
        """Answer one incoming chat message with a plain retrieval.

        No model runs here, so the turn has neither a reasoning trace nor an
        interrupt to report; both fields are still present, because the client
        reads the same answer shape whichever mode produced it.

        Args:
            message: An incoming chat message, whose first content part carries
                the user's text.

        Returns:
            The retrieved passages as the answer's ``text``, an empty
            ``reasoning`` trace and no ``interrupt``. A failed search travels as
            chat output in place of the answer, as it does for the deep agent.
        """
        query = message["content"][0]["text"]

        try:
            documents = self.similarity_search(query)
        except Exception as exc:
            text = f"The retrieval failed: {exc}"
        else:
            text = self._format_documents(documents)

        return {"text": text, "reasoning": "", "interrupt": None}


class LangChainAgent(BaseAgent):
    """Connect to a deepagents agent and stream its events."""

    def __init__(
        self,
        kwargs: Mapping[str, Any] | None = None,
    ):
        """Build a deep agent.

        Args:
            kwargs: Keyword arguments for ``create_deep_agent``, such as
                ``model``, ``tools``, ``system_prompt`` and ``interrupt_on``.
                ``middleware`` and ``permissions`` are given as
                ``{"type": ..., "kwargs": {...}}`` entries and instantiated here.
                A ``checkpointer`` is added when none is supplied, because
                interrupts cannot be resumed without one.
        """

        agent_kwargs = dict(kwargs or {})
        agent_kwargs.setdefault(
            "checkpointer", InMemorySaver()
        )  # TODO: make the checkpointer configurable

        model = agent_kwargs.get("model")
        if isinstance(model, Mapping):
            model_kwargs = dict(model.get("kwargs") or {})
            model_kwargs.setdefault("model", os.getenv("LLM_MODEL"))
            model_kwargs.setdefault("base_url", os.getenv("LLM_API_URL"))
            model_kwargs.setdefault("api_key", os.getenv("LLM_API_KEY", "EMPTY"))
            agent_kwargs["model"] = model["type"](**model_kwargs)

        agent_kwargs["middleware"] = [
            self._build_middleware(middleware_def, agent_kwargs.get("model"))
            for middleware_def in agent_kwargs.get("middleware") or []
        ]

        if "permissions" in agent_kwargs:
            agent_kwargs["permissions"] = [
                self._build_permission(permission_def)
                for permission_def in agent_kwargs["permissions"] or []
            ]

        if "backend" in agent_kwargs:
            backend = self._build_backend(agent_kwargs["backend"])
            agent_kwargs["backend"] = backend

        super().__init__(**agent_kwargs)

        self.agent = create_deep_agent(**agent_kwargs)
        self.thread_id = str(uuid.uuid4())
        self._pending: Mapping[str, Any] | Command | None = None
        self._run: Any | None = None

        self._reset_buffers()

    def _reset_buffers(self):
        """Clear the buffers a turn's output is collected into."""
        self.full_answer = ""
        self.full_reasoning = ""
        self.full_error = ""

    def _collect_answer(self, message: str):
        """Collect streamed answer text, splitting off an inline reasoning trace.

        Args:
            message: The next chunk of streamed answer text.
        """

        # The trace always comes first, so ``</think>`` is the single point at
        # which the stream switches from reasoning to answer. Text accumulates in
        # the answer buffer until then, which leaves a model that never reasons
        # inline with nothing to do. The tag is looked for in the accumulated
        # buffer rather than in the message, because a stream chunk can end in the
        # middle of it.

        self.full_answer += message

        close_tag = _THINK_CLOSE.search(self.full_answer)
        if close_tag is None:
            return

        # The opening tag is dropped when the model sent one; deployments whose
        # chat template pre-fills it start the trace without one.
        reasoning_part = _THINK_OPEN.sub("", self.full_answer[: close_tag.start()], 1)
        self.full_reasoning += reasoning_part
        self.full_answer = self.full_answer[close_tag.end() :]

    def _collect_reasoning(self, message: str):
        """Collect a chunk of the model's reasoning trace.

        Args:
            message: The next chunk of streamed reasoning text.
        """
        self.full_reasoning += message

    def _collect_error(self, message: str):
        """Collect an error that takes the place of the turn's answer.

        Args:
            message: The error text to report back to the client.
        """
        self.full_error += message

    def _collect_tool_call(self, tool_call: Mapping[str, Any]):
        """Render one tool call into the answer buffer.

        Args:
            tool_call: The call the model made, carrying its ``name`` and ``args``.
        """
        name = tool_call.get("name")
        args = tool_call.get("args") or {}
        body = "\n".join(f"{k}: {v}" for k, v in args.items())
        self._collect_answer(f"\n\n````\nUsing tool: {name}\n{body}\n````\n\n")

    @staticmethod
    def _build_middleware(middleware_def: Mapping[str, Any], model: Any) -> Any:
        """Build one middleware from its config entry.

        Args:
            middleware_def: A ``{"type": ..., "kwargs": {...}}`` mapping, where
                the type is a middleware class such as
                ``langchain.agents.middleware.TodoListMiddleware``.
            model: The agent's chat model, handed to the middlewares that run a
                model of their own instead of the agent's.

        Returns:
            The instantiated middleware, ready to hand to ``create_deep_agent``.
        """
        middleware_type = utils.load_type(middleware_def["type"])
        middleware_kwargs = dict(middleware_def.get("kwargs") or {})

        # some middleware needs a model being passed explicitly
        if middleware_type in (SummarizationMiddleware, LLMToolSelectorMiddleware):
            middleware_kwargs.setdefault("model", model)

        return middleware_type(**middleware_kwargs)

    @staticmethod
    def _build_permission(permission_def: Mapping[str, Any]) -> Any:
        """Build one filesystem access rule from its config entry.

        Args:
            permission_def: A ``{"type": ..., "kwargs": {...}}`` mapping, where
                the type is a permission class such as
                ``deepagents.FilesystemPermission``.

        Returns:
            The instantiated rule, ready to hand to ``create_deep_agent``.
        """
        permission_type = utils.load_type(permission_def["type"])
        permission_kwargs = dict(permission_def.get("kwargs") or {})

        # FilesystemPermission insists on absolute paths and rejects "~", so the
        # shell-style shorthands a config is written with are resolved here.
        if "paths" in permission_kwargs:
            permission_kwargs["paths"] = [
                os.path.expanduser(os.path.expandvars(path))
                for path in permission_kwargs["paths"]
            ]

        return permission_type(**permission_kwargs)

    @staticmethod
    def _build_backend(backend_specs: Mapping[str, Mapping[str, Any]]) -> Any:

        processed_backend_specs = {}
        for k, v in backend_specs.items():
            processed_backend_specs[k] = utils._process_config(v)

        default = processed_backend_specs["default_typename"](
            **processed_backend_specs.get("default_kwargs", {})
        )

        routes = {}
        for route, backend_def in processed_backend_specs["routes"].items():
            routes[route] = backend_def["typename"](**backend_def.get("kwargs", {}))

        return CompositeBackend(default=default, routes=routes)

    @property
    def _config(
        self,
    ) -> dict[str, Any]:  # TODO: why is this needed, I am not sure this does much
        """Return the runnable config binding a run to the current thread.

        Returns:
            A config carrying the thread id the checkpointer keys state on.
        """
        return {"configurable": {"thread_id": self.thread_id}}

    def _process_input_message(self, user_input: str):
        """Convert user input into an input payload.

        Args:
            user_input: Raw input entered by the user.

        Returns:
            An input payload for the underlying langraph, or ``None`` for an unsupported wrapper
            command.
        """
        command = user_input.strip().split(" ", 1)[0]

        if command.startswith(("\\", "/")):
            return None  # unsupported wrapper command

        return {"messages": [{"role": "user", "content": user_input}]}

    def send_message(self, input: str):
        """Stage user input for the next run.

        The payload is held until ``get_answers`` consumes it, because a v3
        run is driven by the caller's iteration rather than by writing to a
        process.

        Args:
            input: Raw user input to convert into a graph input payload.
        """
        to_send = self._process_input_message(input)

        if to_send is None:
            self._collect_error(f"{input} is not a processable input")
        else:
            self._pending = to_send

    def get_answers(self):
        """Start a run for the staged payload and yield its messages.

        Iterating the yielded streams is what drives the run forward.

        Yields:
            One ``ChatModelStream`` per model call in the run.
        """
        if self._pending is None:
            return

        # This takes care of the interleaving of steering messages
        # TODO: looks weird. not sure this is  necessary
        pending, self._pending = (
            self._pending,
            None,
        )

        # TODO: I am not too happy that this here sends requests. I think this architecture is way too complicated for what I am trying to do
        self._run = self.agent.stream_events(
            pending,
            config=self._config,
            version="v3",  # TODO: is this necessary?
        )

        yield from self._run.messages  # answer buffer

    def _pending_interrupt(self):
        """Return the interrupt the run is paused on, if any.

        The checkpointer is the single source of truth here rather than the
        retained run, because a pause outlives the request that produced it.

        Returns:
            The pending ``Interrupt``, or ``None`` when nothing is paused.
        """
        interrupts = self.agent.get_state(self._config).interrupts
        return interrupts[0] if interrupts else None

    @staticmethod
    def _interrupt_view(interrupt) -> dict[str, Any]:
        """Describe a pending interrupt for a client that has to answer it.

        Args:
            interrupt: The ``Interrupt`` the run is paused on.

        Returns:
            The interrupt's id and one entry per paused action, carrying the
            action's name, the arguments the model asked for, and the decisions
            allowed for that action specifically.
        """
        request = interrupt.value
        return {
            "id": interrupt.id,
            "actions": [
                {
                    "name": action["name"],
                    "args": action.get("args") or {},
                    "allowed_decisions": list(config["allowed_decisions"]),
                }
                for action, config in zip(
                    request["action_requests"], request["review_configs"]
                )
            ],
        }

    def _process_interrupt(self, payload: Mapping[str, Any]):
        """Answer the pending interrupt and stage the resume for the next run.

        The graph raises ``ValueError`` for a decision count that does not match
        the paused actions, or for a type the action does not allow. Both are
        checked here instead, so a bad reply is a rejected request rather than a
        failed run.

        Args:
            payload: A decision reply, carrying ``interrupt_id`` and one entry in
                ``decisions`` per paused action, in the same order.

        Raises:
            StaleDecision: Nothing is paused, or the reply names another interrupt.
            InvalidDecision: The reply has the wrong number of decisions, or one
                the action does not allow.
        """
        interrupt = self._pending_interrupt()
        if interrupt is None:
            raise StaleDecision("No decision is pending.")

        if payload.get("interrupt_id") != interrupt.id:
            raise StaleDecision(
                "This decision answers an interrupt that is no longer pending."
            )

        request = interrupt.value
        action_requests = request["action_requests"]
        review_configs = request["review_configs"]
        replies = payload.get("decisions") or []

        if len(replies) != len(action_requests):
            raise InvalidDecision(
                f"Expected {len(action_requests)} decisions, got {len(replies)}."
            )

        decisions = [
            self._build_decision(reply, action, config)
            for reply, action, config in zip(replies, action_requests, review_configs)
        ]

        self._pending = Command(resume={"decisions": decisions})

    @staticmethod
    def _build_decision(
        reply: Mapping[str, Any],
        action: Mapping[str, Any],
        config: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Translate one client reply into the decision the middleware expects.

        The edited action's name is taken from the paused action rather than from
        the reply, so a client cannot redirect a decision at a different tool.

        Args:
            reply: One entry of the client's ``decisions`` list.
            action: The paused action the reply answers.
            config: That action's review policy.

        Returns:
            A decision payload for ``HumanInTheLoopMiddleware``.

        Raises:
            InvalidDecision: The type is missing, not allowed for this action, or
                carries the wrong body for its kind.
        """
        decision_type = reply.get("type")
        allowed = config["allowed_decisions"]

        if decision_type not in allowed:
            raise InvalidDecision(
                f"Decision '{decision_type}' is not allowed for "
                f"'{action['name']}'. Expected one of {list(allowed)}."
            )

        # TODO: this hardcodes possible decisions, which are not necessarily always the same.

        if decision_type == "approve":
            return {"type": "approve"}

        if decision_type == "edit":
            args = reply.get("args")
            if not isinstance(args, dict):
                raise InvalidDecision("An edited action needs its args as an object.")
            return {
                "type": "edit",
                "edited_action": {"name": action["name"], "args": args},
            }

        if decision_type == "reject":
            message = (reply.get("message") or "").strip()
            return (
                {"type": "reject", "message": message}
                if message
                else {"type": "reject"}
            )

        message = (reply.get("message") or "").strip()
        if not message:
            raise InvalidDecision("Responding on behalf of a tool needs a message.")
        return {"type": "respond", "message": message}

    def _process_events_message(self, message):
        """Collect one model message as it streams in.

        Raw protocol events are iterated rather than the ``text`` and
        ``reasoning`` projections, because both projections only finish at the
        end of the message; draining either one would wait for the whole message
        instead of collecting it as it arrives.

        Args:
            message: A ``ChatModelStream`` for a single model call.
        """
        for event in message:
            if event.get("event") != "content-block-delta":
                continue

            delta = event.get("delta") or {}

            if delta.get("type") == "text-delta":
                self._collect_answer(delta.get("text", ""))
            elif delta.get("type") == "reasoning-delta":
                self._collect_reasoning(delta.get("reasoning", ""))

        # TODO: what does this do? really?
        for tool_call in message.tool_calls.get() or []:
            self._collect_tool_call(tool_call)

    def process_events(self):
        """Drive the staged run until it finishes or pauses for a decision.

        A paused run is left paused: the checkpointer holds it until a decision
        arrives on a later turn. Only the prompt is collected here; the decisions
        themselves are not, because a client that answers the interrupt reads
        them from the response's ``interrupt`` field, which ``_interrupt_view``
        builds from the checkpointer rather than from buffered output.
        """
        # implements the control flow for event processing.
        while self._pending is not None:
            for message in self.get_answers():
                self._process_events_message(message)

            if self._run.interrupted:
                self._collect_answer("Please decide how you want to proceed:\n")

    @staticmethod
    def _as_decision(text: str) -> dict[str, Any] | None:
        """Read a message as a decision reply, if that is what it is.

        Decisions travel as the JSON text of an ordinary user message, so every
        message is examined. ``interrupt_id`` is what marks one, because it is
        specific enough that ordinary prose cannot produce it by accident.

        Args:
            text: The incoming message's text.

        Returns:
            The decision payload, or ``None`` for an ordinary message.
        """
        stripped = text.strip()
        if not stripped.startswith("{"):
            return None

        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError:
            return None

        if isinstance(payload, dict) and "interrupt_id" in payload:
            return payload
        return None

    def run_single_turn(self, message) -> dict[str, Any]:
        """Run one turn for a single incoming message.

        A message that carries a decision answers the paused run instead of
        starting a new one.

        Args:
            message: An incoming chat message, whose first content part carries
                the user's text.

        Returns:
            The agent's ``text`` answer and its ``reasoning`` trace, either of
            which may be empty, plus the ``interrupt`` the run is now paused on,
            if any. A run that failed leaves no answer, so the collected error
            takes its place.

        Raises:
            StaleDecision: The message answered an interrupt that is not pending.
            InvalidDecision: The decision was malformed or is not allowed.
        """
        text = message["content"][0]["text"]
        decision = self._as_decision(text)

        # Raised before the run is touched, so a refused decision leaves the
        # graph paused exactly as it was.
        if decision is not None:
            self._process_interrupt(decision)
        else:
            self.send_message(text)

        try:
            self.process_events()
        except Exception as exc:
            self._pending = None
            self._collect_error(f"The agent run failed: {exc}")

        # Run failures deliberately travel as chat output during local
        # development. Prefer them over incomplete text emitted before the
        # failure (for example, a tool-call announcement).
        answer_text = self.full_error.strip() or self.full_answer.strip()
        reasoning_text = self.full_reasoning.strip()

        interrupt = self._pending_interrupt()

        answer = {
            "text": answer_text,
            "reasoning": reasoning_text,
            "interrupt": self._interrupt_view(interrupt) if interrupt else None,
        }
        self._reset_buffers()
        return answer

    def teardown(self) -> int:
        """Stop a run that was left partially drained.

        Returns:
            Zero. The agent runs in this process, so there is no exit code to
            report.
        """
        if self._run is not None:
            self._run.abort()
            self._run = None

        return 0


def make_langchain_retriever(
    path: str,
) -> RetrievalAgent:

    with open(Path(path).resolve(), "r") as f:
        config = yaml.safe_load(f)

    return RetrievalAgent(**config)


def make_langchain_deepagent(path: str) -> LangChainAgent:
    """TODO

    Args:
        path (str): TODO

    Returns:
        _type_: TODO
    """

    with open(Path(path).resolve(), "r") as f:
        config = yaml.safe_load(f)

    # recurse

    cfg = {}
    for k, v in config.items():
        cfg[k] = utils._process_config(v)

    return LangChainAgent(**cfg)
