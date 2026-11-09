import { useEffect, useState } from "react";
import api from "../api.js";

export default function AuthImage({ incidentId, alt, className = "" }) {
  const [src, setSrc] = useState(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    let objectUrl = null;
    setSrc(null);
    setFailed(false);
    api
      .get(`/incidents/${incidentId}/evidence`, { responseType: "blob" })
      .then((res) => {
        if (cancelled) return;
        objectUrl = URL.createObjectURL(res.data);
        setSrc(objectUrl);
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [incidentId]);

  if (failed) {
    return <div className={`grid place-items-center bg-surface2 text-xs text-muted ${className}`}>No image</div>;
  }
  if (!src) {
    return <div className={`animate-pulse bg-surface2 ${className}`} aria-busy="true" />;
  }
  return <img src={src} alt={alt} className={className} />;
}
