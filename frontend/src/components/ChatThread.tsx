import {
  forwardRef,
  type ComponentProps,
  type ComponentPropsWithoutRef
} from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  ComposerPrimitive,
  MessagePrimitive,
  ThreadPrimitive,
  type ReasoningMessagePartComponent,
  type TextMessagePartComponent
} from "@assistant-ui/react";

type MarkdownContentProps = ComponentPropsWithoutRef<"div">;

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

const MarkdownText: TextMessagePartComponent = ({ text, status }) => (
  <div className="message-part message-part-text">
    <MarkdownContent>{text}</MarkdownContent>
    {status.type === "running" && <StreamingIndicator />}
  </div>
);

const ReasoningOutput: ReasoningMessagePartComponent = ({ text, status }) => (
  <details className="reasoning-output">
    <summary className="reasoning-summary">Reasoning</summary>
    <div className="reasoning-content">
      <MarkdownContent>{text}</MarkdownContent>
      {status.type === "running" && <StreamingIndicator />}
    </div>
  </details>
);

const messageContentComponents = {
  Text: MarkdownText,
  Reasoning: ReasoningOutput
} satisfies NonNullable<
  ComponentProps<typeof MessagePrimitive.Content>["components"]
>;

export function ChatThread() {
  return (
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
  );
}

function ChatMessage({ role }: { role: string }) {
  return (
    <MessagePrimitive.Root className={`message message-${role}`}>
      <div className="message-label">{role}</div>
      <div className="message-body">
        <MessagePrimitive.Content components={messageContentComponents} />
      </div>
    </MessagePrimitive.Root>
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
