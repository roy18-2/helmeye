from abc import ABC, abstractmethod
from dataclasses import dataclass

from ..models import DetectionLabel


@dataclass
class Detection:
    label: DetectionLabel
    confidence: float
    bbox: list[float]  # normalized [x, y, w, h]
    track_id: int | None = None


class Detector(ABC):
    name: str = "base"

    @abstractmethod
    def detect(self, frame, frame_index: int, timestamp_s: float) -> list[Detection]:
        """Return the violations found in one video frame (a NumPy BGR image)."""
