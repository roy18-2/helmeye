import { useEffect, useState } from "react";
import api, { errorMessage } from "../api.js";
import { PageHeader, StatCard } from "../components/ui.jsx";

const pct = (v) => (v == null ? "n/a" : `${Math.round(v * 100)}%`);

export default function Overview() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    api
      .get("/incidents/summary")
      .then((res) => {
        if (!cancelled) setData(res.data);
      })
      .catch((err) => {
        if (!cancelled) setError(errorMessage(err, "Could not load the summary"));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div>
      <PageHeader title="Overview" subtitle="Incident counts and review progress" />

      {error && (
        <p className="mb-4 rounded-lg border border-danger/40 bg-danger/10 p-3 text-sm text-danger">{error}</p>
      )}
      {!data && !error && <p className="text-muted">Loading...</p>}

      {data && (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard label="Total incidents" value={data.total} tone="accent" />
            <StatCard label="Pending review" value={data.by_review_status.pending} tone="warn" />
            <StatCard label="Confirmed" value={data.by_review_status.confirmed} tone="danger" />
            <StatCard
              label="Reviewed precision"
              value={pct(data.reviewed_precision)}
              hint="Confirmed / (confirmed + false positives)"
              tone="success"
            />
          </div>
          <p className="mt-6 text-xs text-muted">
            Counts include synthetic demo incidents and mock-detector incidents.
          </p>
        </>
      )}
    </div>
  );
}
