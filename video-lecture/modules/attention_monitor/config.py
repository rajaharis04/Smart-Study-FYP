"""
config.py — Central configuration for the Attention & Presence Monitor.

EVERY tunable value used anywhere in this module lives here as a named
constant (Non-Functional Requirement §6: "no magic numbers buried in logic").
Values can be overridden at runtime via environment variables so the module
can be tuned without code edits.

Nothing in this file imports OpenCV / MediaPipe / DeepFace / Torch, so it is
safe to import from anywhere (including the lean production backend) with
zero heavy dependencies.
"""
from __future__ import annotations

import os

# ══════════════════════════════════════════════════════════════════════════
#  CRITICAL: DeepFace + TensorFlow 2.16+ compatibility.
#  TF 2.16 switched to Keras 3 by default, which breaks DeepFace's model
#  building ("'KerasHistory' object has no attribute 'layer'"). Forcing the
#  legacy tf-keras (Keras 2) backend fixes it. This MUST be set BEFORE
#  tensorflow is imported anywhere — config.py is imported earliest in the
#  CV chain (recognition/scorer/landmarks all `from . import config`), and TF
#  is only ever imported lazily afterwards, so setting it here is safe/global.
#  Requires the `tf-keras` package (see requirements-attention.txt).
# ══════════════════════════════════════════════════════════════════════════
os.environ.setdefault("TF_USE_LEGACY_KERAS", "1")


# ──────────────────────────────────────────────────────────────────────────
#  Small env helpers (no external deps)
# ──────────────────────────────────────────────────────────────────────────

def _env_float(key: str, default: float) -> float:
    try:
        return float(os.getenv(key, default))
    except (TypeError, ValueError):
        return default


def _env_int(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, default))
    except (TypeError, ValueError):
        return default


def _env_bool(key: str, default: bool) -> bool:
    raw = os.getenv(key)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


# ══════════════════════════════════════════════════════════════════════════
#  SESSION-LEVEL DECISION
# ══════════════════════════════════════════════════════════════════════════

# Fraction of *sampled* frames that must be "attentive" for the session to be
# marked "Present". Spec §2 default = 0.80.
ATTENDANCE_THRESHOLD: float = _env_float("ATTN_ATTENDANCE_THRESHOLD", 0.80)

# Present / Absent string labels persisted to the DB.
STATUS_PRESENT: str = "Present"
STATUS_ABSENT: str = "Absent"


# ══════════════════════════════════════════════════════════════════════════
#  SAMPLING
# ══════════════════════════════════════════════════════════════════════════

# Spec §4: sample 1 frame per second (NOT every frame) to stay lightweight.
SAMPLE_FPS: float = _env_float("ATTN_SAMPLE_FPS", 1.0)
SAMPLE_INTERVAL_SECONDS: float = 1.0 / SAMPLE_FPS if SAMPLE_FPS > 0 else 1.0


# ══════════════════════════════════════════════════════════════════════════
#  EYE ASPECT RATIO (EAR)  — formulas.py
# ══════════════════════════════════════════════════════════════════════════

# Eyes considered "closed / half-closed" when EAR < this value (spec §4).
EAR_THRESHOLD: float = _env_float("ATTN_EAR_THRESHOLD", 0.20)

# MediaPipe Face Mesh landmark indices (468-point topology) for each eye,
# ordered as the 6 EAR points p1..p6:
#   p1 = outer corner, p4 = inner corner (horizontal),
#   p2,p3 = upper lid  ·  p5,p6 = lower lid (vertical pairs).
# These index sets are the community-standard EAR points for MediaPipe.
LEFT_EYE_EAR_IDX: tuple[int, int, int, int, int, int] = (33, 160, 158, 133, 153, 144)
RIGHT_EYE_EAR_IDX: tuple[int, int, int, int, int, int] = (362, 385, 387, 263, 373, 380)


# ══════════════════════════════════════════════════════════════════════════
#  HEAD POSE  (solvePnP)  — formulas.py
# ══════════════════════════════════════════════════════════════════════════

# Face considered "frontal" (looking at screen) when within these bounds (§4).
HEAD_YAW_MAX_DEG: float = _env_float("ATTN_HEAD_YAW_MAX_DEG", 25.0)
HEAD_PITCH_MAX_DEG: float = _env_float("ATTN_HEAD_PITCH_MAX_DEG", 20.0)
# Roll is not part of the frontal gate by default but exposed for tuning/telemetry.
HEAD_ROLL_MAX_DEG: float = _env_float("ATTN_HEAD_ROLL_MAX_DEG", 45.0)

# The 6 MediaPipe landmark indices used for solvePnP, in the SAME order as the
# 3D model reference points below:
#   nose tip, chin, left-eye outer corner, right-eye outer corner,
#   left mouth corner, right mouth corner.
HEAD_POSE_LANDMARK_IDX: tuple[int, int, int, int, int, int] = (1, 152, 33, 263, 61, 291)

# Generic 3D face reference model (millimetres, arbitrary reference frame).
# Classic Mallick/OpenCV solvePnP head-pose reference points, matched 1:1 with
# HEAD_POSE_LANDMARK_IDX above. Kept here (not in code) so it is tunable.
FACE_MODEL_3D_POINTS: tuple[tuple[float, float, float], ...] = (
    (0.0, 0.0, 0.0),          # Nose tip
    (0.0, -63.6, -12.5),      # Chin
    (-43.3, 32.7, -26.0),     # Left eye outer corner
    (43.3, 32.7, -26.0),      # Right eye outer corner
    (-28.9, -28.9, -24.1),    # Left mouth corner
    (28.9, -28.9, -24.1),     # Right mouth corner
)


