import { useCallback, useEffect, useState } from "react";
import { ChevronLeft, ChevronRight, RefreshCw, RotateCcw } from "lucide-react";
import api, { errorMessage } from "../api.js";
import { PageHeader } from "../components/ui.jsx";
import AuthImage from "../components/AuthImage.jsx";
import IncidentDetail from "../components/IncidentDetail.jsx";
import StatusBadge, { LabelBadge, SourceTag } from "../components/StatusBadge.jsx";
import { LABELS, formatTime, percent } from "../lib/format.js";
import { useDebounce } from "../lib/hooks.js";

const PAGE_SIZE = 20;

const EMPTY = {
  review_status: "",
  camera_code: "",
  label: "",
  min_confidence: 0,
  date_from: "",
  date_to: "",
};

const TABS = [
  ["", "All"],
  ["pending", "Pending"],
  ["confirmed", "Confirmed"],
  ["false_positive", "False positive"],
  ["uncertain", "Uncertain"],
];

const FIELD =
  "rounded-lg border border-line bg-bg px-3 py-2 text-sm text-fg outline-none focus:border-accent";

export default function Incidents() {
  const [filters, setFilters] = useState(EMPTY);
  const [page, setPage] = useState(1);
  const [cameras, setCameras] = useState([]);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedId, setSelectedId] = useState(null);
  const [reloadKey, setReloadKey] = useState(0);

  const debouncedConfidence = useDebounce(filters.min_confidence, 300);
  const { review_status, camera_code, label, date_from, date_to } = filters;

  useEffect(() => {
    let cancelled = false;
    api
      .get("/cameras")
      .then((res) => {
        if (!cancelled) setCameras(res.data);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError("");
    const params = { page, page_size: PAGE_SIZE };
    if (review_status) params.review_status = review_status;
    if (camera_code) params.camera_code = camera_code;
    if (label) params.label = label;
    if (debouncedConfidence > 0) params.min_confidence = debouncedConfidence / 100;
    if (date_from) params.date_from = new Date(`${date_from}T00:00:00`).toISOString();
    if (date_to) params.date_to = new Date(`${date_to}T23:59:59.999`).toISOString();

    api
      .get("/incidents", { params })
      .then((res) => {
        if (!cancelled) setData(res.data);
      })
      .catch((err) => {
        if (!cancelled) setError(errorMessage(err, "Could not load incidents"));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [page, review_status, camera_code, label, date_from, date_to, debouncedConfidence, reloadKey]);

  function setFilter(key, value) {
    setFilters((f) => ({ ...f, [key]: value }));
    setPage(1);
  }

  function resetFilters() {
    setFilters(EMPTY);
    setPage(1);
  }

  const closeDetail = useCallback(() => setSelectedId(null), []);

  function handleReviewed(updated) {
    setData((d) => d && { ...d, items: d.items.map((i) => (i.id === updated.id ? updated : i)) });
  }

  const dirty = Object.keys(EMPTY).some((k) => filters[k] !== EMPTY[k]);
  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const selected = items.find((i) => i.id === selectedId) || null;

  return (
    <div>
      <PageHeader title="Incidents" subtitle={data ? `${total} matching incidents` : "Loading..."} />

      <div className="mb-6 space-y-4 rounded-xl border border-line bg-surface p-4">
        <div className="flex flex-wrap gap-2">
          {TABS.map(([value, text]) => (
            <button
              key={value || "all"}
              type="button"
              onClick={() => setFilter("review_status", value)}
              className={[
                "rounded-lg border px-3 py-1.5 text-xs font-medium uppercase tracking-wider",
                review_status === value
                  ? "border-accent bg-accent/15 text-accent"
                  : "border-line text-muted hover:text-fg",
              ].join(" ")}
            >
              {text}
            </button>
          ))}
        </div>

        <div className="flex flex-wrap items-end gap-4">
          <label className="text-xs text-muted">
            <span className="mb-1 block uppercase tracking-widest">Camera</span>
            <select value={camera_code} onChange={(e) => setFilter("camera_code", e.target.value)} className={FIELD}>
              <option value="">All cameras</option>
              {cameras.map((c) => (
                <option key={c.code} value={c.code}>
                  {c.code} - {c.name}
                </option>
              ))}
            </select>
          </label>

          <label className="text-xs text-muted">
            <span className="mb-1 block uppercase tracking-widest">Detection</span>
            <select value={label} onChange={(e) => setFilter("label", e.target.value)} className={FIELD}>
              <option value="">All types</option>
              {Object.entries(LABELS).map(([value, text]) => (
                <option key={value} value={value}>
                  {text}
                </option>
              ))}
            </select>
          </label>

          <label className="text-xs text-muted">
            <span className="mb-1 block uppercase tracking-widest">From</span>
            <input type="date" value={date_from} onChange={(e) => setFilter("date_from", e.target.value)} className={FIELD} />
          </label>

          <label className="text-xs text-muted">
            <span className="mb-1 block uppercase tracking-widest">To</span>
            <input type="date" value={date_to} onChange={(e) => setFilter("date_to", e.target.value)} className={FIELD} />
          </label>

          <label className="text-xs text-muted">
            <span className="mb-2 block uppercase tracking-widest">
              Min confidence <span className="font-mono text-accent">{filters.min_confidence}%</span>
            </span>
            <input
              type="range"
              min="0"
              max="100"
              step="5"
              value={filters.min_confidence}
              onChange={(e) => setFilter("min_confidence", Number(e.target.value))}
              className="w-44 accent-accent"
            />
          </label>

          <div className="ml-auto flex gap-2">
            <button
              type="button"
              onClick={resetFilters}
              disabled={!dirty}
              className="flex items-center gap-2 rounded-lg border border-line px-3 py-2 text-sm text-muted hover:text-fg disabled:opacity-40"
            >
              <RotateCcw size={14} /> Reset
            </button>
            <button
              type="button"
              onClick={() => setReloadKey((k) => k + 1)}
              className="flex items-center gap-2 rounded-lg border border-line px-3 py-2 text-sm text-muted hover:text-fg"
            >
              <RefreshCw size={14} /> Refresh
            </button>
          </div>
        </div>
      </div>

      {error && (
        <p className="mb-4 rounded-lg border border-danger/40 bg-danger/10 p-3 text-sm text-danger">{error}</p>
      )}

      <div className={`overflow-x-auto rounded-xl border border-line bg-surface ${loading ? "opacity-60" : ""}`}>
        <table className="w-full min-w-[820px] text-left text-sm">
          <thead>
            <tr className="border-b border-line text-xs uppercase tracking-widest text-muted">
              <th className="px-4 py-3 font-medium">Evidence</th>
              <th className="px-4 py-3 font-medium">Time</th>
              <th className="px-4 py-3 font-medium">Camera</th>
              <th className="px-4 py-3 font-medium">Detection</th>
              <th className="px-4 py-3 font-medium">Plate</th>
              <th className="px-4 py-3 font-medium">Conf</th>
              <th className="px-4 py-3 font-medium">Review</th>
              <th className="px-4 py-3 font-medium">Source</th>
            </tr>
          </thead>
          <tbody>
            {items.map((i) => (
              <tr
                key={i.id}
                tabIndex={0}
                onClick={() => setSelectedId(i.id)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") setSelectedId(i.id);
                }}
                className="cursor-pointer border-b border-line last:border-0 hover:bg-surface2 focus:bg-surface2 focus:outline-none"
              >
                <td className="px-4 py-2">
                  {i.evidence_url ? (
                    <AuthImage
                      incidentId={i.id}
                      alt=""
                      className="h-12 w-20 rounded border border-line bg-surface2 object-cover"
                    />
                  ) : (
                    <div className="h-12 w-20 rounded border border-dashed border-line" />
                  )}
                </td>
                <td className="whitespace-nowrap px-4 py-2">{formatTime(i.detected_at)}</td>
                <td className="px-4 py-2 font-mono">{i.camera_code}</td>
                <td className="px-4 py-2">
                  <LabelBadge label={i.label} />
                </td>
                <td className="px-4 py-2 font-mono">{i.plate_text || "-"}</td>
                <td className="px-4 py-2 font-mono">{percent(i.confidence)}</td>
                <td className="px-4 py-2">
                  <StatusBadge status={i.review_status} />
                </td>
                <td className="px-4 py-2">
                  <SourceTag source={i.source} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {!loading && items.length === 0 && !error && (
          <p className="p-8 text-center text-muted">No incidents match these filters.</p>
        )}
      </div>

      <div className="mt-4 flex items-center justify-between text-sm text-muted">
        <span>
          Page {page} of {totalPages}
        </span>
        <div className="flex gap-2">
          <button
            type="button"
            disabled={page <= 1}
            onClick={() => setPage((p) => p - 1)}
            className="flex items-center gap-1 rounded-lg border border-line px-3 py-1.5 hover:text-fg disabled:opacity-40"
          >
            <ChevronLeft size={16} /> Prev
          </button>
          <button
            type="button"
            disabled={page >= totalPages}
            onClick={() => setPage((p) => p + 1)}
            className="flex items-center gap-1 rounded-lg border border-line px-3 py-1.5 hover:text-fg disabled:opacity-40"
          >
            Next <ChevronRight size={16} />
          </button>
        </div>
      </div>

      {selected && <IncidentDetail incident={selected} onClose={closeDetail} onReviewed={handleReviewed} />}
    </div>
  );
}
