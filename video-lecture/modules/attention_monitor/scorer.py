"""
scorer.py — Per-frame attentiveness + session-level aggregation.

This is the orchestration heart of the module. It combines the outputs of
`landmarks`, `formulas`, `gaze`, and `recognition` into:

  1. `analyze_frame()` → a per-frame `FrameResult` implementing spec §4:
         is_attentive = face_detected
                        AND head_pose is frontal
                        AND EAR >= threshold
                        (AND gaze on-screen, only when gaze is available)

  2. `SessionAggregator` → accumulates per-frame results and, at session end,
     computes:
         attention_ratio = attentive_frames / total_sampled_frames
         status          = "Present" if ratio >= ATTENDANCE_THRESHOLD else "Absent"
     while raising the edge-case flags from spec §5:
         left_seat, multiple_faces_detected, viewer_changed, unrecognized_viewer

Privacy (§6): this module only ever handles decoded frames transiently and
stores nothing but derived numbers/booleans. No image is retained.

It is fully DB-independent — the API layer feeds it frames and persists the
`SessionResult` it returns.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np

from . import config
from .landmarks import FaceMeshDetector, FaceLandmarks
from . import formulas
from .gaze import GazeEstimator, GazeResult
from . import recognition
from .recognition import MatchResult


# ══════════════════════════════════════════════════════════════════════════
#  Per-frame result
# ══════════════════════════════════════════════════════════════════════════

@dataclass
class FrameResult:
    """Derived, image-free metrics for one sampled frame.

    Only numbers/booleans — safe to log or persist (no pixels).
    """

    # Presence
    face_detected: bool = False
    face_count: int = 0

    # Metrics
    ear: float = 0.0
    eyes_open: bool = False
    yaw_deg: float = 0.0
    pitch_deg: float = 0.0
    roll_deg: float = 0.0
    head_frontal: bool = False

    # Gaze (only meaningful when gaze_available)
    gaze_available: bool = False
    gaze_on_screen: bool = True
    gaze_yaw_deg: float = 0.0
    gaze_pitch_deg: float = 0.0

    # Identity (populated only when enrolled embeddings are supplied)
    identity_checked: bool = False
    matched_student_id: Optional[int] = None
    identity_similarity: float = 0.0
    identity_matched: bool = False

    # Final verdict for this frame
    is_attentive: bool = False

    def to_dict(self) -> dict:
        """JSON-friendly view (used by the local test harness / debugging)."""
        return {
            "face_detected": self.face_detected,
            "face_count": self.face_count,
            "ear": round(self.ear, 4),
            "eyes_open": self.eyes_open,
            "yaw_deg": round(self.yaw_deg, 2),
            "pitch_deg": round(self.pitch_deg, 2),
            "roll_deg": round(self.roll_deg, 2),
            "head_frontal": self.head_frontal,
            "gaze_available": self.gaze_available,
            "gaze_on_screen": self.gaze_on_screen,
            "identity_checked": self.identity_checked,
            "matched_student_id": self.matched_student_id,
            "identity_similarity": round(self.identity_similarity, 4),
            "identity_matched": self.identity_matched,
            "is_attentive": self.is_attentive,
        }


# ══════════════════════════════════════════════════════════════════════════
#  Per-frame analysis
# ══════════════════════════════════════════════════════════════════════════

def analyze_frame(
    frame_bgr: np.ndarray,
    detector: FaceMeshDetector,
    *,
    gaze_estimator: Optional[GazeEstimator] = None,
    enrolled: Optional[Dict[int, np.ndarray]] = None,
    recognition_threshold: Optional[float] = None,
) -> FrameResult:
    """Run the full per-frame pipeline and return derived metrics.

    Parameters
    ----------
    frame_bgr : np.ndarray
        Decoded BGR frame (in memory).
    detector : FaceMeshDetector
        Reusable MediaPipe wrapper (caller owns its lifecycle).
    gaze_estimator : GazeEstimator, optional
        If provided AND available, adds the gaze gate. If None/unavailable,
        gaze is skipped and does NOT block attentiveness.
    enrolled : dict[int, np.ndarray], optional
        {student_id: embedding}. When supplied, identity is checked so the
        aggregator can detect `viewer_changed` / `unrecognized_viewer`.
    recognition_threshold : float, optional
        Override for the cosine match threshold.

    Returns
    -------
    FrameResult
    """
    result = FrameResult()

    faces: List[FaceLandmarks] = detector.detect(frame_bgr)
    result.face_count = len(faces)
    result.face_detected = len(faces) > 0

    if not result.face_detected:
        # No face → not attentive. Identity/gaze irrelevant this frame.
        return result

    primary = faces[0]

    # ── EAR (eyes open/closed) ─────────────────────────────────────────
    result.ear = formulas.average_ear(primary)
    result.eyes_open = result.ear >= config.EAR_THRESHOLD

    # ── Head pose (frontal?) ───────────────────────────────────────────
    pose = formulas.estimate_head_pose(primary)
    result.yaw_deg = pose.yaw
    result.pitch_deg = pose.pitch
    result.roll_deg = pose.roll
    result.head_frontal = formulas.is_frontal(pose)

    # ── Gaze (optional, additive) ──────────────────────────────────────
    if gaze_estimator is not None and gaze_estimator.available:
        gaze: GazeResult = gaze_estimator.estimate_gaze(frame_bgr)
        result.gaze_available = gaze.available
        result.gaze_on_screen = gaze.on_screen
        result.gaze_yaw_deg = gaze.yaw_deg
        result.gaze_pitch_deg = gaze.pitch_deg
    else:
        result.gaze_available = False
        result.gaze_on_screen = True  # neutral: never blocks when unavailable

    # ── Identity (optional; enables viewer_changed / unrecognized) ─────
    if enrolled:
        match: MatchResult = recognition.identify_frame(
            frame_bgr, enrolled, threshold=recognition_threshold
        )
        result.identity_checked = True
        result.matched_student_id = match.matched_id
        result.identity_similarity = match.similarity
        result.identity_matched = match.is_match

    # ── Final per-frame verdict (spec §4) ──────────────────────────────
    gaze_gate = (not result.gaze_available) or result.gaze_on_screen
    result.is_attentive = bool(
        result.face_detected
        and result.head_frontal
        and result.eyes_open
        and gaze_gate
    )
    return result


# ══════════════════════════════════════════════════════════════════════════
#  Session-level result
# ══════════════════════════════════════════════════════════════════════════

@dataclass
class SessionResult:
    """Final aggregated outcome for a whole viewing session (spec §6)."""

    total_sampled_frames: int
    attentive_frames: int
    attention_ratio: float
    status: str
    flags: List[str] = field(default_factory=list)

    # Extra telemetry (not required by §6 but useful downstream)
    face_present_frames: int = 0
    unrecognized_viewer: bool = False

    def to_dict(self) -> dict:
        return {
            "total_sampled_frames": self.total_sampled_frames,
            "attentive_frames": self.attentive_frames,
            "attention_ratio": round(self.attention_ratio, 4),
            "status": self.status,
            "flags": list(self.flags),
            "face_present_frames": self.face_present_frames,
            "unrecognized_viewer": self.unrecognized_viewer,
        }


# ══════════════════════════════════════════════════════════════════════════
#  Session aggregator
# ══════════════════════════════════════════════════════════════════════════

class SessionAggregator:
    """Accumulates per-frame results and produces the session decision.

    The API layer creates ONE aggregator per viewing session, calls `add()`
    for each sampled frame (~1 fps), then `finalize()` at session end.

    `expected_student_id` is the identity the viewer recognized as at session
    start; if a *different* enrolled student is later matched, we flag
    `viewer_changed`. If recognition is active but never matches anyone, we
    flag `unrecognized_viewer`.
    """

    def __init__(
        self,
        expected_student_id: Optional[int] = None,
        *,
        sample_interval_seconds: Optional[float] = None,
        left_seat_seconds: Optional[float] = None,
        attendance_threshold: Optional[float] = None,
    ) -> None:
        self.expected_student_id = expected_student_id
        self.sample_interval_seconds = (
            sample_interval_seconds
            if sample_interval_seconds is not None
            else config.SAMPLE_INTERVAL_SECONDS
        )
        self.left_seat_seconds = (
            left_seat_seconds if left_seat_seconds is not None else config.LEFT_SEAT_SECONDS
        )
        self.attendance_threshold = (
            attendance_threshold
            if attendance_threshold is not None
            else config.ATTENDANCE_THRESHOLD
        )

        # Counters
        self.total_frames: int = 0
        self.attentive_frames: int = 0
        self.face_present_frames: int = 0

        # Edge-case tracking
        self._flags: set[str] = set()
        self._consecutive_no_face: int = 0
        self._seen_matched_ids: set[int] = set()
        self._any_identity_checked: bool = False
        self._any_identity_matched: bool = False

    # ──────────────────────────────────────────────────────────────────
    #  Ingest one sampled frame
    # ──────────────────────────────────────────────────────────────────
    def add(self, frame: FrameResult) -> None:
        """Fold a single `FrameResult` into the running aggregate."""
        self.total_frames += 1

        if frame.is_attentive:
            self.attentive_frames += 1

        # ── Presence / left_seat (spec §5) ─────────────────────────────
        if frame.face_detected:
            self.face_present_frames += 1
            self._consecutive_no_face = 0
        else:
            self._consecutive_no_face += 1
            # Continuous no-face beyond the threshold duration → left_seat.
            no_face_seconds = self._consecutive_no_face * self.sample_interval_seconds
            if no_face_seconds >= self.left_seat_seconds:
                self._flags.add(config.FLAG_LEFT_SEAT)

        # ── Multiple faces (spec §5) ───────────────────────────────────
        if frame.face_count > 1:
            self._flags.add(config.FLAG_MULTIPLE_FACES)

        # ── Identity: viewer_changed / unrecognized (spec §5) ──────────
        if frame.identity_checked:
            self._any_identity_checked = True
            if frame.identity_matched and frame.matched_student_id is not None:
                self._any_identity_matched = True
                self._seen_matched_ids.add(frame.matched_student_id)

                # If we know who was expected and a DIFFERENT enrolled student
                # is now matched, someone swapped in.
                if (
                    self.expected_student_id is not None
                    and frame.matched_student_id != self.expected_student_id
                ):
                    self._flags.add(config.FLAG_VIEWER_CHANGED)

        # If a face is present but never matches any enrolled identity across
        # the session, the final unrecognized decision is made in finalize().

    # ──────────────────────────────────────────────────────────────────
    #  Mark the start-of-session recognition outcome
    # ──────────────────────────────────────────────────────────────────
    def note_start_recognition(self, match: MatchResult) -> None:
        """Record the session-start identity check (from /session/start).

        If recognition ran but produced no match, we set `unrecognized_viewer`
        immediately (spec §5: "do not silently proceed").
        """
        self._any_identity_checked = True
        if match.is_match and match.matched_id is not None:
            self._any_identity_matched = True
            self._seen_matched_ids.add(match.matched_id)
            if self.expected_student_id is None:
                self.expected_student_id = match.matched_id
        else:
            self._flags.add(config.FLAG_UNRECOGNIZED_VIEWER)

    # ──────────────────────────────────────────────────────────────────
    #  Finalize → SessionResult
    # ──────────────────────────────────────────────────────────────────
    def finalize(self) -> SessionResult:
        """Compute the final attention ratio, status, and flag set."""
        # More than one distinct enrolled identity across the session → changed.
        if len(self._seen_matched_ids) > 1:
            self._flags.add(config.FLAG_VIEWER_CHANGED)

        # Recognition was active but nobody was ever matched → unrecognized.
        unrecognized = self._any_identity_checked and not self._any_identity_matched
        if unrecognized:
            self._flags.add(config.FLAG_UNRECOGNIZED_VIEWER)

        ratio = (
            self.attentive_frames / self.total_frames if self.total_frames > 0 else 0.0
        )
        status = (
            config.STATUS_PRESENT
            if ratio >= self.attendance_threshold
            else config.STATUS_ABSENT
        )

        return SessionResult(
            total_sampled_frames=self.total_frames,
            attentive_frames=self.attentive_frames,
            attention_ratio=ratio,
            status=status,
            flags=sorted(self._flags),
            face_present_frames=self.face_present_frames,
            unrecognized_viewer=unrecognized
            or (config.FLAG_UNRECOGNIZED_VIEWER in self._flags),
        )

    # ──────────────────────────────────────────────────────────────────
    #  Snapshot (for live progress without ending the session)
    # ──────────────────────────────────────────────────────────────────
    def snapshot_ratio(self) -> float:
        """Current attention ratio so far (does not finalize)."""
        if self.total_frames == 0:
            return 0.0
        return self.attentive_frames / self.total_frames
