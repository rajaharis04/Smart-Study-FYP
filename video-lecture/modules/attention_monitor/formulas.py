"""
formulas.py — Classical CV maths: Eye-Aspect-Ratio (EAR) + head pose.

No trained model here — this is pure geometry (spec §3/§4):

  • EAR  : eye open/closed state from 6 eye landmarks.
  • Head : yaw/pitch/roll via OpenCV solvePnP on 6 facial landmarks
           against a generic 3D face reference model.

Everything operates on a `FaceLandmarks` produced by `landmarks.py`.
Functions are deterministic, side-effect free, and easily unit-testable.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence, Tuple

import numpy as np
import cv2

from . import config
from .landmarks import FaceLandmarks


# ══════════════════════════════════════════════════════════════════════════
#  EYE ASPECT RATIO
# ══════════════════════════════════════════════════════════════════════════

def _euclidean(a: np.ndarray, b: np.ndarray) -> float:
    """L2 distance between two 2D points."""
    return float(np.linalg.norm(a - b))


def eye_aspect_ratio(points: np.ndarray, eye_idx: Sequence[int]) -> float:
    """Compute EAR for a single eye.

    Uses the 6-point formula (Soukupová & Čech, 2016):

        EAR = (‖p2-p6‖ + ‖p3-p5‖) / (2 · ‖p1-p4‖)

    where the six indices in `eye_idx` are ordered (p1..p6) as:
        p1 = outer corner, p4 = inner corner  (horizontal),
        p2, p3 = upper-lid points,
        p5, p6 = lower-lid points.

    Parameters
    ----------
    points : np.ndarray
        (N, 2) array of all face landmarks (pixel coords).
    eye_idx : Sequence[int]
        The 6 landmark indices for this eye, in p1..p6 order.

    Returns
    -------
    float
        The eye aspect ratio. ~0.3 for an open eye, → 0 as it closes.
    """
    p1, p2, p3, p4, p5, p6 = (points[i] for i in eye_idx)

    vertical = _euclidean(p2, p6) + _euclidean(p3, p5)
    horizontal = 2.0 * _euclidean(p1, p4)

    if horizontal == 0.0:
        return 0.0
    return vertical / horizontal


def average_ear(face: FaceLandmarks) -> float:
    """Mean EAR across both eyes for a face."""
    left = eye_aspect_ratio(face.points, config.LEFT_EYE_EAR_IDX)
    right = eye_aspect_ratio(face.points, config.RIGHT_EYE_EAR_IDX)
    return (left + right) / 2.0


def eyes_open(face: FaceLandmarks, threshold: float | None = None) -> bool:
    """True if the (averaged) eyes are open, i.e. EAR >= threshold."""
    thr = config.EAR_THRESHOLD if threshold is None else threshold
    return average_ear(face) >= thr


# ══════════════════════════════════════════════════════════════════════════
#  HEAD POSE  (solvePnP → yaw / pitch / roll)
# ══════════════════════════════════════════════════════════════════════════

@dataclass
class HeadPose:
    """Head orientation in degrees.

    yaw   : left/right turn  (looking sideways)
    pitch : up/down tilt     (nodding)
    roll  : in-plane rotation (head tilt to shoulder)
    success : whether solvePnP produced a usable solution.
    """

    yaw: float
    pitch: float
    roll: float
    success: bool


def _camera_matrix(image_width: int, image_height: int) -> np.ndarray:
    """Build a generic pinhole camera intrinsic matrix.

    We approximate the focal length as the image width and place the optical
    centre at the image centre — the standard assumption for webcam head-pose
    when no calibration data is available.
    """
    focal_length = float(image_width)
    center_x = image_width / 2.0
    center_y = image_height / 2.0
    return np.array(
        [
            [focal_length, 0.0, center_x],
            [0.0, focal_length, center_y],
            [0.0, 0.0, 1.0],
        ],
        dtype=np.float64,
    )


def _normalize_angle(angle_deg: float) -> float:
    """Fold a raw Euler angle into the intuitive [-90, 90] range.

    RQDecomp3x3 can report e.g. 178° for a small backward pitch; folding makes
    the frontal-cone thresholds behave predictably.
    """
    a = float(angle_deg)
    if a > 90.0:
        a -= 180.0
    elif a < -90.0:
        a += 180.0
    return a


def estimate_head_pose(face: FaceLandmarks) -> HeadPose:
    """Estimate yaw/pitch/roll for a face using cv2.solvePnP.

    Pipeline (spec §4):
      1. Take the 6 MediaPipe 2D landmarks in `HEAD_POSE_LANDMARK_IDX`.
      2. Pair them with the generic 3D reference model `FACE_MODEL_3D_POINTS`.
      3. solvePnP → rotation vector.
      4. Rodrigues → rotation matrix.
      5. RQDecomp3x3 → Euler angles (pitch, yaw, roll).

    Returns a `HeadPose`; `success=False` if the solver fails.
    """
    image_points = np.array(
        [face.points[i] for i in config.HEAD_POSE_LANDMARK_IDX],
        dtype=np.float64,
    )
    model_points = np.array(config.FACE_MODEL_3D_POINTS, dtype=np.float64)

    camera_matrix = _camera_matrix(face.image_width, face.image_height)
    dist_coeffs = np.zeros((4, 1), dtype=np.float64)  # assume no lens distortion

    ok, rotation_vec, _translation_vec = cv2.solvePnP(
        model_points,
        image_points,
        camera_matrix,
        dist_coeffs,
        flags=cv2.SOLVEPNP_ITERATIVE,
    )
    if not ok:
        return HeadPose(yaw=0.0, pitch=0.0, roll=0.0, success=False)

    rotation_mat, _ = cv2.Rodrigues(rotation_vec)
    # RQDecomp3x3 returns (euler_angles, ...); euler is [pitch, yaw, roll] in deg.
    euler_angles, *_ = cv2.RQDecomp3x3(rotation_mat)
    pitch, yaw, roll = (float(a) for a in euler_angles[:3])

    return HeadPose(
        yaw=_normalize_angle(yaw),
        pitch=_normalize_angle(pitch),
        roll=_normalize_angle(roll),
        success=True,
    )


def is_frontal(
    pose: HeadPose,
    yaw_max: float | None = None,
    pitch_max: float | None = None,
) -> bool:
    """True if the head is oriented toward the screen (spec §4).

        frontal ⇔ |yaw| < yaw_max  AND  |pitch| < pitch_max
    """
    if not pose.success:
        return False
    y_max = config.HEAD_YAW_MAX_DEG if yaw_max is None else yaw_max
    p_max = config.HEAD_PITCH_MAX_DEG if pitch_max is None else pitch_max
    return abs(pose.yaw) < y_max and abs(pose.pitch) < p_max
