import type { ReactNode } from "react";
import {
  AssistantRuntimeProvider,
  useLocalRuntime,
  type ChatModelAdapter,
  type ThreadAssistantMessagePart
} from "@assistant-ui/react";

const apiUrl = import.meta.env.VITE_API_URL ?? "http://localhost:3001";
type ChatResponse = {
  text: string;
  reasoning?: string;
};

const modelAdapter: ChatModelAdapter = {
  async run({ messages, abortSignal }) {
    const response = await fetch(`${apiUrl}/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ messages }),
      signal: abortSignal
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(errorText || `Request failed with ${response.status}`);
    }

    const data = (await response.json()) as ChatResponse;
    const content: ThreadAssistantMessagePart[] = [];

    if (data.reasoning?.trim()) {
      content.push({
        type: "reasoning",
        text: data.reasoning
      });
    }

    content.push({
      type: "text",
      text: data.text
    });

    return {
      content
    };
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
