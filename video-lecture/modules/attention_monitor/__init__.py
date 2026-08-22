"""
Attention & Presence Monitor — pure Computer-Vision module.

This package contains **DB-independent** computer-vision logic for the
SmartStudyInstructor "Attention & Presence Monitor" feature:

    landmarks.py     → MediaPipe Face Mesh wrapper (468 landmarks + iris)
    formulas.py      → EAR + head-pose (solvePnP) + cheap iris-based gaze
    gaze.py          → L2CS-Net precise gaze (throttled; crop-based on CPU)
    recognition.py   → DeepFace (ArcFace) enrolment + cosine matching
    temporal.py      → blink-vs-drowsy, PERCLOS, no-blink liveness, smoothing
    liveness.py      → anti-spoof (MiniFASNet passive + behavioural blink)
    scorer.py        → per-frame state + session aggregation (temporal-aware)
    config.py        → ALL tunable constants (thresholds, sampling, etc.)


Design rules honoured by every file in this package:
  • It NEVER imports the FastAPI app, SQLAlchemy, or any DB code.
  • It NEVER writes a raw webcam frame / image to disk (privacy hard-rule).
  • Every magic number lives in `config.py`, not inline.

The FastAPI routes + Postgres persistence live separately in
`admin_web/backend/app/api/attention.py` and import from this package
lazily (so the lean production backend keeps booting without CV deps).
"""

__version__ = "2.0.0"
__all__ = [
    "config",
    "landmarks",
    "formulas",
    "gaze",
    "recognition",
    "temporal",
    "liveness",
    "scorer",
]


