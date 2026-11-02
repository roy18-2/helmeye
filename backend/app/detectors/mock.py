import hashlib
import random

from ..models import DetectionLabel
from .base import Detection, Detector


class MockDetector(Detector):
    """Simulated detector. It never looks at the image: results come from a hash
    of the video content, so the same file always gives the same output."""

    name = "mock-v1"

    def __init__(self, seed: str, probability: float = 0.15, cooldown_s: float = 3.0):
        self.seed = seed
        self.probability = probability
        self.cooldown_s = cooldown_s
        self._next_track = 1
        self._last_ts: float | None = None

    def detect(self, frame, frame_index: int, timestamp_s: float) -> list[Detection]:
        digest = hashlib.sha256(f"{self.seed}:{frame_index}".encode()).hexdigest()
        rng = random.Random(int(digest[:16], 16))
        if rng.random() >= self.probability:
            return []
        if self._last_ts is not None and timestamp_s - self._last_ts < self.cooldown_s:
            return []
        self._last_ts = timestamp_s

        label = DetectionLabel.UNCLEAR_HEADGEAR if rng.random() < 0.25 else DetectionLabel.NO_HELMET
        bbox = [
            round(rng.uniform(0.15, 0.6), 3),
            round(rng.uniform(0.2, 0.5), 3),
            round(rng.uniform(0.1, 0.2), 3),
            round(rng.uniform(0.15, 0.3), 3),
        ]
        track = self._next_track
        self._next_track += 1
        return [
            Detection(
                label=label,
                confidence=round(rng.uniform(0.55, 0.97), 2),
                bbox=bbox,
                track_id=track,
            )
        ]
