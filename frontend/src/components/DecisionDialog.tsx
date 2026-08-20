import { useEffect, useState } from "react";
import { useAui } from "@assistant-ui/react";
import { onDecision, type DecisionOptions } from "../decisionGate";

const EDIT = "edit";

export function DecisionDialog() {
  const aui = useAui();
  const [options, setOptions] = useState<DecisionOptions | null>(null);
  const [selected, setSelected] = useState<string>("");
  const [args, setArgs] = useState("");

  useEffect(
    () =>
      onDecision((incoming) => {
        setOptions(incoming);
        setSelected(incoming[0] ?? "");
        setArgs("");
      }),
    []
  );

  if (!options) {
    return null;
  }

  const editSelected = selected === EDIT;

  const handleSubmit = () => {
    const payload = editSelected
      ? { option: selected, args }
      : { option: selected };

    setOptions(null);
    aui.thread().append({
      role: "user",
      content: [{ type: "text", text: JSON.stringify(payload) }]
    });
  };

  return (
    <div className="decision-overlay" role="dialog" aria-modal="true">
      <div className="decision-dialog">
        <h2 className="decision-title">How do you want to proceed?</h2>
        <div className="decision-options">
          {options.map((option) => (
            <label className="decision-option" key={option}>
              <input
                checked={selected === option}
                name="decision-option"
                onChange={() => setSelected(option)}
                type="radio"
                value={option}
              />
              <span>{option}</span>
            </label>
          ))}
        </div>
        {options.includes(EDIT) && (
          <textarea
            className="decision-args"
            disabled={!editSelected}
            onChange={(event) => setArgs(event.target.value)}
            placeholder="Your edit..."
            rows={3}
            value={args}
          />
        )}
        <button
          className="decision-submit"
          disabled={!selected}
          onClick={handleSubmit}
          type="button"
        >
          Send
        </button>
      </div>
    </div>
  );
}
