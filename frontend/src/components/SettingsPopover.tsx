import { GearIcon } from "@primer/octicons-react";
import { useEffect, useId, useRef, useState } from "react";

type SettingsPopoverProps = {
  streamReasoning: boolean;
  onStreamReasoningChange: (enabled: boolean) => void;
};

export function SettingsPopover({
  streamReasoning,
  onStreamReasoningChange
}: SettingsPopoverProps) {
  const [isOpen, setIsOpen] = useState(false);
  const popoverId = useId();
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    const handlePointerDown = (event: PointerEvent) => {
      if (!containerRef.current?.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setIsOpen(false);
      }
    };

    document.addEventListener("pointerdown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);

    return () => {
      document.removeEventListener("pointerdown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen]);

  return (
    <div className="settings-menu" ref={containerRef}>
      <button
        aria-controls={popoverId}
        aria-expanded={isOpen}
        aria-haspopup="dialog"
        aria-label="Open settings"
        className="settings-button"
        onClick={() => setIsOpen((open) => !open)}
        title="Settings"
        type="button"
      >
        <GearIcon aria-hidden="true" />
      </button>
      {isOpen && (
        <div
          aria-label="Chat settings"
          className="settings-popover"
          id={popoverId}
          role="dialog"
        >
          <p className="settings-title">Settings</p>
          <label className="settings-option">
            <input
              checked={streamReasoning}
              onChange={(event) =>
                onStreamReasoningChange(event.currentTarget.checked)
              }
              type="checkbox"
            />
            <span>Stream reasoning</span>
          </label>
        </div>
      )}
    </div>
  );
}
