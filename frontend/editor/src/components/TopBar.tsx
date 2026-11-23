import type {ReactNode} from "react";
import { Icon } from "@/lib/icons";

interface TopBarProps {
  onGuide:()=>void;
  projectName: string;
  onRename: (name: string) => void;
  onRenameCommit: () => void;
  source: "live" | "demo";
  stats: { speakers: number; events: number };
  video?: { width: number; height: number; fps: number };
  onExit: () => void;
  onExport: () => void;
  onImportMedia: () => void;
  onOpenProject: () => void;
  localLabel: string;
  saveIndicator?:ReactNode;
}

export function TopBar({
  onGuide,projectName,
  onRename,
  onRenameCommit,
  source,
  stats,
  video,
  onExit,
  onExport,
  onImportMedia,
  onOpenProject,
  localLabel,saveIndicator,
}: TopBarProps) {
  return (
    <header className="topbar">
      {/* brand */}
      <div className="app-mark">
        <span className="mark-badge">
          CI
        </span>
        <span className="mark-word">
          <b>Automated CWI</b>
        </span>
      </div>

      <div className="sep" />

      {/* project name */}
      <input
        className="project-name"
        value={projectName}
        onChange={(e) => onRename(e.target.value)}
        onBlur={onRenameCommit}
        aria-label="Project name"
        spellCheck={false}
      />

      {source === "demo" && (
        <span className="pill" style={{ color: "var(--accent-text)", borderColor: "var(--accent-soft)", background: "var(--accent-softer)" }}>
          <Icon name="sparkle" size={12} />
          {localLabel}
        </span>
      )}

      {saveIndicator}
      <div style={{ flex: 1 }} />

      {/* stats */}
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <span className="stat-chip">
          <Icon name="users" size={14} />
          <b>{stats.speakers}</b> speakers
        </span>
        <span className="stat-chip">
          <Icon name="list" size={14} />
          <b>{stats.events}</b> events
        </span>
      </div>

      <div className="sep" />

      {/* video info */}
      {video && (
        <span className="mono" style={{ fontSize: 10.5, color: "var(--text-400)" }}>
          {video.width}×{video.height} · {video.fps.toFixed(2).replace(/\.?0+$/, "")} fps
        </span>
      )}

      <div className="sep" />

      {/* actions */}
      <button className="ghost" onClick={onGuide}>Guide</button>
      <button className="icon-btn" title="Back to start" onClick={onExit}>
        <Icon name="monitor" size={17} />
      </button>
      <button className="ghost" title="Open project JSON" onClick={onOpenProject}>Open project</button>
      <button className="ghost" onClick={onImportMedia} title="Import local video">
        <Icon name="film" size={15} /> Import video
      </button>
      <button className="ghost" title="Download project JSON" onClick={onExport}>
        <Icon name="export" size={15} />
        Save project
      </button>
    </header>
  );
}
