interface ProjectSummaryProps {
  summary?: Record<string, any>;
}

export function ProjectSummary({ summary }: ProjectSummaryProps) {
  if (!summary) return null;

  const parts: React.ReactNode[] = [];

  if (summary.project_name) {
    parts.push(<strong key="name" style={{ color: "var(--text-100)", fontWeight: 600 }}>{summary.project_name}</strong>);
  }
  if (summary.speaker_count !== undefined) {
    parts.push(<span key="speakers">{summary.speaker_count} speakers</span>);
  }
  if (summary.event_count !== undefined) {
    parts.push(<span key="events">{summary.event_count} events</span>);
  }

  if (parts.length === 0) return null;

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: "var(--sp-2)",
        fontSize: "0.76rem",
        color: "var(--text-300)",
      }}
    >
      {parts.map((part, i) => (
        <div key={i} style={{ display: "flex", alignItems: "center", gap: "var(--sp-2)" }}>
          {i > 0 && <span style={{ color: "var(--text-500)", fontSize: "0.6rem" }}>&#183;</span>}
          {part}
        </div>
      ))}
    </div>
  );
}
