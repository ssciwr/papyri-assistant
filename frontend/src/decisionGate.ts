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
