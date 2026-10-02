/**
 * A measurement, printed the way gear prints one: a silkscreened label, the figure
 * in tabular mono so digits don't jump as they update, and the unit kept small.
 */
export function Stat({ label, value, hint }: { label: string; value: string; hint?: string }) {
  const [figure, unit] = splitUnit(value);

  return (
    <div className="border-l border-border pl-4">
      <div className="silkscreen">{label}</div>
      <div className="readout mt-1 text-2xl leading-none">
        {figure}
        {unit ? <span className="ml-1 text-sm text-muted-foreground">{unit}</span> : null}
      </div>
      {hint ? <div className="mt-1 text-[11px] text-muted-foreground">{hint}</div> : null}
    </div>
  );
}

function splitUnit(value: string): [string, string | null] {
  const match = /^(-?[\d.,]+)\s*(\D.*)$/.exec(value);
  return match ? [match[1], match[2]] : [value, null];
}
