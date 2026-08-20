"""
landmarks.py — MediaPipe Face Mesh wrapper.

Single responsibility: take a decoded BGR frame (numpy array) and return
the 468 facial landmarks for every face found in it, as pixel coordinates.

Everything downstream (EAR, head-pose, gaze) consumes the output of this
module — none of them talk to MediaPipe directly.

Privacy: this module receives an already-decoded in-memory frame and never
writes it anywhere. It only returns numeric landmark arrays.

Heavy deps (mediapipe, numpy) are imported at module import-time, which is
fine because this file is only ever imported *lazily* from the API layer
inside a request handler (see admin_web/backend/app/api/attention.py).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import numpy as np
import mediapipe as mp

from . import config


# MediaPipe Face Mesh has a fixed 468-point topology (478 with refine_landmarks,
# where 468-477 are the iris points). We expose the base count for validation.
NUM_FACE_MESH_LANDMARKS: int = 468


@dataclass
class FaceLandmarks:
    """Landmarks for a single detected face.

    Attributes
    ----------
    points : np.ndarray
        Shape (N, 2) float32 array of (x, y) pixel coordinates, where N is
        468 (or 478 when refine_landmarks is on). Ordered by MediaPipe index,
        so `points[i]` is landmark `i`.
    image_width, image_height : int
        Dimensions of the source frame the points were computed against —
        needed by solvePnP for the camera matrix.
    """

    points: np.ndarray
    image_width: int
    image_height: int

    def point(self, idx: int) -> np.ndarray:
        """Return the (x, y) pixel coordinate for a given landmark index."""
        return self.points[idx]


class FaceMeshDetector:
    """Thin, reusable wrapper around MediaPipe's Face Mesh solution.

    Create ONE instance and reuse it across frames (MediaPipe graphs are
    expensive to build). It is NOT thread-safe — use one detector per worker,
    or guard with a lock. The API layer keeps a single lazily-created instance.
    """

    def __init__(
        self,
        max_faces: Optional[int] = None,
        refine_landmarks: Optional[bool] = None,
        min_detection_confidence: Optional[float] = None,
        min_tracking_confidence: Optional[float] = None,
    ) -> None:
        self._mp_face_mesh = mp.solutions.face_mesh
        self._mesh = self._mp_face_mesh.FaceMesh(
            static_image_mode=False,  # video stream mode → uses tracking
            max_num_faces=max_faces if max_faces is not None else config.FACE_MESH_MAX_FACES,
            refine_landmarks=(
                refine_landmarks
                if refine_landmarks is not None
                else config.FACE_MESH_REFINE_LANDMARKS
            ),
            min_detection_confidence=(
                min_detection_confidence
                if min_detection_confidence is not None
                else config.FACE_MESH_MIN_DETECTION_CONFIDENCE
            ),
            min_tracking_confidence=(
                min_tracking_confidence
                if min_tracking_confidence is not None
                else config.FACE_MESH_MIN_TRACKING_CONFIDENCE
            ),
        )

    # ──────────────────────────────────────────────────────────────────
    #  Core API
    # ──────────────────────────────────────────────────────────────────
    def detect(self, frame_bgr: np.ndarray) -> List[FaceLandmarks]:
        """Detect all faces in a BGR frame.

        Parameters
        ----------
        frame_bgr : np.ndarray
            Decoded frame in OpenCV's default BGR channel order, shape (H, W, 3).

        Returns
        -------
        list[FaceLandmarks]
            One entry per detected face (possibly empty). The list length is
            what the scorer uses to detect the `multiple_faces_detected` case.
        """
        if frame_bgr is None or frame_bgr.size == 0:
            return []

        height, width = frame_bgr.shape[:2]

        # MediaPipe expects RGB. Convert without importing cv2 here (keeps this
        # module's dependency surface minimal): reverse the channel axis.
        frame_rgb = frame_bgr[:, :, ::-1]

        # MediaPipe reads better from a contiguous, writeable-flag-off array.
        frame_rgb = np.ascontiguousarray(frame_rgb)
        frame_rgb.flags.writeable = False

        results = self._mesh.process(frame_rgb)

        faces: List[FaceLandmarks] = []
        if not results.multi_face_landmarks:
            return faces

        for face_landmarks in results.multi_face_landmarks:
            lm = face_landmarks.landmark
            # Convert normalized [0,1] coords → absolute pixel coords.
            pts = np.empty((len(lm), 2), dtype=np.float32)
            for i, p in enumerate(lm):
                pts[i, 0] = p.x * width
                pts[i, 1] = p.y * height
            faces.append(
                FaceLandmarks(points=pts, image_width=width, image_height=height)
            )

        return faces

    def detect_primary(self, frame_bgr: np.ndarray) -> Optional[FaceLandmarks]:
        """Convenience: return only the first (largest/most-confident) face.

        MediaPipe returns faces roughly in confidence order; the scorer uses
        the full `detect()` list for multi-face logic, but per-frame metric
        calculations operate on the primary face.
        """
        faces = self.detect(frame_bgr)
        return faces[0] if faces else None

    # ──────────────────────────────────────────────────────────────────
    #  Lifecycle
    # ──────────────────────────────────────────────────────────────────
    def close(self) -> None:
        """Release the underlying MediaPipe graph."""
        try:
            self._mesh.close()
        except Exception:
            pass

    def __enter__(self) -> "FaceMeshDetector":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
