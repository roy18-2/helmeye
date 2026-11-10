from app.detectors.mock import MockDetector


def run(seed, frames=600):
    detector = MockDetector(seed=seed)
    found = []
    for i in range(frames):
        for det in detector.detect(None, i, float(i)):
            found.append((i, det))
    return found


def test_mock_finds_something():
    assert len(run("seed-a")) > 0


def test_mock_is_deterministic():
    first = [(i, d.label, d.confidence, d.bbox, d.track_id) for i, d in run("seed-a")]
    second = [(i, d.label, d.confidence, d.bbox, d.track_id) for i, d in run("seed-a")]
    assert first == second


def test_different_files_give_different_results():
    a = [(i, d.bbox) for i, d in run("seed-a")]
    b = [(i, d.bbox) for i, d in run("seed-b")]
    assert a != b


def test_mock_ignores_the_frame():
    detector = MockDetector(seed="seed-a")
    assert detector.detect(None, 0, 0.0) == MockDetector(seed="seed-a").detect("not-an-image", 0, 0.0)


def test_cooldown_spacing():
    times = [float(i) for i, _ in run("seed-a")]
    assert all(later - earlier >= 3.0 for earlier, later in zip(times, times[1:]))


def test_boxes_and_confidence_in_range():
    for _, det in run("seed-a"):
        x, y, w, h = det.bbox
        assert 0 <= x and 0 <= y and w > 0 and h > 0
        assert x + w <= 1 and y + h <= 1
        assert 0.55 <= det.confidence <= 0.97
        assert det.label.value in {"no_helmet", "unclear_headgear"}


def test_track_ids_count_up_from_one():
    ids = [d.track_id for _, d in run("seed-a")]
    assert ids == list(range(1, len(ids) + 1))