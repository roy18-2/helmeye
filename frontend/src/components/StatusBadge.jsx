import { LABELS, REVIEW_LABELS } from "../lib/format.js";

const BASE =
  "inline-block whitespace-nowrap rounded border px-2 py-0.5 text-xs font-medium uppercase tracking-wider";

const REVIEW_STYLES = {
  pending: "border-warn/50 bg-warn/10 text-warn",
  confirmed: "border-danger/50 bg-danger/10 text-danger",
  false_positive: "border-success/50 bg-success/10 text-success",
  uncertain: "border-accent/50 bg-accent/10 text-accent",
};

export default function StatusBadge({ status }) {
  const style = REVIEW_STYLES[status] || "border-line text-muted";
  return <span className={`${BASE} ${style}`}>{REVIEW_LABELS[status] || status}</span>;
}

export function LabelBadge({ label }) {
  return <span className={`${BASE} border-line bg-surface2 text-fg`}>{LABELS[label] || label}</span>;
}

export function SourceTag({ source }) {
  const text = source === "demo" ? "Demo data" : source === "mock" ? "Mock detector" : null;
  if (!text) return null;
  return <span className={`${BASE} border-line text-muted`}>{text}</span>;
}
