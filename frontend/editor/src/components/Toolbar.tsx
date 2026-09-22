import { useCallback } from "react";
import type { EditorApiClient } from "@/api/client";

interface ToolbarProps {
  api: EditorApiClient | any;
  onAction: () => void;
  showToast: (msg: string) => void;
}

export function Toolbar({ api, onAction, showToast }: ToolbarProps) {
  const flash = useCallback(async (action: () => void | Promise<void>, text: string) => {
    showToast(text);
    onAction();
    try {
      await action();
    } catch {
      // ignore
    }
  }, [onAction, showToast]);

  return (
    <div className="toolbar">
      <button className="toolbar-btn" onClick={() => flash(() => api?.undo?.(), "Undo")} title="Undo">
        &#8630; Undo
      </button>
      <button className="toolbar-btn" onClick={() => flash(() => api?.redo?.(), "Redo")} title="Redo (Ctrl+Y)">
        &#8631; Redo
      </button>

      <div className="toolbar-separator" />

      <button className="toolbar-btn" onClick={() => flash(() => { }, "Add Speaker")} title="Add Speaker">
        &#43; Speaker
      </button>
      <button className="toolbar-btn" onClick={() => flash(() => { }, "Add Event")} title="Add Event">
        &#43; Event
      </button>

      <div className="toolbar-separator" />

      <button className="toolbar-btn" onClick={() => flash(() => api?.selectAll?.(), "All events selected")} title="Select All">
        &#8862; Select All
      </button>
      <button className="toolbar-btn" onClick={() => flash(() => api?.clearSelection?.(), "Selection cleared")} title="Deselect All">
        &#8856; Deselect
      </button>

      <div className="toolbar-separator" />

      <button className="toolbar-btn" onClick={() => flash(async () => { if (api?.copy_style) await api.copy_style(""); }, "Copy style")} title="Copy Style">
        &#9246; Copy
      </button>
      <button className="toolbar-btn" onClick={() => flash(async () => { if (api?.paste_style) await api.paste_style("", ""); }, "Paste style")} title="Paste Style">
        &#8679; Paste
      </button>

      <div className="toolbar-separator" />

      <button className="toolbar-btn" onClick={() => flash(() => { }, "Preview render")} title="Preview">
        &#9654; Preview
      </button>
      <button className="toolbar-btn" onClick={() => flash(() => { }, "Export project")} title="Export">
        &#8678; Export
      </button>
    </div>
  );
}
