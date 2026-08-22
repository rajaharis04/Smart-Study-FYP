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

# Spec §4 baseline was 1 fps. On CPU we can afford a LIGHT per-frame tier at a
# few fps (MediaPipe landmarks + EAR + head-pose + iris gaze), while the HEAVY
# models (ArcFace recognition, L2CS-Net gaze, anti-spoof) stay throttled — see
# RECOGNITION_REFRESH_SECONDS / GAZE_REFRESH_SECONDS / LIVENESS_REFRESH_SECONDS.
# This makes the live on-screen feedback feel real-time without overloading CPU.
SAMPLE_FPS: float = _env_float("ATTN_SAMPLE_FPS", 3.0)
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
#  BLINK vs DROWSY  (temporal.py / scorer.py)
# ══════════════════════════════════════════════════════════════════════════
#
# A single low-EAR frame does NOT mean the student is sleeping — a normal blink
# lasts ~100-400 ms. We distinguish:
#   • blink  : eyes closed for a SHORT burst (<= BLINK_MAX_SECONDS) — normal,
#              NOT penalized as inattentive.
#   • drowsy : eyes closed CONTINUOUSLY for >= DROWSY_MIN_SECONDS — sleeping.
#   • PERCLOS: fraction of time (over a rolling window) that eyes are closed;
#              a high PERCLOS is the classic fatigue indicator.

# Continuous eye-closure below this duration is treated as a benign blink.
BLINK_MAX_SECONDS: float = _env_float("ATTN_BLINK_MAX_SECONDS", 0.5)

# Continuous eye-closure at/above this duration is flagged as drowsy/sleeping.
DROWSY_MIN_SECONDS: float = _env_float("ATTN_DROWSY_MIN_SECONDS", 1.5)

# Rolling window (seconds) over which PERCLOS is measured.
PERCLOS_WINDOW_SECONDS: float = _env_float("ATTN_PERCLOS_WINDOW_SECONDS", 20.0)

# PERCLOS fraction (0..1) above which the student is considered fatigued.
PERCLOS_THRESHOLD: float = _env_float("ATTN_PERCLOS_THRESHOLD", 0.45)


# ══════════════════════════════════════════════════════════════════════════
#  TEMPORAL SMOOTHING  (temporal.py)
# ══════════════════════════════════════════════════════════════════════════
#
# Per-frame verdicts flicker (one stray frame shouldn't flip the live badge).
# We smooth the displayed state over a short sliding window using a majority
# vote, so the UI is stable and the ratio is robust.
SMOOTHING_WINDOW_FRAMES: int = _env_int("ATTN_SMOOTHING_WINDOW_FRAMES", 5)


# ══════════════════════════════════════════════════════════════════════════
#  ATTENTION STATES  (scorer.py)  — single source of truth for the live label
# ══════════════════════════════════════════════════════════════════════════
#
# Every sampled frame resolves to exactly ONE of these states. The Flutter UI
# maps them to a color + message so the student sees WHY they're (in)attentive.
STATE_ATTENTIVE: str = "attentive"
STATE_LOOKING_AWAY: str = "looking_away"     # head/gaze off-screen
STATE_EYES_CLOSED: str = "eyes_closed"       # short closure (blink-ish)
STATE_DROWSY: str = "drowsy"                 # prolonged closure / high PERCLOS
STATE_NO_FACE: str = "no_face"               # nobody in frame
STATE_MULTIPLE_FACES: str = "multiple_faces" # more than one face
STATE_NOT_RECOGNIZED: str = "not_you"        # face present but not the enrolled student
STATE_SPOOF: str = "spoof"                   # likely photo/video presentation attack

# Only this state counts as "attentive" when computing the session ratio.
ATTENTIVE_STATES: tuple[str, ...] = (STATE_ATTENTIVE,)


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
#  IRIS-BASED GAZE  (formulas.py)  — CHEAP, per-frame, CPU-friendly
# ══════════════════════════════════════════════════════════════════════════
#
# refine_landmarks=True gives MediaPipe's iris points (468-477). By comparing
# each iris centre to its eye corners we get a normalized horizontal/vertical
# gaze ratio essentially for FREE (no extra model). This is our per-frame gaze
# gate; the heavy L2CS-Net (gaze.py) only runs throttled as a precise confirm.

# Iris landmark indices (require FACE_MESH_REFINE_LANDMARKS=True).
LEFT_IRIS_IDX: tuple[int, int, int, int, int] = (468, 469, 470, 471, 472)
RIGHT_IRIS_IDX: tuple[int, int, int, int, int] = (473, 474, 475, 476, 477)
# Eye-corner indices used to normalize the iris centre position (outer, inner).
LEFT_EYE_CORNER_IDX: tuple[int, int] = (33, 133)
RIGHT_EYE_CORNER_IDX: tuple[int, int] = (362, 263)

# Master switch for the cheap iris gaze gate (kept on by default).
ENABLE_IRIS_GAZE: bool = _env_bool("ATTN_ENABLE_IRIS_GAZE", True)

# How far the iris may deviate from the eye centre (0 = centred, 1 = at corner)
# before we treat it as "looking away" horizontally / vertically.
IRIS_H_RATIO_MAX: float = _env_float("ATTN_IRIS_H_RATIO_MAX", 0.35)
IRIS_V_RATIO_MAX: float = _env_float("ATTN_IRIS_V_RATIO_MAX", 0.40)


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
# REQUIRED for the iris-based gaze gate above — keep True.
FACE_MESH_REFINE_LANDMARKS: bool = _env_bool("ATTN_FACE_REFINE_LANDMARKS", True)


# ══════════════════════════════════════════════════════════════════════════
#  GAZE  (gaze.py — L2CS-Net, precise confirm — THROTTLED on CPU)
# ══════════════════════════════════════════════════════════════════════════