# ══════════════════════════════════════════════════════════════════════════
#  FACE MESH  (landmarks.py)
# ══════════════════════════════════════════════════════════════════════════

# Max faces MediaPipe should track. We need >1 so we can DETECT the
# "multiple_faces_detected" edge case (spec §5) rather than silently ignore it.
FACE_MESH_MAX_FACES: int = _env_int("ATTN_FACE_MESH_MAX_FACES", 3)

# MediaPipe confidence thresholds.
FACE_MESH_MIN_DETECTION_CONFIDENCE: float = _env_float("ATTN_FACE_MIN_DET_CONF", 0.5)
FACE_MESH_MIN_TRACKING_CONFIDENCE: float = _env_float("ATTN_FACE_MIN_TRACK_CONF", 0.5)

# Use the refined landmark model (iris + more accurate eyes/lips).
FACE_MESH_REFINE_LANDMARKS: bool = _env_bool("ATTN_FACE_REFINE_LANDMARKS", True)


# ══════════════════════════════════════════════════════════════════════════
#  GAZE  (gaze.py — L2CS-Net, OPTIONAL / feature-flagged)
# ══════════════════════════════════════════════════════════════════════════

# Master switch. Default OFF so the core pipeline (MediaPipe + EAR + head-pose
# + DeepFace) works immediately without downloading L2CS-Net weights.
ENABLE_GAZE: bool = _env_bool("ATTN_ENABLE_GAZE", False)

# Half-angle (degrees) of the "looking at screen" cone. When gaze is enabled,
# a frame passes the gaze gate if BOTH yaw and pitch gaze angles are within it.
GAZE_SCREEN_CONE_DEG: float = _env_float("ATTN_GAZE_SCREEN_CONE_DEG", 30.0)

# Path to L2CS-Net pretrained weights (.pkl). Relative paths resolve against
# the repo. Only used when ENABLE_GAZE is True.
GAZE_WEIGHTS_PATH: str = os.getenv(
    "ATTN_GAZE_WEIGHTS_PATH",
    os.path.join("external", "L2CS-Net", "models", "L2CSNet_gaze360.pkl"),
)

# Torch device string for gaze inference ("cpu" or "cuda:0").
GAZE_DEVICE: str = os.getenv("ATTN_GAZE_DEVICE", "cpu")


# ══════════════════════════════════════════════════════════════════════════
#  FACE RECOGNITION  (recognition.py — DeepFace / ArcFace)
# ══════════════════════════════════════════════════════════════════════════

# DeepFace model + detector backend used for BOTH enrolment and matching.
RECOGNITION_MODEL_NAME: str = os.getenv("ATTN_RECOGNITION_MODEL", "ArcFace")
RECOGNITION_DETECTOR_BACKEND: str = os.getenv("ATTN_RECOGNITION_DETECTOR", "opencv")

# ArcFace produces a 512-dimensional embedding.
RECOGNITION_EMBEDDING_DIM: int = 512

# Cosine-SIMILARITY threshold for a positive identity match (spec §5: ~0.5-0.6).
# similarity = 1 - cosine_distance. Match when similarity >= this value.
RECOGNITION_COSINE_THRESHOLD: float = _env_float("ATTN_RECOGNITION_COSINE_THRESHOLD", 0.55)

# Enrolment requires between MIN and MAX reference photos (spec §5: 3-5).
ENROLL_MIN_PHOTOS: int = _env_int("ATTN_ENROLL_MIN_PHOTOS", 3)
ENROLL_MAX_PHOTOS: int = _env_int("ATTN_ENROLL_MAX_PHOTOS", 5)


# ══════════════════════════════════════════════════════════════════════════
#  EDGE-CASE FLAGS  (scorer.py)  — spec §5
# ══════════════════════════════════════════════════════════════════════════

# Continuous "no face" duration (seconds) after which we raise `left_seat`.
LEFT_SEAT_SECONDS: float = _env_float("ATTN_LEFT_SEAT_SECONDS", 30.0)

# Canonical flag strings (kept as constants so producers/consumers never drift).
FLAG_LEFT_SEAT: str = "left_seat"
FLAG_MULTIPLE_FACES: str = "multiple_faces_detected"
FLAG_VIEWER_CHANGED: str = "viewer_changed"
FLAG_UNRECOGNIZED_VIEWER: str = "unrecognized_viewer"


# ══════════════════════════════════════════════════════════════════════════
#  Introspection helper (handy for /health + debugging)
# ══════════════════════════════════════════════════════════════════════════
def as_dict() -> dict:
    """Return the effective configuration as a plain dict (for logging / health)."""
    return {
        "attendance_threshold": ATTENDANCE_THRESHOLD,
        "sample_fps": SAMPLE_FPS,
        "ear_threshold": EAR_THRESHOLD,
        "head_yaw_max_deg": HEAD_YAW_MAX_DEG,
        "head_pitch_max_deg": HEAD_PITCH_MAX_DEG,
        "enable_gaze": ENABLE_GAZE,
        "gaze_screen_cone_deg": GAZE_SCREEN_CONE_DEG,
        "recognition_model": RECOGNITION_MODEL_NAME,
        "recognition_cosine_threshold": RECOGNITION_COSINE_THRESHOLD,
        "left_seat_seconds": LEFT_SEAT_SECONDS,
    }
