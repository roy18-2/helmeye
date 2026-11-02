import cv2
import numpy as np

from ..config import settings

EVIDENCE_DIR = settings.upload_dir / "evidence"


def save_demo_evidence(filename: str, bbox: list[float], label: str, confidence: float, seed: int) -> str:
    """Draw a synthetic road scene with a detection box. Used only for demo data."""
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    w, h = 640, 360
    rng = np.random.default_rng(seed)

    top = np.array([60, 52, 40], dtype=np.float32)
    bottom = np.array([95, 90, 85], dtype=np.float32)
    gradient = np.linspace(top, bottom, h)[:, None, :]
    frame = np.repeat(gradient, w, axis=1)
    frame = frame + rng.normal(0, 6, frame.shape)
    frame = np.clip(frame, 0, 255).astype(np.uint8)

    cv2.rectangle(frame, (0, int(h * 0.6)), (w, h), (70, 70, 70), -1)
    for x in range(20, w, 90):
        cv2.line(frame, (x, int(h * 0.82)), (x + 40, int(h * 0.82)), (200, 200, 200), 2)

    x1, y1 = int(bbox[0] * w), int(bbox[1] * h)
    x2, y2 = x1 + int(bbox[2] * w), y1 + int(bbox[3] * h)
    color = (60, 60, 230) if label == "no_helmet" else (0, 170, 255)
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

    text = f"{label.replace('_', ' ').upper()} {int(confidence * 100)}%"
    cv2.putText(frame, text, (x1, max(15, y1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)
    cv2.putText(frame, "DEMO FRAME - SYNTHETIC", (10, h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (220, 220, 220), 1, cv2.LINE_AA)

    cv2.imwrite(str(EVIDENCE_DIR / filename), frame)
    return filename


def save_frame_evidence(filename: str, frame, bbox: list[float], label: str, confidence: float) -> str:
    """Save a real video frame with the detection box drawn on it."""
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    h, w = frame.shape[:2]
    scale = min(1.0, 960 / w)
    if scale < 1.0:
        frame = cv2.resize(frame, (int(w * scale), int(h * scale)))
    else:
        frame = frame.copy()
    h, w = frame.shape[:2]

    x1, y1 = int(bbox[0] * w), int(bbox[1] * h)
    x2, y2 = x1 + int(bbox[2] * w), y1 + int(bbox[3] * h)
    color = (60, 60, 230) if label == "no_helmet" else (0, 170, 255)
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
    text = f"{label.replace('_', ' ').upper()} {int(confidence * 100)}%"
    cv2.putText(frame, text, (x1, max(15, y1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 1, cv2.LINE_AA)
    cv2.putText(frame, "MOCK DETECTOR - SIMULATED BOX", (10, h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (230, 230, 230), 1, cv2.LINE_AA)

    cv2.imwrite(str(EVIDENCE_DIR / filename), frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return filename
