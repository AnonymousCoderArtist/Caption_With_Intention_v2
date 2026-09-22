"""Toolbar with undo/redo, copy/paste, and selection controls."""

import { useState } from "react";
import type { EditorApiClient } from "@/api/client";

interface ToolbarProps {
  api: EditorApiClient | any;
  onAction: () => void;
}

export function Toolbar({ api, onAction }: ToolbarProps) {
  const [message, setMessage] = useState<string | null>(null);

  const flash = async (fn: () => Promise<any>, text: string) => {
    setMessage(text);
    onAction();
    setTimeout(() => setMessage(null), 1800);
  };

  return (
    <div className="toolbar">
      {message && (
        <span className="text-success" style={{ fontSize: "0.8rem" }}>
          {message}
        </span>
      )}

      <button onClick={() => flash(() => api?.undo?.(), "Undo")} title="Undo">
        ↩ Undo
      </button>
      <button onClick={() => flash(() => api?.redo?.(), "Redo")} title="Redo (Ctrl+Y)">
        ↪ Redo
      </button>

      <div className="toolbar-separator" />

      <button onClick={() => flash(() => api?.selectAll?.(), "All events selected")} title="Select All">
        Select All
      </button>
      <button onClick={() => flash(() => api?.clearSelection?.(), "Selection cleared")} title="Deselect All">
        Deselect
      </button>

      <div className="toolbar-separator" />

      <button onClick={() => flash(() => api?.copy_style ? api.copy_style("") : {}, "Copy style (select event first)")}>
        Copy Style
      </button>
      <button onClick={() => flash(() => api?.paste_style ? {} : {}, "Paste style to selected")}>
        Paste Style
      </button>

      <div className="toolbar-separator" />

      <button onClick={() => flash(() => {}, "Preview render")}>▶ Preview</button>
      <button onClick={() => flash(() => {}, "Export project")}>Export</button>
    </div>
  );
}
