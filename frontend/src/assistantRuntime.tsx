import type { ReactNode } from "react";
import {
  AssistantRuntimeProvider,
  useLocalRuntime,
  type ChatModelAdapter,
  type ThreadAssistantMessagePart
} from "@assistant-ui/react";

import { requestDecision, type PendingInterrupt } from "./decisionGate";
import { type ModelUsage, type TokenUsage } from "./tokenUsage";

export const apiUrl = import.meta.env.VITE_API_URL ?? "http://localhost:3001";

type VerificationReport = {
  verdict: string;
  problems?: string[];
  retries?: number;
  evidence_count?: number;
  parsed?: boolean | null;
  model?: string | null;
  error?: string | null;
};

// Shown in the reasoning trace rather than in a panel of its own. The report is
// worth seeing on every turn, and a dedicated surface for it is a design
// question this change does not need to answer.
const formatVerification = (report: VerificationReport): string => {
  const lines = [`verdict: ${report.verdict}`];
  lines.push(`evidence items: ${report.evidence_count ?? 0}`);
  lines.push(`rewrites: ${report.retries ?? 0}`);
  if (report.parsed === false) {
    lines.push(
      "the reviewer's reply could not be read, so this answer is unverified"
    );
  }
  if (report.error) {
    lines.push(`reviewer unavailable: ${report.error}`);
  }
  for (const problem of report.problems ?? []) {
    lines.push(`- ${problem}`);
  }
  return `\n\n\`\`\`\nVerification\n${lines.join("\n")}\n\`\`\`\n\n`;
};

type ChatStreamEvent =
  | {
      type: "text" | "reasoning" | "replace";
      content: string;
    }
  | {
      type: "usage";
      usage: TokenUsage;
      model_usage: ModelUsage;
    }
  | {
      type: "verification";
      verification: VerificationReport;
    }
  | {
      type: "done";
      interrupt?: PendingInterrupt | null;
      usage?: TokenUsage | null;
      model_usage?: ModelUsage | null;
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
    let usage: TokenUsage | null = null;
    const modelUsage: ModelUsage[] = [];

    const parseEvent = (line: string): ChatStreamEvent => {
      try {
        const event = JSON.parse(line) as Partial<ChatStreamEvent>;

        if (
          event.type !== "text" &&
          event.type !== "reasoning" &&
          event.type !== "replace" &&
          event.type !== "usage" &&
          event.type !== "verification" &&
          event.type !== "done"
        ) {
          throw new Error("missing stream fields");
        }

        if (
          (event.type === "text" ||
            event.type === "reasoning" ||
            event.type === "replace") &&
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
        case "usage":
          usage = event.usage;
          modelUsage.push(event.model_usage);
          break;
        case "verification":
          reasoning += formatVerification(event.verification);
          break;
        case "done":
          text = text.trim();
          reasoning = reasoning.trim();
          completed = true;
          usage = event.usage ?? usage;
          if (modelUsage.length === 0 && event.model_usage) {
            modelUsage.push(event.model_usage);
          }
          if (event.interrupt?.actions.length) {
            requestDecision(event.interrupt);
          }
      }

      return {
        content: asContent(),
        ...(usage
          ? {
              metadata: {
                steps:
                  modelUsage.length > 0
                    ? modelUsage.map((snapshot) => ({
                        usage: {
                          inputTokens: snapshot.input_tokens,
                          outputTokens: snapshot.output_tokens
                        }
                      }))
                    : [
                        {
                          usage: {
                            inputTokens: usage.input_tokens,
                            outputTokens: usage.output_tokens
                          }
                        }
                      ],
                custom: { modelUsage, tokenUsage: usage }
              }
            }
          : {})
      };
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
