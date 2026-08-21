import { useEffect, useState } from "react";
import { useAui } from "@assistant-ui/react";
import { onDecision, type PendingInterrupt } from "../decisionGate";

type Reply = { type: string; message?: string };

/** Per-action dialog state: the chosen decision and any message going with it. */
type Draft = { decision: string; message: string };

/**
 * Decisions that carry a message back to the model.
 *
 * A rejection's reason arrives as the refused tool call's result, so this is
 * where "do it this way instead" belongs — the model sees which action was
 * refused alongside why, rather than having to tie a later message to it.
 * `respond` answers on the tool's behalf and needs one; `reject` does not.
 */
const MESSAGE_REQUIRED = "respond";
const carriesMessage = (decision: string) =>
  decision === "reject" || decision === MESSAGE_REQUIRED;

const placeholderFor = (decision: string) =>
  decision === MESSAGE_REQUIRED
    ? "Your answer for the agent..."
    : "Optional: what to do instead...";

export function DecisionDialog() {
  const aui = useAui();
  const [interrupt, setInterrupt] = useState<PendingInterrupt | null>(null);
  const [drafts, setDrafts] = useState<Draft[]>([]);

  useEffect(
    () =>
      onDecision((incoming) => {
        setInterrupt(incoming);
        setDrafts(
          incoming.actions.map((action) => ({
            decision: action.allowed_decisions[0] ?? "",
            message: ""
          }))
        );
      }),
    []
  );

  if (!interrupt) {
    return null;
  }

  const update = (index: number, patch: Partial<Draft>) =>
    setDrafts((current) =>
      current.map((draft, i) => (i === index ? { ...draft, ...patch } : draft))
    );

  const incomplete = drafts.some(
    (draft) =>
      !draft.decision ||
      (draft.decision === MESSAGE_REQUIRED && !draft.message.trim())
  );

  const handleSubmit = () => {
    const decisions: Reply[] = drafts.map((draft) => {
      const message = draft.message.trim();
      return carriesMessage(draft.decision) && message
        ? { type: draft.decision, message }
        : { type: draft.decision };
    });

    setInterrupt(null);
    aui.thread().append({
      role: "user",
      content: [
        {
          type: "text",
          text: JSON.stringify({ interrupt_id: interrupt.id, decisions })
        }
      ]
    });
  };

  return (
    <div className="decision-overlay" role="dialog" aria-modal="true">
      <div className="decision-dialog">
        <h2 className="decision-title">How do you want to proceed?</h2>
        {interrupt.actions.map((action, index) => (
          <section className="decision-action" key={`${action.name}-${index}`}>
            <h3 className="decision-action-name">{action.name}</h3>
            <div className="decision-options">
              {action.allowed_decisions.map((option) => (
                <label className="decision-option" key={option}>
                  <input
                    checked={drafts[index]?.decision === option}
                    name={`decision-${index}`}
                    onChange={() => update(index, { decision: option })}
                    type="radio"
                    value={option}
                  />
                  <span>{option}</span>
                </label>
              ))}
            </div>
            {carriesMessage(drafts[index]?.decision ?? "") && (
              <textarea
                className="decision-message"
                onChange={(event) =>
                  update(index, { message: event.target.value })
                }
                placeholder={placeholderFor(drafts[index].decision)}
                rows={3}
                value={drafts[index]?.message ?? ""}
              />
            )}
          </section>
        ))}
        <button
          className="decision-submit"
          disabled={incomplete}
          onClick={handleSubmit}
          type="button"
        >
          Send
        </button>
      </div>
    </div>
  );
}
