import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from eye_tracker import BlinkDetector


def feed(det, scores, dt=1 / 30):
    return [det.update(s, i * dt) for i, s in enumerate(scores)]


def fired(events):
    return [e for e in events if e]


def test_single_blink_gives_one_event():
    det = BlinkDetector(close_threshold=0.5, open_gap=0.2, cooldown_s=0.25)
    events = feed(det, [0.1, 0.1, 0.7, 0.8, 0.9, 0.6, 0.2, 0.1])
    assert fired(events) == ["blink"]
    assert events[2] == "blink"  # fires the moment the eyes close


def test_noise_around_threshold_does_not_retrigger():
    det = BlinkDetector(close_threshold=0.5, open_gap=0.2, cooldown_s=0.0)
    # hovers between 0.45 and 0.55: never drops below the open threshold (0.3)
    events = feed(det, [0.1, 0.55, 0.45, 0.55, 0.45, 0.55])
    assert fired(events) == ["blink"]


def test_two_separate_blinks():
    det = BlinkDetector(close_threshold=0.5, open_gap=0.2, cooldown_s=0.25)
    scores = [0.1] * 3 + [0.8] * 3 + [0.1] * 20 + [0.8] * 3 + [0.1] * 3  # 0.77 s apart: too slow for a double
    assert fired(feed(det, scores)) == ["blink", "blink"]


def test_cooldown_blocks_double_trigger():
    det = BlinkDetector(close_threshold=0.5, open_gap=0.2, cooldown_s=1.0)
    scores = [0.8, 0.1, 0.8, 0.1]  # two closes within 0.1 s
    assert len(fired(feed(det, scores))) == 1


def test_quick_double_blink():
    det = BlinkDetector(close_threshold=0.5, open_gap=0.2, cooldown_s=0.1, double_window_s=0.5)
    scores = [0.1] + [0.8] * 3 + [0.1] * 5 + [0.8] * 3 + [0.1]  # closes 0.27 s apart
    events = feed(det, scores)
    assert fired(events) == ["blink", "double_blink"]
    assert events[9] == "double_blink"  # fires the moment the eyes close the 2nd time


def test_third_quick_blink_starts_a_new_pair():
    det = BlinkDetector(close_threshold=0.5, open_gap=0.2, cooldown_s=0.1, double_window_s=0.5)
    blink = [0.8] * 3 + [0.1] * 5
    assert fired(feed(det, [0.1] + blink * 3)) == ["blink", "double_blink", "blink"]
