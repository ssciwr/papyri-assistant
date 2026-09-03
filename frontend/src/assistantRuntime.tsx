import type { ReactNode } from "react";
import {
  AssistantRuntimeProvider,
  useLocalRuntime,
  type ChatModelAdapter,
  type ThreadAssistantMessagePart
} from "@assistant-ui/react";

import { requestDecision, type PendingInterrupt } from "./decisionGate";

export const apiUrl = import.meta.env.VITE_API_URL ?? "http://localhost:3001";
type ChatStreamEvent =
  | {
      type: "text" | "reasoning" | "replace";
      content: string;
    }
  | {
      type: "done";
      interrupt?: PendingInterrupt | null;
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
    let text = "";
    let reasoning = "";
    let completed = false;

    const parseEvent = (line: string): ChatStreamEvent => {
      try {
        const event = JSON.parse(line) as Partial<ChatStreamEvent>;

        if (
          event.type !== "text" &&
          event.type !== "reasoning" &&
          event.type !== "replace" &&
          event.type !== "done"
        ) {
          throw new Error("missing stream fields");
        }

        if (
          event.type !== "done" &&
          (!("content" in event) || typeof event.content !== "string")
        ) {
          throw new Error("missing stream content");
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

    const asContent = (): ThreadAssistantMessagePart[] => {
      const content: ThreadAssistantMessagePart[] = [];

      // Keep a stable reasoning part throughout the response, including before
      // its first token, so the foldable reasoning panel never disappears.
      content.push({ type: "reasoning", text: reasoning });
      if (text || completed) {
        content.push({ type: "text", text });
      }

      return content;
    };

    const handleEvent = (event: ChatStreamEvent) => {
      switch (event.type) {
        case "text":
          text += event.content;
          break;
        case "reasoning":
          reasoning += event.content;
          break;
        case "replace":
          text = event.content;
          break;
        case "done":
          text = text.trim();
          reasoning = reasoning.trim();
          completed = true;
          if (event.interrupt?.actions.length) {
            requestDecision(event.interrupt);
          }
      }

      return { content: asContent() };
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

    if (!completed) {
      throw new Error(
        "The server closed the response before completing the answer."
      );
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
