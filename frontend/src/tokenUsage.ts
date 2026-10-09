export type TokenUsage = {
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  cached_input_tokens?: number;
};

export type ModelUsage = TokenUsage & {
  model_call: number;
  context_window?: number | null;
};

export function formatContextUsage(usage: ModelUsage) {
  const input = usage.input_tokens.toLocaleString();
  if (!usage.context_window) {
    return `${input} context tokens`;
  }

  const percent = (usage.input_tokens / usage.context_window) * 100;
  const formattedPercent =
    percent > 0 && percent < 0.1 ? "<0.1" : percent.toFixed(1);
  return `${input} / ${usage.context_window.toLocaleString()} context tokens (${formattedPercent}%)`;
}

export function formatInputOutputUsage(usage: TokenUsage) {
  if (usage.cached_input_tokens === undefined) {
    return `${usage.input_tokens.toLocaleString()} in (cached included) / ${usage.output_tokens.toLocaleString()} out`;
  }

  const uncached = usage.input_tokens - usage.cached_input_tokens;
  return `${uncached.toLocaleString()} in (+ ${usage.cached_input_tokens.toLocaleString()} cached) / ${usage.output_tokens.toLocaleString()} out`;
}
