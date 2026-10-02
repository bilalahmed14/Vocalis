export function PageHeader({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children?: React.ReactNode;
}) {
  return (
    <header className="flex items-end justify-between gap-4 border-b border-border px-8 pb-4 pt-6">
      <div>
        <h1 className="display text-2xl leading-none">{title}</h1>
        {subtitle ? <p className="mt-2 text-sm text-muted-foreground">{subtitle}</p> : null}
      </div>
      {children}
    </header>
  );
}
