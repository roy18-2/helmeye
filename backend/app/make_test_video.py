import cv2
import numpy as np

from .config import settings

W, H, FPS, SECONDS = 640, 360, 25, 40


def main() -> None:
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    path = settings.upload_dir / "test_clip.mp4"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), FPS, (W, H))
    for i in range(FPS * SECONDS):
        frame = np.full((H, W, 3), (70, 65, 60), dtype=np.uint8)
        cv2.rectangle(frame, (0, int(H * 0.62)), (W, H), (85, 85, 85), -1)
        x = int((i * 6) % (W + 120)) - 60
        cv2.rectangle(frame, (x, 210), (x + 90, 260), (40, 90, 200), -1)
        cv2.putText(frame, f"TEST CLIP t={i / FPS:5.1f}s", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (230, 230, 230), 1, cv2.LINE_AA)
        writer.write(frame)
    writer.release()
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
