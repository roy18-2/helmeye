import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { FileVideo, Upload as UploadIcon } from "lucide-react";
import api, { errorMessage } from "../api.js";
import { PageHeader } from "../components/ui.jsx";
import { formatTime } from "../lib/format.js";

const ALLOWED = [".mp4", ".mov", ".avi", ".mkv", ".webm"];
const MAX_BYTES = 500 * 1024 * 1024;

const FIELD =
  "w-full rounded-lg border border-line bg-bg px-3 py-2 text-sm text-fg outline-none focus:border-accent";

const STATUS_STYLES = {
  queued: "border-warn/50 bg-warn/10 text-warn",
  processing: "border-accent/50 bg-accent/10 text-accent",
  completed: "border-success/50 bg-success/10 text-success",
  failed: "border-danger/50 bg-danger/10 text-danger",
};

function validate(file) {
  const dot = file.name.lastIndexOf(".");
  const ext = dot >= 0 ? file.name.slice(dot).toLowerCase() : "";
  if (!ALLOWED.includes(ext)) return `Allowed types: ${ALLOWED.join(", ")}`;
  if (file.size > MAX_BYTES) return "File is larger than 500 MB";
  if (file.size === 0) return "This file is empty";
  return "";
}

function fmtSize(bytes) {
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function fmtDuration(seconds) {
  if (!seconds) return "-";
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return `${m}:${String(s).padStart(2, "0")}`;
}

function ProgressBar({ value }) {
  return (
    <div
      className="h-2 w-full overflow-hidden rounded-full bg-surface2"
      role="progressbar"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={value}
    >
      <div className="h-full bg-accent transition-all" style={{ width: `${value}%` }} />
    </div>
  );
}

function JobCard({ video }) {
  return (
    <li className="rounded-xl border border-line bg-surface p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="min-w-0">
          <div className="truncate font-medium">{video.filename}</div>
          <div className="text-xs text-muted">
            <span className="font-mono">{video.camera_code}</span> - {fmtDuration(video.duration_s)} -{" "}
            {fmtSize(video.size_bytes)}
          </div>
        </div>
        <span
          className={`rounded border px-2 py-0.5 text-xs font-medium uppercase tracking-wider ${
            STATUS_STYLES[video.status] || "border-line text-muted"
          }`}
        >
          {video.status}
        </span>
      </div>

      <div className="mt-3">
        <ProgressBar value={video.progress} />
      </div>

      <div className="mt-2 flex flex-wrap items-center justify-between gap-2 text-xs text-muted">
        <span>
          {video.progress}% - {video.incidents_count} incidents found - {video.sampled_frames} frames sampled
        </span>
        <span>
          {video.uploaded_by_name}, {formatTime(video.created_at)}
        </span>
      </div>

      {video.status === "failed" && video.error && (
        <p role="alert" className="mt-2 text-sm text-danger">
          {video.error}
        </p>
      )}
      {video.status === "completed" && (
        <Link to="/incidents" className="mt-2 inline-block text-sm text-accent hover:underline">
          View incidents
        </Link>
      )}
    </li>
  );
}

export default function UploadPage() {
  const [cameras, setCameras] = useState([]);
  const [camera, setCamera] = useState("");
  const [recordedAt, setRecordedAt] = useState("");
  const [file, setFile] = useState(null);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadPct, setUploadPct] = useState(0);
  const [error, setError] = useState("");
  const [videos, setVideos] = useState([]);
  const [listError, setListError] = useState("");

  useEffect(() => {
    let cancelled = false;
    api
      .get("/cameras")
      .then((res) => {
        if (cancelled) return;
        setCameras(res.data);
        setCamera((c) => c || res.data[0]?.code || "");
      })
      .catch((err) => {
        if (!cancelled) setError(errorMessage(err, "Could not load cameras"));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const hasActive = videos.some((v) => v.status === "queued" || v.status === "processing");

  useEffect(() => {
    let cancelled = false;
    const load = () =>
      api
        .get("/videos")
        .then((res) => {
          if (!cancelled) {
            setVideos(res.data);
            setListError("");
          }
        })
        .catch((err) => {
          if (!cancelled) setListError(errorMessage(err, "Could not load jobs"));
        });
    load();
    if (!hasActive) return () => {
      cancelled = true;
    };
    const id = setInterval(load, 2000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [hasActive]);

  function pick(candidate) {
    if (!candidate) return;
    const problem = validate(candidate);
    if (problem) {
      setFile(null);
      setError(problem);
      return;
    }
    setError("");
    setFile(candidate);
  }

  function onDrop(e) {
    e.preventDefault();
    setDragging(false);
    pick(e.dataTransfer.files?.[0]);
  }

  async function submit(e) {
    e.preventDefault();
    if (!file || !camera) return;
    setError("");
    setUploading(true);
    setUploadPct(0);

    const form = new FormData();
    form.append("file", file);
    form.append("camera_code", camera);
    if (recordedAt) form.append("recorded_at", new Date(recordedAt).toISOString());

    try {
      const res = await api.post("/videos", form, {
        timeout: 0,
        onUploadProgress: (ev) => {
          if (ev.total) setUploadPct(Math.round((ev.loaded / ev.total) * 100));
        },
      });
      setVideos((list) => [res.data, ...list.filter((v) => v.id !== res.data.id)]);
      setFile(null);
      setRecordedAt("");
    } catch (err) {
      setError(errorMessage(err, "Upload failed"));
    } finally {
      setUploading(false);
    }
  }

  return (
    <div>
      <PageHeader title="Video Upload" subtitle="Queue footage for the detection pipeline" />

      <div className="grid gap-6 lg:grid-cols-[minmax(0,420px)_1fr]">
        <form onSubmit={submit} className="space-y-4 rounded-xl border border-line bg-surface p-5">
          <label
            onDragOver={(e) => {
              e.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
            className={[
              "flex cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed p-8 text-center",
              dragging ? "border-accent bg-accent/10" : "border-line hover:border-accent",
            ].join(" ")}
          >
            <input
              type="file"
              accept=".mp4,.mov,.avi,.mkv,.webm,video/*"
              className="sr-only"
              onChange={(e) => {
                pick(e.target.files?.[0]);
                e.target.value = "";
              }}
            />
            {file ? <FileVideo size={32} className="text-accent" /> : <UploadIcon size={32} className="text-muted" />}
            {file ? (
              <>
                <span className="break-all text-sm font-medium">{file.name}</span>
                <span className="text-xs text-muted">{fmtSize(file.size)} - click to choose another</span>
              </>
            ) : (
              <>
                <span className="text-sm font-medium">Drop a video here, or click to browse</span>
                <span className="text-xs text-muted">MP4, MOV, AVI, MKV or WEBM, up to 500 MB</span>
              </>
            )}
          </label>

          <label className="block text-sm">
            <span className="mb-1 block text-xs uppercase tracking-widest text-muted">Camera</span>
            <select value={camera} onChange={(e) => setCamera(e.target.value)} className={FIELD}>
              {cameras.map((c) => (
                <option key={c.code} value={c.code}>
                  {c.code} - {c.name}
                </option>
              ))}
            </select>
          </label>

          <label className="block text-sm">
            <span className="mb-1 block text-xs uppercase tracking-widest text-muted">Recorded at (optional)</span>
            <input
              type="datetime-local"
              value={recordedAt}
              onChange={(e) => setRecordedAt(e.target.value)}
              className={FIELD}
            />
            <span className="mt-1 block text-xs text-muted">
              Incident times count up from this moment. Leave empty to use the upload time.
            </span>
          </label>

          {uploading && (
            <div>
              <ProgressBar value={uploadPct} />
              <p className="mt-1 text-xs text-muted">
                {uploadPct < 100 ? `Uploading ${uploadPct}%` : "Checking the video..."}
              </p>
            </div>
          )}

          {error && (
            <p role="alert" className="text-sm text-danger">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={!file || !camera || uploading}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-accent px-4 py-2 font-semibold text-accent-fg disabled:opacity-50"
          >
            <UploadIcon size={16} />
            {uploading ? "Uploading..." : "Queue for analysis"}
          </button>

          <p className="rounded-lg border border-warn/40 bg-warn/10 p-3 text-xs text-warn">
            Demo pipeline: the mock detector does not look at the footage. It invents violations from the file
            contents, so results are simulated.
          </p>
        </form>

        <section>
          <h2 className="mb-3 font-display text-2xl font-bold uppercase tracking-wide">Processing jobs</h2>
          {listError && (
            <p className="mb-3 rounded-lg border border-danger/40 bg-danger/10 p-3 text-sm text-danger">
              {listError}
            </p>
          )}
          {videos.length === 0 && !listError ? (
            <p className="rounded-xl border border-dashed border-line bg-surface p-8 text-center text-muted">
              No videos yet. Upload one to start.
            </p>
          ) : (
            <ul className="space-y-3">
              {videos.map((v) => (
                <JobCard key={v.id} video={v} />
              ))}
            </ul>
          )}
        </section>
      </div>
    </div>
  );
}