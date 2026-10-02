/**
 * Which stages cost the most, across recent turns.
 *
 * Ranked horizontal bars: the comparison is between named things, so the names sit
 * beside the bars and the values are labelled directly — no axis to read across.
 * Whether a node owns the time is written on each row, not left to colour alone.
 */
export function StageBars({
  stages,
}: {
  stages: { label: string; node_id: string | null; median_ms: number }[];
}) {
  if (!stages.length) {
    return (
      <p className="flex h-24 items-center justify-center text-sm text-muted-foreground">
        Nothing measured yet.
      </p>
    );
  }

  const worst = Math.max(...stages.map((stage) => stage.median_ms), 1);

  return (
    <ul className="space-y-2">
      {stages.map((stage) => (
        <li key={`${stage.label}-${stage.node_id}`} className="space-y-1">
          <div className="flex items-baseline justify-between gap-3 text-xs">
            <span className="min-w-0 truncate">
              {stage.label}
              <span className="silkscreen ml-1.5">
                {stage.node_id ? stage.node_id : "setting"}
              </span>
            </span>
            <span className="readout shrink-0 text-muted-foreground">{stage.median_ms} ms</span>
          </div>
          <div className="h-1 w-full overflow-hidden rounded-none bg-muted">
            <div
              className="h-full"
              style={{
                width: `${(stage.median_ms / worst) * 100}%`,
                // A node's time is something you can change by editing a box; a
                // setting's time is not, so they read differently.
                background: stage.node_id ? "var(--primary)" : "var(--muted-foreground)",
              }}
            />
          </div>
        </li>
      ))}
    </ul>
  );
}
