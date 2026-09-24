import { Icon } from "@/lib/icons";

interface TopBarProps {
  projectName: string;
  onRename: (name: string) => void;
  source: "live" | "demo";
  stats: { speakers: number; events: number };
  video?: { width: number; height: number; fps: number };
  onExit: () => void;
}

export function TopBar({
  projectName,
  onRename,
  source,
  stats,
  video,
  onExit,
}: TopBarProps) {
  return (
    <header className="topbar">
      {/* brand */}
      <div className="app-mark">
        <span className="mark-badge">
          <Icon name="logo" size={17} />
        </span>
        <span className="mark-word">
          <b>CWI</b>
        </span>
      </div>

      <div className="sep" />

      {/* project name */}
      <input
        className="project-name"
        value={projectName}
        onChange={(e) => onRename(e.target.value)}
        aria-label="Project name"
        spellCheck={false}
      />

      {source === "demo" && (
        <span className="pill" style={{ color: "var(--accent-text)", borderColor: "var(--accent-soft)", background: "var(--accent-softer)" }}>
          <Icon name="sparkle" size={12} />
          Demo scene
        </span>
      )}

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
      <button className="icon-btn" title="Back to start" onClick={onExit}>
        <Icon name="monitor" size={17} />
      </button>
      <button className="ghost" title="Export">
        <Icon name="export" size={15} />
        Export
      </button>
    </header>
  );
}
