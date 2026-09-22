"""Project summary widget for the header."""

import type { CaptionEvent, Speaker } from "@/types/project";

interface ProjectSummaryProps {
  summary?: Record<string, any>;
}

export function ProjectSummary({ summary }: ProjectSummaryProps) {
  if (!summary) return null;

  return (
    <div
      style={{
        display: "flex",
        gap: "var(--spacing-lg)",
        fontSize: "0.85rem",
        color: "var(--color-text-secondary)",
      }}
    >
      <span>
        <strong>{summary.project_name ?? "Untitled"}</strong>
      </span>
      <span>
        {summary.speaker_count ?? 0} speakers
      </span>
      <span>
        {summary.event_count ?? 0} events
      </span>
      <span>
        {summary.scene_count ?? 0} scenes
      </span>
      {summary.modified_at && (
        <span style={{ color: "var(--color-text-muted)", fontSize: "0.75rem" }}>
          {new Date(summary.modified_at).toLocaleString()}
        </span>
      )}
    </div>
  );
}
