import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import api, { errorMessage } from "../api.js";
import { PageHeader, StatCard } from "../components/ui.jsx";
import { CHART_COLORS } from "../lib/chartColors.js";
import { REVIEW_LABELS } from "../lib/format.js";
import { useTheme } from "../theme.jsx";

const TZ = Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";

const FIELD =
  "rounded-lg border border-line bg-bg px-3 py-2 text-sm text-fg outline-none focus:border-accent";

function ChartCard({ title, subtitle, children }) {
  return (
    <section className="rounded-xl border border-line bg-surface p-5">
      <h2 className="font-display text-xl font-bold uppercase tracking-wide">{title}</h2>
      <p className="mb-3 text-xs text-muted">{subtitle}</p>
      <div className="h-64">{children}</div>
    </section>
  );
}

function Empty() {
  return <div className="grid h-full place-items-center text-sm text-muted">No incidents in this period.</div>;
}

export default function Analytics() {
  const { theme } = useTheme();
  const c = CHART_COLORS[theme] || CHART_COLORS.light;
  const [days, setDays] = useState(7);
  const [source, setSource] = useState("");
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError("");
    const params = { days, tz: TZ };
    if (source) params.source = source;
    api
      .get("/analytics", { params })
      .then((res) => {
        if (!cancelled) setData(res.data);
      })
      .catch((err) => {
        if (!cancelled) setError(errorMessage(err, "Could not load analytics"));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [days, source]);

  const axis = { tick: { fill: c.muted, fontSize: 12 }, stroke: c.line };
  const tip = {
    contentStyle: { background: c.surface, border: `1px solid ${c.line}`, borderRadius: 8, color: c.fg },
    labelStyle: { color: c.fg },
    itemStyle: { color: c.fg },
    cursor: { fill: c.surface2, stroke: c.line },
  };

  const statusColors = {
    pending: c.warn,
    confirmed: c.danger,
    false_positive: c.success,
    uncertain: c.accent,
  };
  const outcomes = data
    ? Object.entries(data.by_review_status)
        .map(([key, value]) => ({ key, name: REVIEW_LABELS[key], value }))
        .filter((d) => d.value > 0)
    : [];
  const empty = data && data.total === 0;

  return (
    <div>
      <PageHeader title="Analytics" subtitle={`Incident patterns - times in ${data?.timezone || TZ}`} />

      <div className="mb-6 flex flex-wrap items-end gap-4 rounded-xl border border-line bg-surface p-4">
        <label className="text-xs text-muted">
          <span className="mb-1 block uppercase tracking-widest">Period</span>
          <select value={days} onChange={(e) => setDays(Number(e.target.value))} className={FIELD}>
            <option value={1}>Today</option>
            <option value={7}>Last 7 days</option>
            <option value={14}>Last 14 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
          </select>
        </label>
        <label className="text-xs text-muted">
          <span className="mb-1 block uppercase tracking-widest">Source</span>
          <select value={source} onChange={(e) => setSource(e.target.value)} className={FIELD}>
            <option value="">All sources</option>
            <option value="demo">Demo data</option>
            <option value="mock">Mock detector</option>
          </select>
        </label>
        {loading && <span className="text-xs text-muted">Loading...</span>}
      </div>

      {error && (
        <p className="mb-4 rounded-lg border border-danger/40 bg-danger/10 p-3 text-sm text-danger">{error}</p>
      )}

      {data && (
        <>
          <div className="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard label="Incidents" value={data.total} tone="accent" />
            <StatCard label="Pending" value={data.by_review_status.pending} tone="warn" />
            <StatCard label="Confirmed" value={data.by_review_status.confirmed} tone="danger" />
            <StatCard
              label="Reviewed precision"
              value={data.reviewed_precision == null ? "n/a" : `${Math.round(data.reviewed_precision * 100)}%`}
              hint={`From ${data.reviewed_count} reviewed incidents`}
              tone="success"
            />
          </div>

          <div className="grid gap-6 xl:grid-cols-2">
            <ChartCard title="Violations by hour" subtitle="Hour of day, local time">
              {empty ? (
                <Empty />
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={data.by_hour}>
                    <CartesianGrid stroke={c.line} strokeDasharray="3 3" vertical={false} />
                    <XAxis
                      dataKey="hour"
                      {...axis}
                      minTickGap={8}
                      tickFormatter={(h) => String(h).padStart(2, "0")}
                    />
                    <YAxis allowDecimals={false} {...axis} />
                    <Tooltip {...tip} labelFormatter={(h) => `${String(h).padStart(2, "0")}:00`} />
                    <Bar dataKey="count" name="Incidents" fill={c.accent} radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </ChartCard>

            <ChartCard title="Incidents per day" subtitle="Daily trend for the selected period">
              {empty ? (
                <Empty />
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={data.daily}>
                    <CartesianGrid stroke={c.line} strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="date" {...axis} minTickGap={16} tickFormatter={(d) => d.slice(5)} />
                    <YAxis allowDecimals={false} {...axis} />
                    <Tooltip {...tip} />
                    <Line
                      type="monotone"
                      dataKey="count"
                      name="Incidents"
                      stroke={c.accent}
                      strokeWidth={2}
                      dot={{ r: 3, fill: c.accent }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              )}
            </ChartCard>

            <ChartCard title="Incidents by camera" subtitle="Fleet distribution">
              {empty ? (
                <Empty />
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={data.by_camera} layout="vertical">
                    <CartesianGrid stroke={c.line} strokeDasharray="3 3" horizontal={false} />
                    <XAxis type="number" allowDecimals={false} {...axis} />
                    <YAxis type="category" dataKey="camera_code" width={70} {...axis} />
                    <Tooltip {...tip} />
                    <Bar dataKey="count" name="Incidents" fill={c.danger} radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </ChartCard>

            <ChartCard title="Review outcomes" subtitle="What reviewers decided">
              {outcomes.length === 0 ? (
                <Empty />
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={outcomes}
                      dataKey="value"
                      nameKey="name"
                      innerRadius={55}
                      outerRadius={85}
                      paddingAngle={2}
                      stroke={c.surface}
                    >
                      {outcomes.map((o) => (
                        <Cell key={o.key} fill={statusColors[o.key]} />
                      ))}
                    </Pie>
                    <Tooltip {...tip} />
                    <Legend formatter={(v) => <span style={{ color: c.fg }}>{v}</span>} />
                  </PieChart>
                </ResponsiveContainer>
              )}
            </ChartCard>
          </div>

          <p className="mt-6 text-xs text-muted">
            Demo data and mock-detector incidents are simulated. Use the source filter to separate them.
          </p>
        </>
      )}
    </div>
  );
}