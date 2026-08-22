"""
liveness.py — Anti-spoofing / presentation-attack detection.

Goal: stop a student from fooling the recognizer by holding a PHOTO (printed or
on a phone) in front of the webcam. We combine two independent signals so one
weak signal alone can't wave an attack through:

  1. PASSIVE TEXTURE (model)  — DeepFace ships a "silent" face anti-spoofing
     model (MiniFASNet). Given a single frame it returns is_real + a confidence
     score by inspecting micro-texture / moiré / reflection cues that separate a
     live face from a re-photographed one. This is heavy-ish, so the API layer
     runs it THROTTLED (config.LIVENESS_REFRESH_SECONDS), not every frame.

  2. BEHAVIOURAL BLINK (temporal, free) — a real person blinks every few
     seconds; a static photo never does, and its EAR barely changes. The
     `temporal.EyeClosureTracker` already gives us `seconds_since_blink` and
     `ear_variance`; `behavioural_spoof_suspected()` turns those into a verdict.

The passive model is imported LAZILY (like recognition) so importing this file
is cheap and the lean backend never pays for TensorFlow. If the model can't be
loaded, `passive_is_real()` degrades to "unknown" (never fabricates an attack).

Attribution: DeepFace (https://github.com/serengil/deepface) — MIT License.
Anti-spoofing model: MiniFASNet (Silent-Face-Anti-Spoofing).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

from . import config


# ══════════════════════════════════════════════════════════════════════════
#  Result container
# ══════════════════════════════════════════════════════════════════════════

@dataclass
class LivenessResult:
    """Outcome of a liveness check for one frame.

    is_real     : True = live face, False = suspected spoof, None = unknown
                  (model unavailable / not run this frame).
    score       : model confidence for the "real" class (0..1), 0 when unknown.
    checked     : whether the passive model actually ran this frame.
    reason      : short human-readable note (for telemetry / debugging).
    """

    is_real: Optional[bool]
    score: float
    checked: bool
    reason: str = ""

    @classmethod
    def unknown(cls, reason: str = "not checked") -> "LivenessResult":
        return cls(is_real=None, score=0.0, checked=False, reason=reason)


# ══════════════════════════════════════════════════════════════════════════
#  Passive texture check (DeepFace / MiniFASNet) — lazy + throttled by caller
# ══════════════════════════════════════════════════════════════════════════

# Cache of the load attempt so we don't retry a broken import every call.
_passive_load_error: Optional[str] = None
_passive_ready: bool = False


def _ensure_passive_ready() -> bool:
    """Best-effort: confirm DeepFace's anti-spoofing path is importable.

    Returns True if we believe the passive model can run. Records the error in
    `_passive_load_error` otherwise. Safe to call repeatedly (memoised).
    """
    global _passive_ready, _passive_load_error
    if _passive_ready:
        return True
    if _passive_load_error is not None:
        return False
    try:
        # DeepFace exposes anti-spoofing via extract_faces(anti_spoofing=True)
        # (DeepFace >= 0.0.90). Importing here keeps module import cheap.
        from deepface import DeepFace  # noqa: F401
        _passive_ready = True
        return True
    except Exception as exc:  # pragma: no cover
        _passive_load_error = f"DeepFace anti-spoofing unavailable: {exc}"
        return False


def passive_is_real(image_bgr: np.ndarray) -> LivenessResult:
    """Run DeepFace's silent anti-spoofing (MiniFASNet) on one frame.

    Returns a `LivenessResult`. On ANY failure (no model, no face, runtime
    error) it degrades to `LivenessResult.unknown()` so liveness can never
    fabricate a spoof verdict from a purely technical hiccup.
    """
    if not config.ENABLE_ANTISPOOF:
        return LivenessResult.unknown("anti-spoof disabled")
    if not _ensure_passive_ready():
        return LivenessResult.unknown(_passive_load_error or "model unavailable")

    try:
        from deepface import DeepFace

        # extract_faces with anti_spoofing=True annotates each face with
        # `is_real` (bool) and `antispoof_score` (float). We use the primary.
        faces = DeepFace.extract_faces(
            img_path=image_bgr,
            detector_backend=config.RECOGNITION_DETECTOR_BACKEND,
            enforce_detection=False,
            anti_spoofing=True,
            align=False,
        )
    except Exception as exc:  # runtime / version differences → unknown
        return LivenessResult.unknown(f"antispoof error: {exc}")

    if not faces:
        return LivenessResult.unknown("no face for antispoof")

    primary = faces[0]
    is_real = bool(primary.get("is_real", True))
    score = float(primary.get("antispoof_score", 0.0) or 0.0)

    # Accept "real" only if the model is confident enough.
    confident_real = is_real and score >= config.ANTISPOOF_REAL_THRESHOLD
    return LivenessResult(
        is_real=confident_real,
        score=score,
        checked=True,
        reason="real" if confident_real else "spoof/low-confidence",
    )


# ══════════════════════════════════════════════════════════════════════════
#  Behavioural blink check (free, temporal) — always available
# ══════════════════════════════════════════════════════════════════════════

def behavioural_spoof_suspected(
    seconds_since_blink: float,
    ear_variance: float,
    *,
    face_present: bool,
) -> bool:
    """Heuristic: a live viewer blinks and their EAR varies over time.

    We suspect a static photo when a face IS present but:
       • no blink has been observed for NO_BLINK_SUSPECT_SECONDS, AND
       • the EAR has been almost perfectly constant (variance below
         EAR_STATIC_VARIANCE_MAX) over the window.
    Both conditions together make a false positive from a very still — but
    real — viewer unlikely, while still catching a printed/phone photo.
    """
    if not face_present:
        return False
    no_blink = seconds_since_blink >= config.NO_BLINK_SUSPECT_SECONDS
    too_static = ear_variance <= config.EAR_STATIC_VARIANCE_MAX
    return no_blink and too_static
