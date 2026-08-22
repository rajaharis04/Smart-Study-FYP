"""
gaze.py — Gaze estimation via L2CS-Net (OPTIONAL / feature-flagged).

Answers the optional part of the per-frame rule (spec §4): "is the gaze angle
within a 'looking at screen' cone?".

Design (per decision #3 — gaze is optional in v1):
  • Controlled by `config.ENABLE_GAZE` (default False).
  • The heavy L2CS-Net model + PyTorch weights are loaded LAZILY, only on the
    first `estimate_gaze()` call, and only when the feature is enabled.
  • If gaze is disabled OR the model/weights are unavailable, the estimator
    degrades gracefully: `available` is False and callers treat the gaze gate
    as "pass" (i.e. gaze never *blocks* attention when it isn't running).

This lets the core pipeline (MediaPipe + EAR + head-pose + DeepFace) work
immediately without cloning L2CS-Net or downloading weights, and lets gaze be
switched on later purely via env vars.

────────────────────────────────────────────────────────────────────────────
Attribution: L2CS-Net — Ahmed A. Abdelrahman et al.
Source: https://github.com/Ahmednull/L2CS-Net  (MIT License)
Vendored under external/L2CS-Net/ with its original LICENSE retained.
────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import os
import math
from dataclasses import dataclass
from typing import Optional

import numpy as np

from . import config


@dataclass
class GazeResult:
    """Result of a gaze estimation for one face.

    yaw_deg / pitch_deg : gaze angles in degrees (0,0 ≈ looking straight ahead).
    on_screen : whether the gaze falls within the configured screen cone.
    available : whether the estimator actually ran (False → gaze disabled or
                model unavailable; callers should NOT penalize the frame).
    """

    yaw_deg: float
    pitch_deg: float
    on_screen: bool
    available: bool

    @classmethod
    def unavailable(cls) -> "GazeResult":
        """A neutral result used when gaze is off/unusable — never blocks."""
        return cls(yaw_deg=0.0, pitch_deg=0.0, on_screen=True, available=False)


class GazeEstimator:
    """Lazy, feature-flagged wrapper around the L2CS-Net gaze pipeline.

    Usage:
        est = GazeEstimator()          # cheap; loads nothing
        res = est.estimate_gaze(frame) # loads model on first enabled call

    The estimator is a no-op (returns `GazeResult.unavailable()`) when
    `config.ENABLE_GAZE` is False, or when Torch / L2CS-Net / weights are
    missing. It records `self.load_error` for diagnostics in that case.
    """

    def __init__(self, enabled: Optional[bool] = None) -> None:
        self.enabled: bool = config.ENABLE_GAZE if enabled is None else enabled
        self._pipeline = None          # underlying L2CS Pipeline (lazy)
        self._load_attempted: bool = False
        self.load_error: Optional[str] = None

    # ──────────────────────────────────────────────────────────────────
    #  Availability
    # ──────────────────────────────────────────────────────────────────
    @property
    def available(self) -> bool:
        """True only if enabled AND the model has been (or can be) loaded."""
        if not self.enabled:
            return False
        if not self._load_attempted:
            self._try_load()
        return self._pipeline is not None

    def _try_load(self) -> None:
        """Attempt a one-time lazy load of the L2CS-Net pipeline."""
        self._load_attempted = True

        if not self.enabled:
            self.load_error = "Gaze disabled via config.ENABLE_GAZE=False."
            return

        weights_path = config.GAZE_WEIGHTS_PATH
        if not os.path.isabs(weights_path):
            # Resolve relative to current working dir (repo root at runtime).
            weights_path = os.path.abspath(weights_path)

        if not os.path.exists(weights_path):
            self.load_error = (
                f"L2CS-Net weights not found at '{weights_path}'. "
                "Download per external/L2CS-Net/README and set ATTN_GAZE_WEIGHTS_PATH."
            )
            return

        try:
            # Lazy heavy imports — torch + l2cs are only touched here.
            import torch  # noqa: F401
            from l2cs import Pipeline  # provided by `pip install -e external/L2CS-Net`

            device_str = config.GAZE_DEVICE
            # Guard against requesting CUDA when it isn't present.
            try:
                import torch as _torch
                if device_str.startswith("cuda") and not _torch.cuda.is_available():
                    device_str = "cpu"
                device = _torch.device(device_str)
            except Exception:
                device = device_str  # let Pipeline coerce it

            self._pipeline = Pipeline(
                weights=weights_path,
                arch="ResNet50",
                device=device,
            )
        except Exception as exc:  # ImportError, weight mismatch, etc.
            self._pipeline = None
            self.load_error = f"Failed to initialize L2CS-Net pipeline: {exc}"

    # ──────────────────────────────────────────────────────────────────
    #  Estimation
    # ──────────────────────────────────────────────────────────────────
    def estimate_gaze(self, frame_bgr: np.ndarray) -> GazeResult:
        """Estimate gaze for the primary face in a BGR frame.

        Returns `GazeResult.unavailable()` (a non-blocking pass) whenever the
        estimator can't run, so gaze is strictly *additive*: it can only ever
        confirm attention, never fabricate inattention due to a missing model.
        """
        if not self.available:
            return GazeResult.unavailable()

        try:
            results = self._pipeline.step(frame_bgr)
        except Exception:
            # Any runtime failure (e.g. no face) → neutral, non-blocking.
            return GazeResult.unavailable()

        yaw_deg, pitch_deg = self._extract_primary_angles(results)
        if yaw_deg is None or pitch_deg is None:
            return GazeResult.unavailable()

        cone = config.GAZE_SCREEN_CONE_DEG
        on_screen = abs(yaw_deg) <= cone and abs(pitch_deg) <= cone
        return GazeResult(
            yaw_deg=float(yaw_deg),
            pitch_deg=float(pitch_deg),
            on_screen=bool(on_screen),
            available=True,
        )

    def estimate_gaze_from_crop(
        self,
        frame_bgr: np.ndarray,
        bbox: Optional[tuple] = None,
    ) -> GazeResult:
        """CPU-friendly gaze: run L2CS on a pre-cropped face region.

        L2CS-Net's `Pipeline.step()` internally runs a RetinaFace detector on
        the WHOLE frame, which dominates CPU cost. When we already know where
        the face is (from MediaPipe), we crop+pad around it and hand L2CS a
        small image, so its detector has almost no work to do. This is a big
        speed-up on CPU and is why the API layer only calls this (throttled).

        Parameters
        ----------
        frame_bgr : np.ndarray
            Full decoded BGR frame.
        bbox : tuple(x_min, y_min, x_max, y_max) | None
            Face box in pixel coords (e.g. from MediaPipe landmark extents).
            If None or cropping is disabled, falls back to `estimate_gaze()`.
        """
        if not self.available:
            return GazeResult.unavailable()

        if bbox is None or not config.GAZE_USE_FACE_CROP:
            return self.estimate_gaze(frame_bgr)

        try:
            h, w = frame_bgr.shape[:2]
            x0, y0, x1, y1 = bbox
            bw = x1 - x0
            bh = y1 - y0
            pad_x = bw * config.GAZE_CROP_PADDING
            pad_y = bh * config.GAZE_CROP_PADDING
            cx0 = max(0, int(x0 - pad_x))
            cy0 = max(0, int(y0 - pad_y))
            cx1 = min(w, int(x1 + pad_x))
            cy1 = min(h, int(y1 + pad_y))
            if cx1 <= cx0 or cy1 <= cy0:
                return self.estimate_gaze(frame_bgr)
            crop = frame_bgr[cy0:cy1, cx0:cx1]
            results = self._pipeline.step(crop)
        except Exception:
            return GazeResult.unavailable()

        yaw_deg, pitch_deg = self._extract_primary_angles(results)
        if yaw_deg is None or pitch_deg is None:
            return GazeResult.unavailable()

        cone = config.GAZE_SCREEN_CONE_DEG
        on_screen = abs(yaw_deg) <= cone and abs(pitch_deg) <= cone
        return GazeResult(
            yaw_deg=float(yaw_deg),
            pitch_deg=float(pitch_deg),
            on_screen=bool(on_screen),
            available=True,
        )

    @staticmethod
    def _extract_primary_angles(results) -> tuple[Optional[float], Optional[float]]:
        """Pull (yaw_deg, pitch_deg) for the first face from an L2CS result.

        L2CS `GazeResultContainer` exposes `.yaw` / `.pitch` numpy arrays in
        RADIANS (one entry per detected face). We convert the first to degrees.
        Written defensively so minor version differences don't crash us.
        """
        try:
            yaw_arr = getattr(results, "yaw", None)
            pitch_arr = getattr(results, "pitch", None)
            if yaw_arr is None or pitch_arr is None:
                return None, None
            if len(yaw_arr) == 0 or len(pitch_arr) == 0:
                return None, None
            yaw_deg = math.degrees(float(yaw_arr[0]))
            pitch_deg = math.degrees(float(pitch_arr[0]))
            return yaw_deg, pitch_deg
        except Exception:
            return None, None


# Module-level singleton so the (potentially heavy) pipeline loads at most once
# per process. The API layer imports and reuses this.
_default_estimator: Optional[GazeEstimator] = None


def get_default_estimator() -> GazeEstimator:
    """Return a process-wide shared GazeEstimator (created on first use)."""
    global _default_estimator
    if _default_estimator is None:
        _default_estimator = GazeEstimator()
    return _default_estimator
