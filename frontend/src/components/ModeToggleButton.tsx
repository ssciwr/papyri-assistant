import { useState } from "react";
import { useAui } from "@assistant-ui/react";

import { apiUrl } from "../assistantRuntime";

type Mode = "agentic" | "retrieval";

const modeLabels: Record<Mode, string> = {
  agentic: "Agent",
  retrieval: "Similarity"
};

const modeTitles: Record<Mode, string> = {
  agentic: "Agent mode: switch to plain similarity search",
  retrieval: "Similarity search: switch back to agent mode"
};

export function ModeToggleButton() {
  const aui = useAui();
  const [mode, setMode] = useState<Mode>("agentic");
  const [isSwitching, setIsSwitching] = useState(false);

  const handleToggle = async () => {
    const nextMode: Mode = mode === "agentic" ? "retrieval" : "agentic";
    setIsSwitching(true);

    try {
      const response = await fetch(
        `${apiUrl}/changemode?mode=${encodeURIComponent(nextMode)}`,
        { method: "POST" }
      );

      if (!response.ok) {
        const errorText = await response.text();

        throw new Error(errorText || `Request failed with ${response.status}`);
      }

      // The agent is built for the mode it was created in, so the new mode only
      // takes effect once the backend has replaced it.
      const newAgent = await fetch(`${apiUrl}/new`, { method: "POST" });

      if (!newAgent.ok) {
        const errorText = await newAgent.text();

        throw new Error(errorText || `Request failed with ${newAgent.status}`);
      }

      // The two modes answer very differently, so the comparison is easier to
      // read when each one starts on its own transcript.
      setMode(nextMode);
      aui.threads().switchToNewThread();
    } catch (error) {
      window.alert(
        `Could not switch mode: ${
          error instanceof Error ? error.message : String(error)
        }`
      );
    } finally {
      setIsSwitching(false);
    }
  };

  return (
    <button
      aria-label={modeTitles[mode]}
      className="mode-toggle-button"
      disabled={isSwitching}
      onClick={handleToggle}
      title={modeTitles[mode]}
      type="button"
    >
      {modeLabels[mode]}
    </button>
  );
}
