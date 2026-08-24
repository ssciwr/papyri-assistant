import { useState } from "react";
import { useAui } from "@assistant-ui/react";

import { apiUrl } from "../assistantRuntime";

export function NewSessionButton() {
  const aui = useAui();
  const [isStarting, setIsStarting] = useState(false);

  const handleNewSession = async () => {
    setIsStarting(true);

    try {
      const response = await fetch(`${apiUrl}/new`, { method: "POST" });

      if (!response.ok) {
        const errorText = await response.text();

        throw new Error(errorText || `Request failed with ${response.status}`);
      }

      // Only clear the transcript once the backend agent has been replaced,
      // so a failed reset leaves the existing conversation intact.
      aui.threads().switchToNewThread();
    } catch (error) {
      window.alert(
        `Could not start a new session: ${
          error instanceof Error ? error.message : String(error)
        }`
      );
    } finally {
      setIsStarting(false);
    }
  };

  return (
    <button
      aria-label="Start new session"
      className="new-session-button"
      disabled={isStarting}
      onClick={handleNewSession}
      title="Start new session"
      type="button"
    >
      <svg
        aria-hidden="true"
        fill="none"
        height="20"
        viewBox="0 0 24 24"
        width="20"
      >
        <path
          d="M12 5v14M5 12h14"
          stroke="currentColor"
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth="2"
        />
      </svg>
    </button>
  );
}
