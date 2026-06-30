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
type ThinkSegment = {
  type: "text" | "reasoning";
  text: string;
};

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

function findThinkTag(
  text: string,
  startIndex: number,
  closing: boolean
): RegExpExecArray | null {
  const tagPattern = closing ? /<\/\s*think\s*>/gi : /<\s*think\s*>/gi;
  tagPattern.lastIndex = startIndex;
  return tagPattern.exec(text);
}

function splitThinkTags(text: string): ThinkSegment[] {
  const segments: ThinkSegment[] = [];
  let index = 0;

  while (index < text.length) {
    const openTag = findThinkTag(text, index, false);
    const closeTag = findThinkTag(text, index, true);

    if (closeTag && (!openTag || closeTag.index < openTag.index)) {
      segments.push({
        type: "reasoning",
        text: text.slice(index, closeTag.index)
      });
      index = closeTag.index + closeTag[0].length;
      continue;
    }

    if (!openTag) {
      segments.push({ type: "text", text: text.slice(index) });
      break;
    }

    if (openTag.index > index) {
      segments.push({ type: "text", text: text.slice(index, openTag.index) });
    }

    const reasoningStart = openTag.index + openTag[0].length;
    const matchingCloseTag = findThinkTag(text, reasoningStart, true);

    if (!matchingCloseTag) {
      segments.push({ type: "reasoning", text: text.slice(reasoningStart) });
      break;
    }

    segments.push({
      type: "reasoning",
      text: text.slice(reasoningStart, matchingCloseTag.index)
    });
    index = matchingCloseTag.index + matchingCloseTag[0].length;
  }

  return segments.filter((segment) => segment.text.trim().length > 0);
}

function StreamingIndicator() {
  return <span className="message-streaming-indicator">●</span>;
}

function FoldedReasoning({ text }: { text: string }) {
  if (!text.trim()) {
    return null;
  }

  return (
    <details className="reasoning-output">
      <summary className="reasoning-summary">Reasoning</summary>
      <div className="reasoning-content">
        <MarkdownContent>{text}</MarkdownContent>
      </div>
    </details>
  );
}

const MarkdownText: TextMessagePartComponent = ({ text, status }) => (
  <div className="message-part message-part-text">
    {splitThinkTags(text).map((segment, index) =>
      segment.type === "reasoning" ? (
        <FoldedReasoning key={`reasoning-${index}`} text={segment.text} />
      ) : (
        <MarkdownContent key={`text-${index}`}>{segment.text}</MarkdownContent>
      )
    )}
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
