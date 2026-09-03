import type { ReactNode } from "react";
import {
  AssistantRuntimeProvider,
  useLocalRuntime,
  type ChatModelAdapter,
  type ThreadAssistantMessagePart
} from "@assistant-ui/react";

import { requestDecision, type PendingInterrupt } from "./decisionGate";

export const apiUrl = import.meta.env.VITE_API_URL ?? "http://localhost:3001";
type ChatStreamEvent = {
  text: string;
  reasoning: string;
  interrupt?: PendingInterrupt | null;
  done: boolean;
};

const modelAdapter: ChatModelAdapter = {
  async *run({ messages, abortSignal }) {
    const response = await fetch(`${apiUrl}/chat`, {
      method: "POST",
      headers: {
        Accept: "application/jsonl",
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ messages }),
      signal: abortSignal
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(errorText || `Request failed with ${response.status}`);
    }

    if (!response.body) {
      throw new Error("The server returned an empty response stream.");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let receivedEvent = false;

    const parseEvent = (line: string): ChatStreamEvent => {
      try {
        const event = JSON.parse(line) as Partial<ChatStreamEvent>;

        if (
          typeof event.text !== "string" ||
          typeof event.reasoning !== "string" ||
          typeof event.done !== "boolean"
        ) {
          throw new Error("missing stream fields");
        }

        return event as ChatStreamEvent;
      } catch (error) {
        throw new Error(
          `The server returned an invalid stream event: ${
            error instanceof Error ? error.message : String(error)
          }`
        );
      }
    };

    const asContent = (
      event: ChatStreamEvent
    ): ThreadAssistantMessagePart[] => {
      const content: ThreadAssistantMessagePart[] = [];

      // Keep a stable reasoning part throughout the response, including before
      // its first token, so the foldable reasoning panel never disappears.
      content.push({ type: "reasoning", text: event.reasoning });
      if (event.text || event.done) {
        content.push({ type: "text", text: event.text });
      }

      return content;
    };

    const handleEvent = (event: ChatStreamEvent) => {
      receivedEvent = true;

      if (event.done && event.interrupt?.actions.length) {
        requestDecision(event.interrupt);
      }

      return { content: asContent(event) };
    };

    while (true) {
      const { done, value } = await reader.read();
      buffer += decoder.decode(value, { stream: !done });

      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";

      for (const line of lines) {
        if (line.trim()) {
          yield handleEvent(parseEvent(line));
        }
      }

      if (done) {
        if (buffer.trim()) {
          yield handleEvent(parseEvent(buffer));
        }
        break;
      }
    }

    if (!receivedEvent) {
      throw new Error("The server closed the response without an answer.");
    }
  }
};

export function RuntimeProvider({ children }: { children: ReactNode }) {
  const runtime = useLocalRuntime(modelAdapter);

  return (
    <AssistantRuntimeProvider runtime={runtime}>
      {children}
    </AssistantRuntimeProvider>
  );
}
