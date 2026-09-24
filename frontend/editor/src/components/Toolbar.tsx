import { Icon } from "@/lib/icons";

interface ToolbarProps {
  onUndo: () => void;
  onRedo: () => void;
  onAddEvent: () => void;
  onAddSpeaker: () => void;
  onSelectAll: () => void;
  onClearSelection: () => void;
  onCopyStyle: () => void;
  onPasteStyle: () => void;
  onExport: () => void;
  onSettings: () => void;
}

export function Toolbar({
  onUndo,
  onRedo,
  onAddEvent,
  onAddSpeaker,
  onSelectAll,
  onClearSelection,
  onCopyStyle,
  onPasteStyle,
  onExport,
  onSettings,
}: ToolbarProps) {
  const TBtn = ({
    icon,
    label,
    onClick,
    title,
  }: {
    icon: Parameters<typeof Icon>[0]["name"];
    label?: string;
    onClick: () => void;
    title: string;
  }) => (
    <button className="toolbar-btn" onClick={onClick} title={title}>
      <Icon name={icon} size={16} />
      {label}
    </button>
  );

  return (
    <div className="toolbar">
      <TBtn icon="undo" label="Undo" onClick={onUndo} title="Undo (⌘/Ctrl Z)" />
      <TBtn icon="redo" label="Redo" onClick={onRedo} title="Redo (⇧⌘/Ctrl Z)" />

      <div className="toolbar-separator" />

      <TBtn icon="plus" label="Event" onClick={onAddEvent} title="New caption event" />
      <TBtn icon="user" label="Speaker" onClick={onAddSpeaker} title="New speaker" />

      <div className="toolbar-separator" />

      <TBtn icon="cursor" onClick={onSelectAll} title="Select all events" />
      <TBtn icon="deselect" onClick={onClearSelection} title="Clear selection" />

      <div className="toolbar-separator" />

      <TBtn icon="copy" label="Copy style" onClick={onCopyStyle} title="Copy style" />
      <TBtn icon="paste" label="Paste style" onClick={onPasteStyle} title="Paste style" />

      <div className="toolbar-spacer" />

      <span className="toolbar-hint">
        <Icon name="sparkle" size={14} />
        Every property is editable · fully undoable
      </span>

      <div className="toolbar-spacer" />

      <button className="ghost" onClick={onSettings} title="Settings" style={{ padding: "7px 12px" }}>
        <Icon name="settings" size={15} />
      </button>
      <button className="primary" onClick={onExport} title="Export" style={{ padding: "7px 16px", fontSize: 12 }}>
        <Icon name="export" size={15} />
        Export
      </button>
    </div>
  );
}
