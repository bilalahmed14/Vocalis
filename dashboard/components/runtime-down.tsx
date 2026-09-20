export function RuntimeDown() {
  const url = process.env.VOCALIS_API_URL ?? "http://localhost:8000";
  return (
    <main className="mx-auto max-w-xl px-6 py-24">
      <h1 className="text-xl font-semibold">The Vocalis runtime isn&apos;t running</h1>
      <p className="mt-2 text-sm text-muted-foreground">
        The canvas reads providers and saved agents from the runtime API, expected at{" "}
        <code className="rounded bg-muted px-1 py-0.5">{url}</code>. Start it with:
      </p>
      <pre className="mt-4 overflow-x-auto rounded-md border bg-muted/40 p-3 text-xs">
        docker compose -f deploy/docker-compose.yml up -d
      </pre>
      <p className="mt-4 text-sm text-muted-foreground">Then reload this page.</p>
    </main>
  );
}
