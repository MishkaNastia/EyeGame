"""Webcam blink detection for EyeGame.

The game only talks to `EyeTracker`. It never touches OpenCV or MediaPipe directly:

    tracker = EyeTracker(); tracker.start()
    for event in tracker.poll_events():   # each frame
        if event == "blink": ...          # or "double_blink" (2nd blink in quick succession)
    tracker.stop()

Detection uses MediaPipe Face Landmarker *blendshapes* ("eyeBlinkLeft"/"eyeBlinkRight",
0 = open, 1 = closed). `BlinkDetector` turns that score into clean events, using
hysteresis plus a cooldown so one blink gives exactly one jump. Events fire the moment
the eyes close (no lag).
"""

from __future__ import annotations

import os
import queue
import ssl
import threading
import time
import urllib.request

import settings


class BlinkDetector:
    """Turns a stream of blink scores (0..1) into discrete events.

    Pure logic with no camera, so it is easy to unit-test.
    """

    def __init__(
        self,
        close_threshold: float = settings.CLOSE_THRESHOLD,
        open_gap: float = settings.OPEN_GAP,
        cooldown_s: float = settings.BLINK_COOLDOWN_S,
        double_window_s: float = settings.DOUBLE_BLINK_WINDOW_S,
    ) -> None:
        self.close_threshold = close_threshold
        self.open_gap = open_gap
        self.cooldown_s = cooldown_s
        self.double_window_s = double_window_s
        self.closed = False
        self._last_blink_t = -1e9
        self._pair_open = False  # last event was a single "blink" that a 2nd blink could pair with

    @property
    def open_threshold(self) -> float:
        return max(0.0, self.close_threshold - self.open_gap)

    def update(self, score: float, t: float) -> str | None:
        """Feed one measurement. On the frame the eyes close, returns "double_blink" if it
        follows a single blink within `double_window_s`, else "blink"; otherwise None."""
        if not self.closed and score >= self.close_threshold:
            self.closed = True
            gap = t - self._last_blink_t
            if gap >= self.cooldown_s:
                self._last_blink_t = t
                if self._pair_open and gap <= self.double_window_s:
                    self._pair_open = False  # a 3rd quick blink starts a new pair
                    return "double_blink"
                self._pair_open = True
                return "blink"
        elif self.closed and score <= self.open_threshold:
            self.closed = False
        return None


def _download_model(url: str, path: str) -> None:
    """Download the face model once. Uses certifi if present (fixes macOS SSL errors)."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        import certifi

        ctx = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        ctx = ssl.create_default_context()
    tmp = path + ".part"
    with urllib.request.urlopen(url, context=ctx, timeout=60) as r, open(tmp, "wb") as f:
        f.write(r.read())
    os.replace(tmp, path)


class EyeTracker:
    """Reads the webcam in a background thread and reports blinks."""

    def __init__(self, camera_index: int = settings.CAMERA_INDEX) -> None:
        self.camera_index = camera_index
        self.detector = BlinkDetector()
        self.status = "starting"  # starting | downloading | ready | no-face | error: ...
        self.score = 0.0
        self.preview = None  # small RGB numpy frame (mirrored) or None
        self._events: queue.Queue[str] = queue.Queue()
        self._running = False
        self._thread: threading.Thread | None = None
        self._cap = None

    # --- public API -------------------------------------------------------
    @property
    def available(self) -> bool:
        return self.status in ("ready", "no-face")

    @property
    def eyes_closed(self) -> bool:
        return self.detector.closed

    def start(self) -> None:
        try:
            import cv2
        except ImportError:
            self.status = "error: opencv not installed"
            return
        # Open the camera on the main thread: on macOS the camera permission
        # request fails if it is made from a background thread.
        cap = cv2.VideoCapture(self.camera_index)
        if not cap.isOpened():
            self.status = "error: no camera (check camera permission)"
            return
        self._cap = cap
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        if self._cap is not None:
            self._cap.release()

    def poll_events(self) -> list[str]:
        events = []
        while True:
            try:
                events.append(self._events.get_nowait())
            except queue.Empty:
                return events

    def adjust_sensitivity(self, delta: float) -> None:
        """Positive delta = blinks need to be stronger (less sensitive)."""
        t = self.detector.close_threshold + delta
        self.detector.close_threshold = min(0.9, max(0.2, t))

    # --- worker thread ----------------------------------------------------
    def _run(self) -> None:
        try:
            landmarker = self._make_landmarker()
        except Exception as e:  # noqa: BLE001 - show any setup problem in the HUD
            self.status = f"error: {e.__class__.__name__}: {e}"[:90]
            print("[eye_tracker]", self.status)
            return

        import cv2
        import mediapipe as mp

        self.status = "ready"
        t0 = time.monotonic()
        last_ts = -1
        while self._running:
            ok, frame = self._cap.read()
            if not ok:
                time.sleep(0.01)
                continue
            frame = cv2.flip(frame, 1)  # mirror, feels natural
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            self.preview = cv2.resize(rgb, settings.PREVIEW_SIZE)

            ts = int((time.monotonic() - t0) * 1000)
            if ts <= last_ts:  # MediaPipe needs strictly increasing timestamps
                ts = last_ts + 1
            last_ts = ts
            result = landmarker.detect_for_video(
                mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), ts
            )
            if not result.face_blendshapes:
                self.status = "no-face"
                continue
            self.status = "ready"
            shapes = {c.category_name: c.score for c in result.face_blendshapes[0]}
            self.score = (shapes.get("eyeBlinkLeft", 0) + shapes.get("eyeBlinkRight", 0)) / 2
            event = self.detector.update(self.score, time.monotonic())
            if event:
                self._events.put(event)
        landmarker.close()

    def _make_landmarker(self):
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision

        if not os.path.exists(settings.MODEL_PATH):
            self.status = "downloading face model..."
            _download_model(settings.MODEL_URL, settings.MODEL_PATH)
        options = vision.FaceLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=settings.MODEL_PATH),
            running_mode=vision.RunningMode.VIDEO,
            num_faces=1,
            output_face_blendshapes=True,
        )
        return vision.FaceLandmarker.create_from_options(options)
