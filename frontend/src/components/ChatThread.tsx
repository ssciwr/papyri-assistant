import {
  createContext,
  forwardRef,
  useContext,
  useEffect,
  useState,
  type ComponentProps,
  type ComponentPropsWithoutRef
} from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  ComposerPrimitive,
  MessagePrimitive,
  ThreadPrimitive,
  useAuiState,
  type EmptyMessagePartComponent,
  type ReasoningMessagePartProps,
  type TextMessagePartComponent
} from "@assistant-ui/react";
import { readDecision, type DecisionReply } from "../decisionGate";
import {
  formatContextUsage,
  formatInputOutputUsage,
  type ModelUsage,
  type TokenUsage
} from "../tokenUsage";

type MarkdownContentProps = ComponentPropsWithoutRef<"div">;
type MessageContentComponents = NonNullable<
  ComponentProps<typeof MessagePrimitive.Content>["components"]
>;
const StreamReasoningContext = createContext(false);
const EMPTY_MODEL_USAGE: ModelUsage[] = [];

const MarkdownContent = forwardRef<HTMLDivElement, MarkdownContentProps>(
  ({ children, className, ...props }, ref) => {
    const markdown = typeof children === "string" ? children : "";
    const classNames = ["markdown-content", className]
      .filter(Boolean)
      .join(" ");

    return (
      <div {...props} ref={ref} className={classNames}>
        <ReactMarkdown remarkPlugins={[remarkGfm]}>
          {markdown}
        </ReactMarkdown>
      </div>
    );
  }
);

MarkdownContent.displayName = "MarkdownContent";

function StreamingIndicator() {
  return <span className="message-streaming-indicator">●</span>;
}

function DecisionSummary({ decisions }: { decisions: DecisionReply[] }) {
  return (
    <div className="decision-summary">
      {decisions.map((decision, index) => (
        <p className="decision-summary-item" key={index}>
          <span className="decision-summary-type">{decision.type}</span>
          {decision.message && (
            <span className="decision-summary-message">
              {" — "}
              {decision.message}
            </span>
          )}
        </p>
      ))}
    </div>
  );
}

const MarkdownText: TextMessagePartComponent = ({ text, status }) => {
  // assistant-ui adds a synthetic empty text part while a response whose last
  // real part is reasoning is still running. The reasoning panel already owns
  // that progress state, so rendering the empty part would leave a stray dot
  // below the panel before the real answer begins.
  if (!text.trim() && status.type === "running") {
    return null;
  }

  // A decision travels as the JSON text of a user message, so it is summarised
  // here rather than rendered as the payload it literally is.
  const decisions = readDecision(text);

  if (decisions) {
    return <DecisionSummary decisions={decisions} />;
  }

  return (
    <div className="message-part message-part-text">
      <MarkdownContent>{text}</MarkdownContent>
      {status.type === "running" && <StreamingIndicator />}
    </div>
  );
};

function ReasoningOutput({
  text,
  status
}: ReasoningMessagePartProps) {
  const streamReasoning = useContext(StreamReasoningContext);
  const isReasoningRunning = status.type === "running";
  const isResponseRunning = useAuiState(
    (state) => state.message.status?.type === "running"
  );

  return (
    <ReasoningBox
      initiallyOpen={streamReasoning}
      isReasoningRunning={isReasoningRunning}
      isResponseRunning={isResponseRunning}
      text={text}
    />
  );
}

function ReasoningBox({
  initiallyOpen,
  isReasoningRunning,
  isResponseRunning,
  text
}: {
  initiallyOpen: boolean;
  isReasoningRunning: boolean;
  isResponseRunning: boolean;
  text: string;
}) {
  const [isOpen, setIsOpen] = useState(initiallyOpen);
  const modelUsage = useAuiState((state) => {
    const value = state.message.metadata.custom.modelUsage;
    return Array.isArray(value) ? (value as ModelUsage[]) : EMPTY_MODEL_USAGE;
  });
  const latestUsage = modelUsage.at(-1);

  useEffect(() => {
    if (!isResponseRunning) {
      setIsOpen(false);
    }
  }, [isResponseRunning]);

  return (
    <details
      className="reasoning-output"
      onToggle={(event) => setIsOpen(event.currentTarget.open)}
      open={isOpen}
    >
      <summary className="reasoning-summary">
        Reasoning
        {isResponseRunning && (
          <span className="reasoning-summary-status"> in progress...</span>
        )}
        {latestUsage && (
          <span className="reasoning-summary-usage">
            {" · "}
            {formatContextUsage(latestUsage)}
          </span>
        )}
      </summary>
      <div className="reasoning-content">
        <MarkdownContent>{text}</MarkdownContent>
        {isReasoningRunning && <StreamingIndicator />}
      </div>
    </details>
  );
}

const EmptyReasoning: EmptyMessagePartComponent = ({ status }) => {
  const streamReasoning = useContext(StreamReasoningContext);

  return status.type === "running" ? (
    <ReasoningBox
      initiallyOpen={streamReasoning}
      isReasoningRunning
      isResponseRunning
      text=""
    />
  ) : null;
};

const messageContentComponents = {
  Empty: EmptyReasoning,
  Text: MarkdownText,
  Reasoning: ReasoningOutput
} satisfies MessageContentComponents;

export function ChatThread({
  streamReasoning
}: {
  streamReasoning: boolean;
}) {
  return (
    <StreamReasoningContext.Provider value={streamReasoning}>
      <ThreadPrimitive.Root className="thread-root">
        <ThreadPrimitive.Viewport className="thread-viewport">
          <ThreadPrimitive.Messages>
            {({ message }) => <ChatMessage role={message.role} />}
          </ThreadPrimitive.Messages>
          <ThreadPrimitive.ViewportFooter className="thread-footer">
            <Composer />
          </ThreadPrimitive.ViewportFooter>
        </ThreadPrimitive.Viewport>
      </ThreadPrimitive.Root>
    </StreamReasoningContext.Provider>
  );
}

function ChatMessage({ role }: { role: string }) {
  return (
    <MessagePrimitive.Root className={`message message-${role}`}>
      <div className="message-label">{role}</div>
      <div className="message-body">
        <MessagePrimitive.Content components={messageContentComponents} />
        {role === "assistant" && <FinalTokenUsage />}
      </div>
    </MessagePrimitive.Root>
  );
}

function FinalTokenUsage() {
  const usage = useAuiState(
    (state) =>
      (state.message.metadata.custom.tokenUsage as TokenUsage | undefined) ??
      null
  );
  const isRunning = useAuiState(
    (state) => state.message.status?.type === "running"
  );

  if (isRunning || !usage || usage.total_tokens === 0) {
    return null;
  }

  return (
    <div
      className="message-token-usage"
      title={`${usage.input_tokens.toLocaleString()} total input tokens, ${usage.output_tokens.toLocaleString()} output tokens`}
    >
      {usage.total_tokens.toLocaleString()} tokens
      <span aria-hidden="true"> · </span>
      {formatInputOutputUsage(usage)}
    </div>
  );
}

function Composer() {
  return (
    <ComposerPrimitive.Root className="composer">
      <ComposerPrimitive.Input
        className="composer-input"
        placeholder="Ask a question..."
        rows={1}
      />
      <ComposerPrimitive.Send className="send-button">
        Send
      </ComposerPrimitive.Send>
    </ComposerPrimitive.Root>
  );
}
