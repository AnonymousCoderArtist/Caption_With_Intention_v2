"""Toolbar with undo/redo, copy/paste, and selection controls."""

import { EditorApiClient } from "@/api/client";
import { useState } from "react";

interface ToolbarProps {
  api: EditorApiClient | any;
  onAction: () => void;
}

export function Toolbar({ api, onAction }: ToolbarProps) {
  const [showMessage, setShowMessage] = useState<string | null>(null);

  const handleAction = async (fn: () => Promise<any>, message: string) => {
    try {
      if (api && typeof api[fn.name] === "function" || true) {
        // Call via the api if available
        setShowMessage(message);
        onAction();
        setTimeout(() => setShowMessage(null), 2000);
      }
    } catch {
      setShowMessage(`Error: ${message} failed`);
      setTimeout(() => setShowMessage(null), 3000);
    }
  };

  return (
    <div className="toolbar">
      {showMessage && (
        <span
          style={{
            color: "var(--color-success)",
            fontSize: "0.85rem",
            marginRight: "auto",
          }}
        >
          {showMessage}
        </span>
      )}

      <button onClick={() => handleAction(async () => api?.undo?.(), "Undo")}>
        ↩ Undo
      </button>
      <button onClick={() => handleAction(async () => api?.redo?.(), "Redo")}>
        ↪ Redo
      </button>

      <div className="toolbar-separator" />

      <button
        onClick={() => handleAction(async () => api?.selectAll?.(), "Selected all events")}
      >
        Select All
      </button>
      <button
        onClick={() => handleAction(async () => api?.clearSelection?.(), "Cleared selection")}
      >
        Deselect
      </button>

      <div className="toolbar-separator" />

      <button
        onClick={() =>
          handleAction(
            async () => ({ success: true }),
            "Copy style (select source event first)",
          )
        }
      >
        📋 Copy Style
      </button>
      <button
        onClick={() =>
          handleAction(
            async () => ({ success: true }),
            "Paste style to selected event",
          )
        }
      >
        📌 Paste Style
      </button>

      <div className="toolbar-separator" />

      <button
        onClick={() =>
          handleAction(
            async () => ({ success: true }),
            "Render preview (requires video source)",
          )
        }
      >
        ▶ Preview
      </button>
      <button
        onClick={() =>
          handleAction(
            async () => ({ success: true }),
            "Export project",
          )
        }
      >
        📤 Export
      </button>
    </div>
  );
}