# Master switch. Now ON by default; degrades gracefully to the iris gaze gate
# if Torch / L2CS-Net / weights are unavailable (never blocks attention).
ENABLE_GAZE: bool = _env_bool("ATTN_ENABLE_GAZE", True)

# Half-angle (degrees) of the "looking at screen" cone. When gaze is enabled,
# a frame passes the gaze gate if BOTH yaw and pitch gaze angles are within it.
GAZE_SCREEN_CONE_DEG: float = _env_float("ATTN_GAZE_SCREEN_CONE_DEG", 30.0)

# CPU throttle: run the heavy L2CS-Net gaze CNN at most once per this many
# seconds; between runs the cheap iris gaze gate carries the per-frame verdict.
GAZE_REFRESH_SECONDS: float = _env_float("ATTN_GAZE_REFRESH_SECONDS", 2.0)

# Feed L2CS-Net a MediaPipe-derived face crop (skip its slow internal detector)
# for a big CPU speed-up. Padding expands the crop around the face box.
GAZE_USE_FACE_CROP: bool = _env_bool("ATTN_GAZE_USE_FACE_CROP", True)
GAZE_CROP_PADDING: float = _env_float("ATTN_GAZE_CROP_PADDING", 0.30)

# Path to L2CS-Net pretrained weights (.pkl). Relative paths resolve against
# the repo. Only used when ENABLE_GAZE is True.
GAZE_WEIGHTS_PATH: str = os.getenv(
    "ATTN_GAZE_WEIGHTS_PATH",
    os.path.join("video-lecture", "external", "L2CS-Net", "models", "L2CSNet_gaze360.pkl"),
)

# Torch device string for gaze inference ("cpu" or "cuda:0").
GAZE_DEVICE: str = os.getenv("ATTN_GAZE_DEVICE", "cpu")


# ══════════════════════════════════════════════════════════════════════════
#  FACE RECOGNITION  (recognition.py — DeepFace / ArcFace) — THROTTLED
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

# CPU throttle: after the identity is LOCKED at session start, re-verify the
# viewer with ArcFace at most once per this many seconds (guards against a
# viewer swap) instead of every frame — recognition is the most expensive op.
RECOGNITION_REFRESH_SECONDS: float = _env_float("ATTN_RECOGNITION_REFRESH_SECONDS", 4.0)


# ══════════════════════════════════════════════════════════════════════════
#  LIVENESS / ANTI-SPOOF  (liveness.py)
# ══════════════════════════════════════════════════════════════════════════
#
# Stops a student holding a PHOTO/phone-video to the camera. Two signals:
#   1. Passive texture check — DeepFace's silent anti-spoofing (MiniFASNet)
#      classifies a single frame as real vs presentation-attack.
#   2. Behavioural check — a real person blinks; if EAR stays almost constant
#      (no blink) for a long stretch, that's photo-like.

ENABLE_ANTISPOOF: bool = _env_bool("ATTN_ENABLE_ANTISPOOF", True)

# CPU throttle for the passive texture model (seconds between checks).
LIVENESS_REFRESH_SECONDS: float = _env_float("ATTN_LIVENESS_REFRESH_SECONDS", 5.0)

# MiniFASNet real-vs-fake confidence (0..1) at/above which we accept "real".
ANTISPOOF_REAL_THRESHOLD: float = _env_float("ATTN_ANTISPOOF_REAL_THRESHOLD", 0.60)

# Behavioural liveness: if no blink is observed for this many seconds while a
# face IS present, raise suspicion of a static photo.
NO_BLINK_SUSPECT_SECONDS: float = _env_float("ATTN_NO_BLINK_SUSPECT_SECONDS", 25.0)

# EAR variance below this (over the PERCLOS window) is "suspiciously static".
EAR_STATIC_VARIANCE_MAX: float = _env_float("ATTN_EAR_STATIC_VARIANCE_MAX", 0.0002)


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
FLAG_DROWSY: str = "drowsy_detected"
FLAG_SPOOF: str = "spoof_suspected"


# ══════════════════════════════════════════════════════════════════════════
#  Introspection helper (handy for /health + debugging)
# ══════════════════════════════════════════════════════════════════════════
def as_dict() -> dict:
    """Return the effective configuration as a plain dict (for logging / health)."""
    return {
        "attendance_threshold": ATTENDANCE_THRESHOLD,
        "sample_fps": SAMPLE_FPS,
        "ear_threshold": EAR_THRESHOLD,
        "blink_max_seconds": BLINK_MAX_SECONDS,
        "drowsy_min_seconds": DROWSY_MIN_SECONDS,
        "perclos_window_seconds": PERCLOS_WINDOW_SECONDS,
        "perclos_threshold": PERCLOS_THRESHOLD,
        "smoothing_window_frames": SMOOTHING_WINDOW_FRAMES,
        "head_yaw_max_deg": HEAD_YAW_MAX_DEG,
        "head_pitch_max_deg": HEAD_PITCH_MAX_DEG,
        "enable_iris_gaze": ENABLE_IRIS_GAZE,
        "enable_gaze": ENABLE_GAZE,
        "gaze_screen_cone_deg": GAZE_SCREEN_CONE_DEG,
        "gaze_refresh_seconds": GAZE_REFRESH_SECONDS,
        "recognition_model": RECOGNITION_MODEL_NAME,
        "recognition_cosine_threshold": RECOGNITION_COSINE_THRESHOLD,
        "recognition_refresh_seconds": RECOGNITION_REFRESH_SECONDS,
        "enable_antispoof": ENABLE_ANTISPOOF,
        "liveness_refresh_seconds": LIVENESS_REFRESH_SECONDS,
        "left_seat_seconds": LEFT_SEAT_SECONDS,
    }
