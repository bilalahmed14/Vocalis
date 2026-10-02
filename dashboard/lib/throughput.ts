/** How a stage's throughput reads in the UI. */
export function throughputLabel(stage: {
  tokens_per_sec?: number;
  chars_per_sec?: number;
  realtime_factor?: number;
}): string | null {
  if (stage.tokens_per_sec) return `${stage.tokens_per_sec} tok/s`;
  if (stage.chars_per_sec) return `${stage.chars_per_sec} chars/s`;
  // Below 1 means the model generates speech slower than it plays, which a live
  // call can never keep up with.
  if (stage.realtime_factor) return `${stage.realtime_factor}x realtime`;
  return null;
}
