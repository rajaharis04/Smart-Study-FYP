"""
Attention & Presence Monitor — pure Computer-Vision module.

This package contains **DB-independent** computer-vision logic for the
SmartStudyInstructor "Attention & Presence Monitor" feature:

    landmarks.py     → MediaPipe Face Mesh wrapper (468 landmarks)
    formulas.py      → Eye-Aspect-Ratio (EAR) + head-pose (solvePnP)
    gaze.py          → L2CS-Net gaze estimation (optional / feature-flagged)
    recognition.py   → DeepFace (ArcFace) enrolment + cosine matching
    scorer.py        → per-frame is_attentive() + session aggregation
    config.py        → ALL tunable constants (thresholds, sampling, etc.)

Design rules honoured by every file in this package:
  • It NEVER imports the FastAPI app, SQLAlchemy, or any DB code.
  • It NEVER writes a raw webcam frame / image to disk (privacy hard-rule).
  • Every magic number lives in `config.py`, not inline.

The FastAPI routes + Postgres persistence live separately in
`admin_web/backend/app/api/attention.py` and import from this package
lazily (so the lean production backend keeps booting without CV deps).
"""

__version__ = "1.0.0"
__all__ = ["config", "landmarks", "formulas", "gaze", "recognition", "scorer"]
