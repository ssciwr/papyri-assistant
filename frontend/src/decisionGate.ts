// Verbatim decision tokens from the paused action's `allowed_decisions`,
// e.g. ["approve", "edit", "reject"]. Sent back to the agent as-is.
export type DecisionOptions = string[];

type DecisionListener = (options: DecisionOptions) => void;

let listener: DecisionListener | null = null;

export function onDecision(fn: DecisionListener) {
  listener = fn;

  return () => {
    if (listener === fn) {
      listener = null;
    }
  };
}

export function requestDecision(options: DecisionOptions) {
  listener?.(options);
}
