import { useEffect, useState } from "react";
import { X } from "lucide-react";
import api, { errorMessage } from "../api.js";
import AuthImage from "./AuthImage.jsx";
import StatusBadge, { LabelBadge, SourceTag } from "./StatusBadge.jsx";
import { formatTime, percent } from "../lib/format.js";

const ACTIONS = [
  { status: "confirmed", label: "Confirm violation", style: "border-danger text-danger hover:bg-danger/10" },
  { status: "false_positive", label: "False positive", style: "border-success text-success hover:bg-success/10" },
  { status: "uncertain", label: "Uncertain", style: "border-accent text-accent hover:bg-accent/10" },
];

function Field({ label, children }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-widest text-muted">{label}</dt>
      <dd className="mt-0.5 text-sm">{children}</dd>
    </div>
  );
}

export default function IncidentDetail({ incident, onClose, onReviewed }) {
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const onKey = (e) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = previous;
    };
  }, [onClose]);

  async function review(status) {
    setBusy(true);
    setError("");
    try {
      const res = await api.patch(`/incidents/${incident.id}/review`, {
        status,
        note: note.trim() || null,
      });
      onReviewed(res.data);
      setNote("");
    } catch (err) {
      setError(errorMessage(err, "Could not save the review"));
    } finally {
      setBusy(false);
    }
  }

  const history = [...(incident.review_history || [])].reverse();

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/60 p-4"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Incident details"
        className="w-full max-w-4xl rounded-xl border border-line bg-surface"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-line px-5 py-3">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="font-display text-2xl font-bold uppercase tracking-wide">Incident</h2>
            <StatusBadge status={incident.review_status} />
            <SourceTag source={incident.source} />
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="rounded-lg border border-line p-2 text-muted hover:text-fg"
          >
            <X size={18} />
          </button>
        </div>

        <div className="grid gap-6 p-5 lg:grid-cols-2">
          <div>
            {incident.evidence_url ? (
              <AuthImage
                incidentId={incident.id}
                alt={`Evidence for incident ${incident.id}`}
                className="aspect-video w-full rounded-lg border border-line bg-surface2 object-contain"
              />
            ) : (
              <div className="grid aspect-video place-items-center rounded-lg border border-dashed border-line text-sm text-muted">
                No evidence image
              </div>
            )}
          </div>

          <dl className="grid grid-cols-2 gap-4">
            <Field label="Camera">{incident.camera_code}</Field>
            <Field label="Track">{incident.track_id ?? "-"}</Field>
            <Field label="Detected">{formatTime(incident.detected_at)}</Field>
            <Field label="Confidence">{percent(incident.confidence)}</Field>
            <Field label="Detection">
              <LabelBadge label={incident.label} />
            </Field>
            <Field label="Plate">
              <span className="font-mono">{incident.plate_text || "-"}</span>
            </Field>
            <Field label="Reviewed by">{incident.reviewed_by_name || "-"}</Field>
            <Field label="Reviewed at">{formatTime(incident.reviewed_at)}</Field>
            {incident.review_note && (
              <div className="col-span-2">
                <Field label="Latest note">{incident.review_note}</Field>
              </div>
            )}
          </dl>
        </div>

        <div className="border-t border-line p-5">
          <h3 className="mb-2 text-xs font-medium uppercase tracking-widest text-muted">Your decision</h3>
          <textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            maxLength={500}
            rows={2}
            placeholder="Optional note (max 500 characters)"
            className="w-full rounded-lg border border-line bg-bg px-3 py-2 text-sm text-fg outline-none focus:border-accent"
          />
          <div className="mt-3 flex flex-wrap gap-2">
            {ACTIONS.map((a) => (
              <button
                key={a.status}
                type="button"
                disabled={busy}
                onClick={() => review(a.status)}
                className={`rounded-lg border px-4 py-2 text-sm font-semibold disabled:opacity-50 ${a.style}`}
              >
                {a.label}
              </button>
            ))}
          </div>
          {error && (
            <p role="alert" className="mt-2 text-sm text-danger">
              {error}
            </p>
          )}

          <h3 className="mb-2 mt-6 text-xs font-medium uppercase tracking-widest text-muted">Review history</h3>
          {history.length === 0 ? (
            <p className="text-sm text-muted">Not reviewed yet.</p>
          ) : (
            <ul className="space-y-2">
              {history.map((h, i) => (
                <li key={`${h.at}-${i}`} className="rounded-lg border border-line bg-surface2 px-3 py-2 text-sm">
                  <div className="flex flex-wrap items-center gap-2">
                    <StatusBadge status={h.status} />
                    <span>{h.by_name}</span>
                    <span className="text-muted">{formatTime(h.at)}</span>
                  </div>
                  {h.note && <p className="mt-1 text-muted">{h.note}</p>}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
