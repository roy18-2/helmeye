export function PageHeader({ title, subtitle }) {
  return (
    <div className="mb-6">
      <h1 className="font-display text-4xl font-bold uppercase tracking-wide">{title}</h1>
      {subtitle && <p className="mt-1 text-sm text-muted">{subtitle}</p>}
    </div>
  );
}

const TONES = {
  accent: "text-accent",
  danger: "text-danger",
  success: "text-success",
  warn: "text-warn",
};

export function StatCard({ label, value, hint, tone = "accent" }) {
  return (
    <div className="rounded-xl border border-line bg-surface p-5">
      <div className="text-xs font-medium uppercase tracking-widest text-muted">{label}</div>
      <div className={`mt-2 font-display text-5xl font-bold ${TONES[tone]}`}>{value}</div>
      {hint && <div className="mt-1 text-xs text-muted">{hint}</div>}
    </div>
  );
}
