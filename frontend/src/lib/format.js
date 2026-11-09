export const LABELS = {
  no_helmet: "No helmet",
  unclear_headgear: "Unclear headgear",
};

export const REVIEW_LABELS = {
  pending: "Pending",
  confirmed: "Confirmed",
  false_positive: "False positive",
  uncertain: "Uncertain",
};

export function formatTime(iso) {
  if (!iso) return "-";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "-";
  return d.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "medium" });
}

export function percent(value) {
  return `${Math.round(value * 100)}%`;
}
