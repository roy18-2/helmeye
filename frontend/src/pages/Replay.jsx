import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { SkipForward } from "lucide-react";
import api, { errorMessage } from "../api.js";
import { PageHeader } from "../components/ui.jsx";
import AuthImage from "../components/AuthImage.jsx";
import { LabelBadge } from "../components/StatusBadge.jsx";
import { LABELS, percent } from "../lib/format.js";

function clock(seconds) {
  const s = Math.max(0, Math.round(seconds));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

const FIELD =
  "rounded-lg border border-line bg-bg px-3 py-2 text-sm text-fg outline-none focus:border-accent";

export default function Replay() {
  const [videos, setVideos] = useState([]);
  const [videoId, setVideoId] = useState("");
  const [incidents, setIncidents] = useState([]);
  const [src, setSrc] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [playError, setPlayError] = useState(false);
  const [time, setTime] = useState(0);
  const [listLoaded, setListLoaded] = useState(false);
  const videoRef = useRef(null);

  useEffect(() => {
    let cancelled = false;
    api
      .get("/videos")
      .then((res) => {
        if (cancelled) return;
        const done = res.data.filter((v) => v.status === "completed");
        setVideos(done);
        setVideoId((id) => id || done[0]?.id || "");
      })
      .catch((err) => {
        if (!cancelled) setError(errorMessage(err, "Could not load videos"));
      })
      .finally(() => {
        if (!cancelled) setListLoaded(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!videoId) return;
    let cancelled = false;
    setLoading(true);
    setError("");
    setPlayError(false);
    setTime(0);
    setSrc("");
    setIncidents([]);
    Promise.all([
      api.get("/incidents", { params: { video_id: videoId, page_size: 100 } }),
      api.post(`/videos/${videoId}/stream-token`),
    ])
      .then(([inc, tok]) => {
        if (cancelled) return;
        setIncidents(inc.data.items);
        setSrc(`/api/videos/${videoId}/stream?token=${encodeURIComponent(tok.data.token)}`);
      })
      .catch((err) => {
        if (!cancelled) setError(errorMessage(err, "Could not load this video"));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [videoId]);

  const video = videos.find((v) => v.id === videoId) || null;

  const events = useMemo(() => {
    if (!video) return [];
    const start = new Date(video.recorded_at).getTime();
    return incidents
      .map((i) => ({ ...i, offset: (new Date(i.detected_at).getTime() - start) / 1000 }))
      .sort((a, b) => a.offset - b.offset);
  }, [incidents, video]);

  const active = events.filter((e) => time >= e.offset - 0.25 && time <= e.offset + 1.75);
  const activeIds = new Set(active.map((e) => e.id));
  const ratio = video?.width && video?.height ? video.width / video.height : 16 / 9;

  function seek(offset) {
    const el = videoRef.current;
    if (!el) return;
    el.currentTime = Math.max(0, offset);
    setTime(Math.max(0, offset));
  }

  function nextEvent() {
    const next = events.find((e) => e.offset > time + 0.5) || events[0];
    if (next) seek(next.offset);
  }

  if (listLoaded && videos.length === 0 && !error) {
    return (
      <div>
        <PageHeader title="Replay" subtitle="Processed video with detection overlays" />
        <div className="rounded-xl border border-dashed border-line bg-surface p-8 text-center text-muted">
          No processed videos yet.{" "}
          <Link to="/upload" className="text-accent hover:underline">
            Upload one
          </Link>{" "}
          and wait for it to finish.
        </div>
      </div>
    );
  }

  return (
    <div>
      <PageHeader title="Replay" subtitle="Processed video with detection overlays" />

      <div className="mb-4 flex flex-wrap items-end gap-4">
        <label className="text-xs text-muted">
          <span className="mb-1 block uppercase tracking-widest">Video</span>
          <select value={videoId} onChange={(e) => setVideoId(e.target.value)} className={`${FIELD} max-w-xs`}>
            {videos.map((v) => (
              <option key={v.id} value={v.id}>
                {v.filename} - {v.camera_code}
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          onClick={nextEvent}
          disabled={events.length === 0 || !src}
          className="flex items-center gap-2 rounded-lg border border-line px-3 py-2 text-sm text-muted hover:text-fg disabled:opacity-40"
        >
          <SkipForward size={16} /> Next event
        </button>
      </div>

      {error && (
        <p className="mb-4 rounded-lg border border-danger/40 bg-danger/10 p-3 text-sm text-danger">{error}</p>
      )}

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_340px]">
        <div>
          <div
            className="relative w-full overflow-hidden rounded-xl border border-line bg-black"
            style={{ aspectRatio: ratio }}
          >
            {src && (
              <video
                key={src}
                ref={videoRef}
                src={src}
                controls
                playsInline
                preload="metadata"
                className="absolute inset-0 h-full w-full"
                onTimeUpdate={(e) => setTime(e.currentTarget.currentTime)}
                onSeeked={(e) => setTime(e.currentTarget.currentTime)}
                onError={() => setPlayError(true)}
              />
            )}
            {loading && <div className="absolute inset-0 grid place-items-center text-sm text-white/70">Loading...</div>}
            {active.map((e) => (
              <div
                key={e.id}
                className="pointer-events-none absolute border-2 border-danger"
                style={{
                  left: `${e.bbox[0] * 100}%`,
                  top: `${e.bbox[1] * 100}%`,
                  width: `${e.bbox[2] * 100}%`,
                  height: `${e.bbox[3] * 100}%`,
                }}
              >
                <span className="absolute -top-6 left-0 whitespace-nowrap bg-danger px-1.5 py-0.5 text-xs font-semibold text-accent-fg">
                  {LABELS[e.label] || e.label} {percent(e.confidence)}
                </span>
              </div>
            ))}
          </div>

          <p className="mt-2 text-xs text-warn">
            Mock detector: boxes are simulated and do not follow real riders.
          </p>

          {playError && (
            <div role="alert" className="mt-3 rounded-lg border border-danger/40 bg-danger/10 p-3 text-sm text-danger">
              Your browser cannot play this file, probably because of its video codec. Browsers play H.264 MP4
              files. The event list still shows the frames the detector flagged.
            </div>
          )}
        </div>

        <aside>
          <h2 className="mb-2 font-display text-xl font-bold uppercase tracking-wide">
            Events <span className="font-mono text-base text-muted">{events.length}</span>
          </h2>
          {events.length === 0 && !loading ? (
            <p className="rounded-xl border border-dashed border-line bg-surface p-4 text-sm text-muted">
              The detector flagged nothing in this video.
            </p>
          ) : (
            <ul className="max-h-[32rem] space-y-2 overflow-y-auto pr-1">
              {events.map((e) => (
                <li key={e.id}>
                  <button
                    type="button"
                    onClick={() => seek(e.offset)}
                    className={[
                      "flex w-full items-center gap-3 rounded-lg border p-2 text-left",
                      activeIds.has(e.id) ? "border-accent bg-accent/10" : "border-line hover:bg-surface2",
                    ].join(" ")}
                  >
                    <AuthImage
                      incidentId={e.id}
                      alt=""
                      className="h-12 w-20 shrink-0 rounded border border-line bg-surface2 object-cover"
                    />
                    <div className="min-w-0 space-y-1 text-sm">
                      <div className="font-mono">
                        {clock(e.offset)} <span className="text-muted">- {percent(e.confidence)}</span>
                      </div>
                      <LabelBadge label={e.label} />
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </aside>
      </div>
    </div>
  );
}