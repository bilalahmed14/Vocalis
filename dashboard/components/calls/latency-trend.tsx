/**
 * Median time-to-first-audio per day.
 *
 * Columns rather than a line: each day is a bucket of turns, not a reading taken at
 * an instant. One series, so no legend — the heading names it — and only the worst
 * day carries a number, so the shape stays readable. Columns keep a fixed maximum
 * width, so two days of data look like two days rather than a filled rectangle.
 */
export function LatencyTrend({
  daily,
}: {
  daily: { day: string; calls: number; p50_ms: number | null }[];
}) {
  const points = daily.filter(
    (entry): entry is { day: string; calls: number; p50_ms: number } => entry.p50_ms !== null,
  );

  if (!points.length) {
    return (
      <p className="flex h-24 items-center justify-center text-sm text-muted-foreground">
        No calls in this period.
      </p>
    );
  }

  const worst = Math.max(...points.map((point) => point.p50_ms));

  return (
    <figure className="space-y-1.5">
      <div className="flex h-24 items-end gap-1" role="img" aria-label={ariaLabel(points, worst)}>
        {points.map((point) => (
          <div
            key={point.day}
            title={`${point.day}: ${point.p50_ms} ms across ${point.calls} call${point.calls === 1 ? "" : "s"}`}
            className="max-w-8 flex-1 rounded-none bg-primary transition-opacity hover:opacity-100"
            style={{
              height: `${Math.max(4, (point.p50_ms / worst) * 100)}%`,
              opacity: point.p50_ms === worst ? 1 : 0.55,
            }}
          />
        ))}
      </div>

      <figcaption className="flex justify-between text-[11px] text-muted-foreground">
        <span>{points[0].day}</span>
        <span className="readout">worst {worst} ms</span>
        <span>{points.length > 1 ? points[points.length - 1].day : `${points[0].calls} calls`}</span>
      </figcaption>
    </figure>
  );
}

function ariaLabel(points: { day: string; p50_ms: number }[], worst: number): string {
  return `Median time to first audio per day over ${points.length} day${
    points.length === 1 ? "" : "s"
  }, worst ${worst} milliseconds`;
}
