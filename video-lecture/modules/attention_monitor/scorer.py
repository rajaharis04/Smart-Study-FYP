"""
scorer.py — Per-frame attentiveness + session-level aggregation.

This is the orchestration heart of the module. It combines the outputs of
`landmarks`, `formulas` (EAR / head-pose / iris-gaze), `gaze` (L2CS-Net),
`recognition` (ArcFace), `temporal` (blink-vs-drowsy / PERCLOS / smoothing),
and `liveness` (anti-spoof) into:

  1. `analyze_frame()` → per-frame RAW signals (`FrameResult`). The LIGHT tier
     (landmarks + EAR + head-pose + iris gaze) runs every frame; the HEAVY tier
     (L2CS-Net gaze, ArcFace recognition, MiniFASNet liveness) runs only when
     the caller passes the corresponding `run_*` flag (CPU throttling lives in
     the API layer, which knows the per-session timing).

  2. `SessionAggregator` → owns the temporal trackers and resolves each frame
     into exactly ONE state:
         attentive | looking_away | eyes_closed | drowsy | no_face |
         multiple_faces | not_you | spoof
     It smooths the DISPLAY state (anti-flicker), counts attentive frames for
     the session ratio, and raises the spec-§5 edge-case flags.

Blink vs sleep: a brief eye-closure (<= BLINK_MAX_SECONDS) is a normal blink
and does NOT break attention; a prolonged closure (>= DROWSY_MIN_SECONDS) or a
high PERCLOS is `drowsy`.

Privacy (§6): only decoded frames are handled transiently; nothing but derived
numbers/booleans is retained. No image is stored.

Backward compatibility: `analyze_frame(frame, detector, gaze_estimator=..., 
enrolled=...)` and `aggregator.add(frame)` still work (the local webcam harness
relies on them); the new temporal behaviour activates automatically.
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
from . import temporal
from . import liveness


# ══════════════════════════════════════════════════════════════════════════
#  Per-frame result (RAW signals — temporal state resolved by the aggregator)
# ══════════════════════════════════════════════════════════════════════════

@dataclass
class FrameResult:
    """Derived, image-free metrics for one sampled frame.

    Only numbers/booleans — safe to log or persist (no pixels).
    """

    # Presence
    face_detected: bool = False
    face_count: int = 0

    # Eyes
    ear: float = 0.0
    eyes_open: bool = False

    # Head pose
    yaw_deg: float = 0.0
    pitch_deg: float = 0.0
    roll_deg: float = 0.0
    head_frontal: bool = False

    # Iris gaze (cheap, per-frame)
    iris_available: bool = False
    iris_on_screen: bool = True
    iris_h_ratio: float = 0.0
    iris_v_ratio: float = 0.0

    # L2CS-Net gaze (throttled; only meaningful when gaze_available)
    gaze_available: bool = False
    gaze_on_screen: bool = True
    gaze_yaw_deg: float = 0.0
    gaze_pitch_deg: float = 0.0
    gaze_checked: bool = False   # did the heavy model run THIS frame?

    # Identity (populated only when recognition ran this frame)
    identity_checked: bool = False
    matched_student_id: Optional[int] = None
    identity_similarity: float = 0.0
    identity_matched: bool = False

    # Liveness / anti-spoof (passive model; throttled)
    liveness_checked: bool = False
    liveness_is_real: Optional[bool] = None
    liveness_score: float = 0.0

    # Provisional per-frame verdict (NON-temporal; aggregator has the final say).
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
            "iris_available": self.iris_available,
            "iris_on_screen": self.iris_on_screen,
            "gaze_available": self.gaze_available,
            "gaze_on_screen": self.gaze_on_screen,
            "gaze_checked": self.gaze_checked,
            "identity_checked": self.identity_checked,
            "matched_student_id": self.matched_student_id,
            "identity_similarity": round(self.identity_similarity, 4),
            "identity_matched": self.identity_matched,
            "liveness_checked": self.liveness_checked,
            "liveness_is_real": self.liveness_is_real,
            "liveness_score": round(self.liveness_score, 4),
            "is_attentive": self.is_attentive,
        }


# ══════════════════════════════════════════════════════════════════════════
#  Per-frame analysis (LIGHT tier always; HEAVY tier gated by run_* flags)
# ══════════════════════════════════════════════════════════════════════════

def analyze_frame(
    frame_bgr: np.ndarray,
    detector: FaceMeshDetector,
    *,
    gaze_estimator: Optional[GazeEstimator] = None,
    enrolled: Optional[Dict[int, np.ndarray]] = None,
    recognition_threshold: Optional[float] = None,
    run_gaze_model: bool = False,
    run_recognition: Optional[bool] = None,
    run_liveness: bool = False,
) -> FrameResult:
    """Run the per-frame pipeline and return derived metrics.

    LIGHT tier (every call): face mesh, EAR, head-pose, iris gaze.
    HEAVY tier (only when requested):
      • run_gaze_model  → L2CS-Net precise gaze (uses MediaPipe face crop).
      • run_recognition → ArcFace identity check (defaults to True when an
                          `enrolled` set is supplied, for harness compatibility).
      • run_liveness    → MiniFASNet passive anti-spoof.
    """
    result = FrameResult()

    faces: List[FaceLandmarks] = detector.detect(frame_bgr)
    result.face_count = len(faces)
    result.face_detected = len(faces) > 0

    if not result.face_detected:
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

    # ── Iris gaze (cheap, per-frame) ───────────────────────────────────
    if config.ENABLE_IRIS_GAZE:
        iris = formulas.estimate_iris_gaze(primary)
        result.iris_available = iris.success
        result.iris_on_screen = iris.on_screen
        result.iris_h_ratio = iris.h_ratio
        result.iris_v_ratio = iris.v_ratio

    # ── L2CS-Net gaze (throttled, precise confirm) ─────────────────────
    if run_gaze_model and gaze_estimator is not None and gaze_estimator.available:
        gaze: GazeResult = gaze_estimator.estimate_gaze_from_crop(
            frame_bgr, bbox=primary.bbox()
        )
        result.gaze_available = gaze.available
        result.gaze_on_screen = gaze.on_screen
        result.gaze_yaw_deg = gaze.yaw_deg
        result.gaze_pitch_deg = gaze.pitch_deg
        result.gaze_checked = gaze.available
    else:
        result.gaze_available = False
        result.gaze_on_screen = True  # neutral: never blocks when not run

    # ── Identity (ArcFace; throttled) ──────────────────────────────────
    do_reco = run_recognition if run_recognition is not None else bool(enrolled)
    if do_reco and enrolled:
        match: MatchResult = recognition.identify_frame(
            frame_bgr, enrolled, threshold=recognition_threshold
        )
        result.identity_checked = True
        result.matched_student_id = match.matched_id
        result.identity_similarity = match.similarity
        result.identity_matched = match.is_match

    # ── Liveness / anti-spoof (MiniFASNet; throttled) ──────────────────
    if run_liveness and config.ENABLE_ANTISPOOF:
        live = liveness.passive_is_real(frame_bgr)
        result.liveness_checked = live.checked
        result.liveness_is_real = live.is_real
        result.liveness_score = live.score

    # ── Provisional per-frame verdict (non-temporal; harness convenience)
    gaze_gate = (not result.gaze_available) or result.gaze_on_screen
    iris_gate = (not result.iris_available) or result.iris_on_screen
    result.is_attentive = bool(
        result.face_detected
        and result.face_count == 1
        and result.head_frontal
        and result.eyes_open
        and gaze_gate
        and iris_gate
    )
    return result


# ══════════════════════════════════════════════════════════════════════════
#  Live per-frame status (returned by the aggregator for the UI)
# ══════════════════════════════════════════════════════════════════════════

# Human-readable messages per state (surfaced to the student).
STATE_MESSAGES: Dict[str, str] = {
    config.STATE_ATTENTIVE: "Attentive",
    config.STATE_LOOKING_AWAY: "Looking away",
    config.STATE_EYES_CLOSED: "Eyes closed",
    config.STATE_DROWSY: "Drowsy / sleeping",
    config.STATE_NO_FACE: "No face detected",
    config.STATE_MULTIPLE_FACES: "Multiple faces",
    config.STATE_NOT_RECOGNIZED: "Not the enrolled student",
    config.STATE_SPOOF: "Spoof suspected (photo?)",
}


@dataclass
class LiveStatus:
    """What the aggregator returns for each frame — drives the live UI."""

    state: str                    # SMOOTHED state (for display)
    raw_state: str                # this frame's raw state
    message: str                  # human text for `state`
    is_attentive: bool            # raw attentive (counts toward ratio)
    attention_ratio_so_far: float
    perclos: float
    drowsy: bool
    blink_count: int
    face_count: int
    ear: float
    eyes_open: bool
    yaw_deg: float
    pitch_deg: float
    gaze_available: bool
    gaze_on_screen: bool
    identity_checked: bool
    identity_matched: bool
    matched_student_id: Optional[int]
    liveness_checked: bool
    liveness_is_real: Optional[bool]
    spoof_suspected: bool

    def to_dict(self) -> dict:
        return {
            "state": self.state,
            "raw_state": self.raw_state,
            "message": self.message,
            "attentive": self.is_attentive,
            "is_attentive": self.is_attentive,  # legacy alias
            "attention_ratio_so_far": round(self.attention_ratio_so_far, 4),
            "perclos": round(self.perclos, 4),
            "drowsy": self.drowsy,
            "blink_count": self.blink_count,
            "face_detected": self.face_count > 0,
            "face_count": self.face_count,
            "ear": round(self.ear, 4),
            "eyes_open": self.eyes_open,
            "yaw_deg": round(self.yaw_deg, 2),
            "pitch_deg": round(self.pitch_deg, 2),
            "gaze_available": self.gaze_available,
            "gaze_on_screen": self.gaze_on_screen,
            "identity_checked": self.identity_checked,
            "identity_matched": self.identity_matched,
            "matched_student_id": self.matched_student_id,
            "liveness_checked": self.liveness_checked,
            "liveness_is_real": self.liveness_is_real,
            "spoof_suspected": self.spoof_suspected,
        }


# ══════════════════════════════════════════════════════════════════════════
#  State resolution (pure function of one frame + its temporal signals)
# ══════════════════════════════════════════════════════════════════════════

def resolve_state(
    fr: FrameResult,
    eye_state: temporal.EyeClosureState,
    *,
    expected_student_id: Optional[int],
    spoof_suspected: bool,
) -> str:
    """Collapse all signals into ONE state, most-severe-first.

    Priority: no_face > multiple_faces > spoof > not_you > drowsy >
              eyes_closed(long) > looking_away > attentive.
    A short blink falls through the eye checks and does NOT break attention.
    """
    if fr.face_count == 0:
        return config.STATE_NO_FACE
    if fr.face_count > 1:
        return config.STATE_MULTIPLE_FACES
    if spoof_suspected:
        return config.STATE_SPOOF

    # Identity is only judged on frames where recognition actually ran; between
    # throttled checks the session-start lock holds (benefit of the doubt).
    if fr.identity_checked:
        if not fr.identity_matched or fr.matched_student_id is None:
            return config.STATE_NOT_RECOGNIZED
        if expected_student_id is not None and fr.matched_student_id != expected_student_id:
            return config.STATE_NOT_RECOGNIZED

    if eye_state.is_drowsy:
        return config.STATE_DROWSY

    # Eyes closed longer than a blink but not yet drowsy → eyes_closed.
    if not fr.eyes_open and not eye_state.is_blink:
        return config.STATE_EYES_CLOSED

    # Orientation / gaze (blink frames reach here and stay attentive if facing).
    if not fr.head_frontal:
        return config.STATE_LOOKING_AWAY
    if fr.iris_available and not fr.iris_on_screen:
        return config.STATE_LOOKING_AWAY
    if fr.gaze_available and not fr.gaze_on_screen:
        return config.STATE_LOOKING_AWAY

    return config.STATE_ATTENTIVE


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

    # Extra telemetry
    face_present_frames: int = 0
    unrecognized_viewer: bool = False
    drowsy_events: int = 0
    blink_count: int = 0
    spoof_frames: int = 0
    avg_perclos: float = 0.0
    state_breakdown: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "total_sampled_frames": self.total_sampled_frames,
            "attentive_frames": self.attentive_frames,
            "attention_ratio": round(self.attention_ratio, 4),
            "status": self.status,
            "flags": list(self.flags),
            "face_present_frames": self.face_present_frames,
            "unrecognized_viewer": self.unrecognized_viewer,
            "drowsy_events": self.drowsy_events,
            "blink_count": self.blink_count,
            "spoof_frames": self.spoof_frames,
            "avg_perclos": round(self.avg_perclos, 4),
            "state_breakdown": dict(self.state_breakdown),
        }


# ══════════════════════════════════════════════════════════════════════════
#  Session aggregator
# ══════════════════════════════════════════════════════════════════════════

class SessionAggregator:
    """Accumulates per-frame results and produces the session decision.

    The API layer creates ONE aggregator per viewing session, calls `add()`
    for each sampled frame, then `finalize()` at session end. It owns the
    temporal trackers (blink/drowsy, smoothing) so it can turn stateless
    per-frame signals into a robust, time-aware verdict.
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

        # Temporal machinery
        self._eye = temporal.EyeClosureTracker()
        self._smoother = temporal.StateSmoother()
        self._frame_index: int = 0
        self._perclos_sum: float = 0.0

        # State bookkeeping
        self._state_counts: Dict[str, int] = {}
        self._drowsy_events: int = 0
        self._was_drowsy: bool = False
        self._spoof_frames: int = 0

        # Edge-case tracking
        self._flags: set[str] = set()
        self._consecutive_no_face: int = 0
        self._seen_matched_ids: set[int] = set()
        self._any_identity_checked: bool = False
        self._any_identity_matched: bool = False

    # ──────────────────────────────────────────────────────────────────
    #  Ingest one sampled frame
    # ──────────────────────────────────────────────────────────────────
    def add(self, frame: FrameResult, timestamp: Optional[float] = None) -> LiveStatus:
        """Fold a single `FrameResult` into the running aggregate.

        `timestamp` (monotonic seconds) drives the blink/drowsy timing. When
        omitted (e.g. the local harness), synthetic timestamps are derived from
        the sample interval so the temporal logic still works.
        """
        self.total_frames += 1
        if timestamp is None:
            timestamp = self._frame_index * self.sample_interval_seconds
        self._frame_index += 1

        # ── Temporal eye signals (blink vs drowsy, PERCLOS, liveness) ──
        eye_state = self._eye.update(timestamp, frame.ear, frame.eyes_open)
        self._perclos_sum += eye_state.perclos

        # ── Liveness fusion: passive model (if run) + behavioural blink ─
        spoof_suspected = False
        if frame.liveness_checked and frame.liveness_is_real is False:
            spoof_suspected = True
        if config.ENABLE_ANTISPOOF and liveness.behavioural_spoof_suspected(
            eye_state.seconds_since_blink,
            eye_state.ear_variance,
            face_present=frame.face_detected,
        ):
            spoof_suspected = True
        if spoof_suspected:
            self._spoof_frames += 1
            self._flags.add(config.FLAG_SPOOF)

        # ── Resolve the raw state, then smooth for display ─────────────
        raw_state = resolve_state(
            frame,
            eye_state,
            expected_student_id=self.expected_student_id,
            spoof_suspected=spoof_suspected,
        )
        smoothed = self._smoother.update(raw_state)

        self._state_counts[raw_state] = self._state_counts.get(raw_state, 0) + 1
        is_attentive = raw_state == config.STATE_ATTENTIVE
        if is_attentive:
            self.attentive_frames += 1

        # ── Drowsy events (rising edge) ────────────────────────────────
        if eye_state.is_drowsy:
            if not self._was_drowsy:
                self._drowsy_events += 1
                self._flags.add(config.FLAG_DROWSY)
            self._was_drowsy = True
        else:
            self._was_drowsy = False

        # ── Presence / left_seat (spec §5) ─────────────────────────────
        if frame.face_detected:
            self.face_present_frames += 1
            self._consecutive_no_face = 0
        else:
            self._consecutive_no_face += 1
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
                if (
                    self.expected_student_id is not None
                    and frame.matched_student_id != self.expected_student_id
                ):
                    self._flags.add(config.FLAG_VIEWER_CHANGED)

        return LiveStatus(
            state=smoothed,
            raw_state=raw_state,
            message=STATE_MESSAGES.get(smoothed, smoothed),
            is_attentive=is_attentive,
            attention_ratio_so_far=self.snapshot_ratio(),
            perclos=eye_state.perclos,
            drowsy=eye_state.is_drowsy,
            blink_count=self._eye.blink_count,
            face_count=frame.face_count,
            ear=frame.ear,
            eyes_open=frame.eyes_open,
            yaw_deg=frame.yaw_deg,
            pitch_deg=frame.pitch_deg,
            gaze_available=frame.gaze_available,
            gaze_on_screen=frame.gaze_on_screen,
            identity_checked=frame.identity_checked,
            identity_matched=frame.identity_matched,
            matched_student_id=frame.matched_student_id,
            liveness_checked=frame.liveness_checked,
            liveness_is_real=frame.liveness_is_real,
            spoof_suspected=spoof_suspected,
        )

    # ──────────────────────────────────────────────────────────────────
    #  Mark the start-of-session recognition outcome
    # ──────────────────────────────────────────────────────────────────
    def note_start_recognition(self, match: MatchResult) -> None:
        """Record the session-start identity check (from /session/start).

        If recognition ran but produced no match, we set `unrecognized_viewer`
        immediately (spec §5: "do not silently proceed"). A successful match
        LOCKS the expected identity for the rest of the session.
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
        if len(self._seen_matched_ids) > 1:
            self._flags.add(config.FLAG_VIEWER_CHANGED)

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
        avg_perclos = (
            self._perclos_sum / self.total_frames if self.total_frames > 0 else 0.0
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
            drowsy_events=self._drowsy_events,
            blink_count=self._eye.blink_count,
            spoof_frames=self._spoof_frames,
            avg_perclos=avg_perclos,
            state_breakdown=dict(self._state_counts),
        )

    # ──────────────────────────────────────────────────────────────────
    #  Snapshot (for live progress without ending the session)
    # ──────────────────────────────────────────────────────────────────
    def snapshot_ratio(self) -> float:
        """Current attention ratio so far (does not finalize)."""
        if self.total_frames == 0:
            return 0.0
        return self.attentive_frames / self.total_frames
