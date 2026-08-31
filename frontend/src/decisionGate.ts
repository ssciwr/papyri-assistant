/** One tool call the agent is waiting for a decision on. */
export type PausedAction = {
  name: string;
  args: Record<string, unknown>;
  /** Verbatim decision tokens allowed for this action specifically. */
  allowed_decisions: string[];
};

/** The decision a paused run needs before it can continue. */
export type PendingInterrupt = {
  /** Sent back with the reply so the backend can reject a stale decision. */
  id: string;
  actions: PausedAction[];
};

type InterruptListener = (interrupt: PendingInterrupt) => void;

let listener: InterruptListener | null = null;

export function onDecision(fn: InterruptListener) {
  listener = fn;

  return () => {
    if (listener === fn) {
      listener = null;
    }
  };
}

export function requestDecision(interrupt: PendingInterrupt) {
  listener?.(interrupt);
}

/** One decision as it travels back to the agent. */
export type DecisionReply = { type: string; message?: string };

/**
 * Read a message as the decision reply it may be.
 *
 * A decision is carried as the JSON text of an ordinary user message, so the
 * transcript would otherwise show the raw payload. This recognises one for
 * display only — the message itself is unchanged. The `interrupt_id` test
 * mirrors the backend's discriminator in `LangChainAgent._as_decision`.
 */
export function readDecision(text: string): DecisionReply[] | null {
  const trimmed = text.trim();
  if (!trimmed.startsWith("{")) {
    return null;
  }

  try {
    const payload = JSON.parse(trimmed) as {
      interrupt_id?: unknown;
      decisions?: unknown;
    } | null;

    if (
      typeof payload === "object" &&
      payload !== null &&
      typeof payload.interrupt_id === "string" &&
      Array.isArray(payload.decisions)
    ) {
      return payload.decisions as DecisionReply[];
    }
  } catch {
    // Ordinary text that happens to start with a brace.
  }

  return null;
}
