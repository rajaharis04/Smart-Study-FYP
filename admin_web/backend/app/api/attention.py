"""
Attention & Presence Monitor API  (admin_web backend, Postgres persistence).

This router is the ONLY place where the CV module meets the web app + DB. It:
  • exposes the endpoints from spec §7,
  • persists results into the existing Postgres tables (`attention_sessions`,
    `attention_enrolled_faces`) and updates the existing `attendance` table,
  • maps `student_id` to the REAL `students` table via the existing
    `_get_current_student` auth pattern.

────────────────────────────────────────────────────────────────────────────
TWO-TIER CPU DESIGN (v2):
  Every sampled frame runs the LIGHT tier (MediaPipe landmarks + EAR +
  head-pose + iris gaze) — cheap enough for a few fps on CPU. The HEAVY models
  are THROTTLED per session on their own timers so they don't overload the CPU:
    • ArcFace recognition   → every config.RECOGNITION_REFRESH_SECONDS
    • L2CS-Net precise gaze  → every config.GAZE_REFRESH_SECONDS
    • MiniFASNet anti-spoof  → every config.LIVENESS_REFRESH_SECONDS
  Identity is LOCKED at session start; between recognition refreshes the lock
  holds. The temporal layer (blink-vs-drowsy, PERCLOS, smoothing) lives in the
  aggregator so the live state is stable and time-aware.
────────────────────────────────────────────────────────────────────────────

LAZY-IMPORT DESIGN (so the lean production backend keeps booting):
  The heavy CV stack (MediaPipe / DeepFace→TensorFlow / OpenCV / L2CS→Torch)
  is NEVER imported at module import-time. It is imported inside request
  handlers via `_load_cv()`. If those libraries aren't installed (i.e. the
  server is running in the lean venv), the CV endpoints return a clean
  HTTP 503 instead of crashing the whole app.

PRIVACY (spec §6 — hard constraint, enforced in code, not comments):
  Webcam frames arrive base64-encoded, are decoded into an in-memory numpy
  array, processed, and then explicitly `del`-eted. There is no cv2.imwrite,
  no file write, and no image bytes are stored in the DB — only derived
  numbers/booleans/flags.
"""
from __future__ import annotations

import os
import sys
import json
import time
import base64
import threading
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.models import (
    User, Student, Lecture, Section, Attendance,
    EnrolledFace, AttentionSession,
)
from app.services.auth_service import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
router = APIRouter(prefix="/attention", tags=["Attention & Presence Monitor"])


# ══════════════════════════════════════════════════════════════════════════
#  Auth dependency (mirrors the existing _get_current_student pattern)
# ══════════════════════════════════════════════════════════════════════════

def _get_current_student(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Student:
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")
    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found.")
    student = db.query(Student).filter(Student.user_id == user.id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student profile not found.")
    return student


# ══════════════════════════════════════════════════════════════════════════
#  Lazy CV loader  (keeps the lean backend importable)
# ══════════════════════════════════════════════════════════════════════════

# Cache for the imported CV surface so we only pay the import cost once.
_cv_cache: dict = {}


def _ensure_cv_on_path() -> None:
    """Add `<repo>/video-lecture/modules` to sys.path so `attention_monitor`
    (the pure CV package) can be imported. Idempotent."""
    # attention.py → app/api → app → backend → admin_web → <repo root>
    here = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.abspath(os.path.join(here, "..", "..", "..", ".."))
    modules_dir = os.path.join(repo_root, "video-lecture", "modules")
    if modules_dir not in sys.path:
        sys.path.insert(0, modules_dir)


def _load_cv() -> dict:
    """Import heavy CV deps + the pure module lazily.

    Returns a dict of the handles the routes need. Raises HTTP 503 with a
    helpful message if the CV stack isn't installed (lean venv).
    """
    if _cv_cache:
        return _cv_cache

    _ensure_cv_on_path()
    try:
        import numpy as np              # noqa: N813
        import cv2                       # noqa: F401
        from attention_monitor import config as cv_config
        from attention_monitor import recognition, scorer, liveness
        from attention_monitor.landmarks import FaceMeshDetector
        from attention_monitor.gaze import get_default_estimator
    except Exception as exc:  # ImportError or native-lib load failure
        raise HTTPException(
            status_code=503,
            detail=(
                "Attention CV engine not installed in this environment. "
                "Start the backend from the dedicated CV virtualenv "
                "(pip install -r requirements-attention.txt). "
                f"Import error: {exc}"
            ),
        ) from exc

    _cv_cache.update(
        np=np,
        cv2=cv2,
        config=cv_config,
        recognition=recognition,
        scorer=scorer,
        liveness=liveness,
        FaceMeshDetector=FaceMeshDetector,
        get_default_estimator=get_default_estimator,
    )
    return _cv_cache


# ══════════════════════════════════════════════════════════════════════════
#  Process-wide singletons + in-memory active-session registry
# ══════════════════════════════════════════════════════════════════════════

_LOCK = threading.Lock()          # guards detector use + registry (MediaPipe
                                  # is not thread-safe; low fps/student → fine).
_DETECTOR = None                  # FaceMeshDetector singleton (lazy)

# Active viewing sessions keyed by the persisted AttentionSession.id.
# Each value: {"aggregator", "enrolled", "student_id", "lecture_id",
#              "start_ts", "last_reco_ts", "last_gaze_ts", "last_liveness_ts"}
_SESSIONS: Dict[int, dict] = {}


def _get_detector():
    """Return the shared FaceMeshDetector, creating it on first use."""
    global _DETECTOR
    if _DETECTOR is None:
        cv = _load_cv()
        _DETECTOR = cv["FaceMeshDetector"]()
    return _DETECTOR


def warmup() -> bool:
    """Eagerly load the whole CV stack ONCE (heavy: TF/MediaPipe/DeepFace/Torch).

    Called from a background thread at server startup so the very first real
    request is fast instead of paying the ~15-40s cold-start cost mid-request.
    Warms ArcFace, the L2CS-Net gaze pipeline, and the anti-spoof model too so
    their first throttled use during a session doesn't stall a frame. Safe
    no-op / False in the lean venv where the CV libs aren't installed.
    """
    try:
        cv = _load_cv()          # numpy/cv2/mediapipe/deepface/tensorflow imports
        _get_detector()          # build MediaPipe FaceMesh
        np = cv["np"]
        dummy = np.full((160, 160, 3), 127, dtype=np.uint8)
        # Force the DeepFace/ArcFace model to build+cache with a dummy frame.
        try:
            cv["recognition"].embed_face(dummy)
        except Exception:
            pass  # no-face dummy may raise AFTER the model is cached — fine.
        # Warm the L2CS-Net gaze pipeline (loads Torch + weights if present).
        try:
            gaze = cv["get_default_estimator"]()
            if gaze.available:
                gaze.estimate_gaze(dummy)
                print("✅ L2CS-Net gaze warmed up.")
            else:
                print(f"ℹ️  Gaze not active ({gaze.load_error}); using iris gaze.")
        except Exception as exc:
            print(f"ℹ️  Gaze warm-up skipped: {exc}")
        # Warm the anti-spoof model.
        try:
            cv["liveness"].passive_is_real(dummy)
        except Exception:
            pass
        print("✅ Attention CV engine warmed up (models loaded).")
        return True
    except HTTPException:
        print("ℹ️  Attention CV engine not installed here; skipping warm-up.")
        return False
    except Exception as exc:  # pragma: no cover
        print(f"⚠️  Attention CV warm-up error (non-fatal): {exc}")
        return False


def _load_enrolled(db: Session, student_id: Optional[int] = None):
    """Load enrolled embeddings as {student_id: np.ndarray} for matching.

    If `student_id` is given, load ONLY that student's embedding (identity-lock:
    during a session we only need to confirm the same person, which keeps the
    match fast and unambiguous). Otherwise load all (used at session start).
    """
    cv = _load_cv()
    q = db.query(EnrolledFace)
    if student_id is not None:
        q = q.filter(EnrolledFace.student_id == student_id)
    rows = q.all()
    enrolled: Dict[int, "cv['np'].ndarray"] = {}
    for row in rows:
        try:
            values = json.loads(row.embedding)
            enrolled[row.student_id] = cv["recognition"].embedding_from_list(values)
        except Exception:
            continue
    return enrolled


def _decode_frame(image_base64: str):
    """Decode a base64 (optionally data-URL) image into an in-memory BGR array.

    Returns a numpy ndarray. Caller MUST `del` it after use (privacy §6).
    """
    cv = _load_cv()
    np = cv["np"]
    cv2 = cv["cv2"]

    # Strip a data-URL prefix like "data:image/jpeg;base64,"
    if "," in image_base64 and image_base64.strip().lower().startswith("data:"):
        image_base64 = image_base64.split(",", 1)[1]

    try:
        raw = base64.b64decode(image_base64)
        arr = np.frombuffer(raw, dtype=np.uint8)
        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)  # → BGR
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid image data: {exc}")

    if frame is None or getattr(frame, "size", 0) == 0:
        raise HTTPException(status_code=400, detail="Could not decode image frame.")
    return frame


# ══════════════════════════════════════════════════════════════════════════
#  Pydantic payloads
# ══════════════════════════════════════════════════════════════════════════

class EnrollPayload(BaseModel):
    images_base64: List[str] = Field(..., description="3-5 reference photos (base64).")


class SessionStartPayload(BaseModel):
    lecture_id: Optional[int] = Field(None, description="Lecture/video being watched.")
    image_base64: Optional[str] = Field(
        None, description="Optional first frame for start-of-session recognition."
    )


class FramePayload(BaseModel):
    session_id: int
    image_base64: str


class SessionEndPayload(BaseModel):
    session_id: int


# ══════════════════════════════════════════════════════════════════════════
#  ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════

@router.get("/status")
def attention_status():
    """Diagnostic: is the CV engine importable here, and is gaze available?

    Never raises — returns availability so a caller can decide whether to use
    the feature. (Does not require auth; leaks no data.)
    """
    try:
        cv = _load_cv()
    except HTTPException as exc:
        return {"cv_available": False, "detail": exc.detail}

    gaze = cv["get_default_estimator"]()
    return {
        "cv_available": True,
        "config": cv["config"].as_dict(),
        "gaze_enabled": cv["config"].ENABLE_GAZE,
        "gaze_available": gaze.available,
        "gaze_load_error": gaze.load_error,
        "antispoof_enabled": cv["config"].ENABLE_ANTISPOOF,
        "active_sessions": len(_SESSIONS),
    }


# ── Enrollment status ───────────────────────────────────────────────────────
@router.get("/enrollment/status")
def enrollment_status(
    student: Student = Depends(_get_current_student),
    db: Session = Depends(get_db),
):
    """Has THIS student already enrolled their face? Drives the one-time wizard.

    The Flutter client calls this before offering monitoring: if `enrolled` is
    true it skips the capture wizard and goes straight to monitoring.
    """
    row = db.query(EnrolledFace).filter(EnrolledFace.student_id == student.id).first()
    return {
        "enrolled": row is not None,
        "student_id": student.id,
        "num_photos": row.num_photos if row else 0,
        "model": row.model_name if row else None,
        "updated_at": row.updated_at.isoformat() if row and row.updated_at else None,
    }


# ── Enrollment ──────────────────────────────────────────────────────────────
@router.post("/enroll")
def enroll_student(
    payload: EnrollPayload,
    student: Student = Depends(_get_current_student),
    db: Session = Depends(get_db),
):
    """Register the authenticated student's face (spec §5.1).

    Captures 3-5 reference photos, builds ONE averaged ArcFace embedding, and
    stores it in `attention_enrolled_faces` (upsert). Each photo is also run
    through the anti-spoof check so a student can't enrol from a photo of a
    photo. Raw photos are decoded in memory and discarded — never written.
    """
    cv = _load_cv()
    recognition = cv["recognition"]
    liveness = cv["liveness"]
    config = cv["config"]

    if not payload.images_base64:
        raise HTTPException(status_code=400, detail="No photos provided.")

    # Decode all photos into memory.
    frames = []
    spoof_hits = 0
    try:
        for b64 in payload.images_base64:
            frames.append(_decode_frame(b64))

        # Anti-spoof gate on enrolment (best-effort; skips if model unavailable).
        if config.ENABLE_ANTISPOOF:
            for f in frames:
                res = liveness.passive_is_real(f)
                if res.checked and res.is_real is False:
                    spoof_hits += 1
            # If the MAJORITY of usable photos look like spoofs, reject.
            if spoof_hits > len(frames) // 2:
                raise HTTPException(
                    status_code=422,
                    detail="Enrollment photos look like a photo/screen (spoof). "
                           "Please enroll using your live face.",
                )

        try:
            embedding = recognition.build_enrollment_embedding(frames)
        except recognition.EnrollmentError as exc:
            raise HTTPException(status_code=422, detail=str(exc))

        embedding_json = json.dumps(recognition.embedding_to_list(embedding))
        num_photos = len(frames)
    finally:
        # Privacy §6: destroy all decoded frames regardless of outcome.
        for f in frames:
            del f
        del frames

    # Upsert the student's enrolled face.
    row = db.query(EnrolledFace).filter(EnrolledFace.student_id == student.id).first()
    if row:
        row.embedding = embedding_json
        row.model_name = config.RECOGNITION_MODEL_NAME
        row.num_photos = num_photos
        row.updated_at = datetime.utcnow()
    else:
        row = EnrolledFace(
            student_id=student.id,
            embedding=embedding_json,
            model_name=config.RECOGNITION_MODEL_NAME,
            num_photos=num_photos,
        )
        db.add(row)
    db.commit()
    db.refresh(row)

    return {
        "ok": True,
        "student_id": student.id,
        "enrolled_face_id": row.id,
        "num_photos_used": num_photos,
        "model": row.model_name,
    }


# ── Session start ─────────────────────────────────────────────────────────
@router.post("/session/start")
def session_start(
    payload: SessionStartPayload,
    student: Student = Depends(_get_current_student),
    db: Session = Depends(get_db),
):
    """Begin a monitored viewing session (spec §5.2).

    Creates an `attention_sessions` row and an in-memory aggregator. If a first
    frame is supplied, runs recognition immediately to LOCK the identity; a
    non-match sets the `unrecognized_viewer` flag ("do not silently proceed").
    """
    cv = _load_cv()
    scorer = cv["scorer"]
    recognition = cv["recognition"]

    # Persist the session shell first (so we have an id to key the aggregator).
    db_session = AttentionSession(
        student_id=student.id,
        lecture_id=payload.lecture_id,
        video_id=payload.lecture_id,
        session_start=datetime.utcnow(),
        total_sampled_frames=0,
        attentive_frames=0,
        attention_ratio=0.0,
        is_complete=False,
    )
    db.add(db_session)
    db.commit()
    db.refresh(db_session)

    # Identity-lock: only this student's embedding is needed during the session.
    enrolled = _load_enrolled(db, student_id=student.id)
    aggregator = scorer.SessionAggregator(expected_student_id=student.id)

    recognized = False
    unrecognized_viewer = False

    if payload.image_base64 and enrolled:
        frame = _decode_frame(payload.image_base64)
        try:
            with _LOCK:
                match = recognition.identify_frame(frame, enrolled)
            aggregator.note_start_recognition(match)
            recognized = bool(match.is_match)
            unrecognized_viewer = not recognized
            if recognized:
                db_session.recognized_student_id = match.matched_id
        finally:
            del frame  # privacy §6

    db_session.unrecognized_viewer = unrecognized_viewer
    db.commit()

    now = time.monotonic()
    # Stash the live aggregator + enrolled set + throttle timers for /frame.
    with _LOCK:
        _SESSIONS[db_session.id] = {
            "aggregator": aggregator,
            "enrolled": enrolled,
            "student_id": student.id,
            "lecture_id": payload.lecture_id,
            "start_ts": now,
            # Seed the recognition timer so the first refresh waits the interval.
            "last_reco_ts": now,
            "last_gaze_ts": 0.0,       # 0 → run gaze on the very first frame
            "last_liveness_ts": 0.0,   # 0 → run liveness on the very first frame
        }

    return {
        "ok": True,
        "session_id": db_session.id,
        "recognized": recognized,
        "unrecognized_viewer": unrecognized_viewer,
        "enrolled_students_known": len(enrolled),
    }


# ── Per-frame sample ────────────────────────────────────────────────────────
@router.post("/frame")
def session_frame(
    payload: FramePayload,
    student: Student = Depends(_get_current_student),
    db: Session = Depends(get_db),
):
    """Process ONE sampled frame for an active session (spec §5.3, two-tier).

    LIGHT tier runs every frame; HEAVY models (recognition/gaze/liveness) run
    only when their per-session throttle interval has elapsed. Returns the
    smoothed live state + metrics; the frame is destroyed before returning.
    """
    cv = _load_cv()
    scorer = cv["scorer"]
    config = cv["config"]

    with _LOCK:
        state = _SESSIONS.get(payload.session_id)

    if not state:
        raise HTTPException(
            status_code=404,
            detail="No active session with that id (start one via /attention/session/start).",
        )
    if state["student_id"] != student.id:
        raise HTTPException(status_code=403, detail="Session does not belong to you.")

    # ── Decide which HEAVY models run this frame (CPU throttle) ────────
    now = time.monotonic()
    run_reco = (now - state.get("last_reco_ts", 0.0)) >= config.RECOGNITION_REFRESH_SECONDS
    run_gaze = (now - state.get("last_gaze_ts", 0.0)) >= config.GAZE_REFRESH_SECONDS
    run_live = (
        config.ENABLE_ANTISPOOF
        and (now - state.get("last_liveness_ts", 0.0)) >= config.LIVENESS_REFRESH_SECONDS
    )

    frame = _decode_frame(payload.image_base64)
    try:
        detector = _get_detector()
        gaze = cv["get_default_estimator"]()
        # Serialize CV work (MediaPipe not thread-safe).
        with _LOCK:
            frame_result = scorer.analyze_frame(
                frame,
                detector,
                gaze_estimator=gaze,
                enrolled=(state["enrolled"] or None),
                run_gaze_model=run_gaze,
                run_recognition=run_reco,
                run_liveness=run_live,
            )
            live = state["aggregator"].add(frame_result, timestamp=now - state["start_ts"])
            # Advance the throttle timers only for models that actually ran.
            if run_reco:
                state["last_reco_ts"] = now
            if run_gaze:
                state["last_gaze_ts"] = now
            if run_live:
                state["last_liveness_ts"] = now
    finally:
        del frame  # privacy §6 — no image survives this request

    result = live.to_dict()
    result["session_id"] = payload.session_id
    return result


# ── Session end ─────────────────────────────────────────────────────────────
@router.post("/session/end")
def session_end(
    payload: SessionEndPayload,
    student: Student = Depends(_get_current_student),
    db: Session = Depends(get_db),
):
    """Finalize a session (spec §5.4): compute ratio + Present/Absent, persist
    the `attention_sessions` record, and update the `attendance` table.
    """
    cv = _load_cv()

    with _LOCK:
        state = _SESSIONS.pop(payload.session_id, None)

    if not state:
        raise HTTPException(status_code=404, detail="No active session with that id.")
    if state["student_id"] != student.id:
        # Put it back so the rightful owner can still end it.
        with _LOCK:
            _SESSIONS[payload.session_id] = state
        raise HTTPException(status_code=403, detail="Session does not belong to you.")

    session_result = state["aggregator"].finalize()

    # ── Persist the AttentionSession row ───────────────────────────────
    db_session = db.query(AttentionSession).filter(
        AttentionSession.id == payload.session_id
    ).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session record not found in DB.")

    db_session.session_end = datetime.utcnow()
    db_session.total_sampled_frames = session_result.total_sampled_frames
    db_session.attentive_frames = session_result.attentive_frames
    db_session.attention_ratio = session_result.attention_ratio
    db_session.status = session_result.status
    db_session.flags = json.dumps(session_result.flags)
    db_session.unrecognized_viewer = session_result.unrecognized_viewer
    db_session.is_complete = True
    # New v2 telemetry (columns are nullable / auto-migrated).
    _set_if_has(db_session, "drowsy_events", session_result.drowsy_events)
    _set_if_has(db_session, "blink_count", session_result.blink_count)
    _set_if_has(db_session, "spoof_frames", session_result.spoof_frames)
    _set_if_has(db_session, "avg_perclos", session_result.avg_perclos)
    _set_if_has(db_session, "state_breakdown", json.dumps(session_result.state_breakdown))

    # ── Update the existing Attendance table (decision #1) ─────────────
    attendance_written = False
    lecture_id = state.get("lecture_id")
    if lecture_id:
        lecture = db.query(Lecture).filter(Lecture.id == lecture_id).first()
        section_id = lecture.section_id if lecture else None
        if section_id:
            is_present = session_result.status == cv["config"].STATUS_PRESENT
            att = db.query(Attendance).filter(
                Attendance.student_id == student.id,
                Attendance.lecture_id == lecture_id,
            ).first()
            if att:
                att.is_present = is_present
                att.attention_ratio = session_result.attention_ratio
                att.attention_status = session_result.status
                att.attention_flags = json.dumps(session_result.flags)
                att.attention_marked_at = datetime.utcnow()
                att.marked_at = datetime.utcnow()
            else:
                att = Attendance(
                    student_id=student.id,
                    lecture_id=lecture_id,
                    section_id=section_id,
                    is_present=is_present,
                    marked_at=datetime.utcnow(),
                    attention_ratio=session_result.attention_ratio,
                    attention_status=session_result.status,
                    attention_flags=json.dumps(session_result.flags),
                    attention_marked_at=datetime.utcnow(),
                )
                db.add(att)
            attendance_written = True

    db.commit()

    payload_out = session_result.to_dict()
    payload_out.update(
        {
            "ok": True,
            "session_id": payload.session_id,
            "attendance_updated": attendance_written,
        }
    )
    return payload_out


# ── Report ────────────────────────────────────────────────────────────────
@router.get("/report/{student_id}")
def attention_report(
    student_id: int,
    student: Student = Depends(_get_current_student),
    db: Session = Depends(get_db),
):
    """Return a student's attention-session history (spec §7).

    Students may only view their own report. (Teacher/admin dashboards are
    explicitly out of scope per spec §9.)
    """
    if student_id != student.id:
        raise HTTPException(
            status_code=403,
            detail="You can only view your own attention report.",
        )

    sessions = db.query(AttentionSession).filter(
        AttentionSession.student_id == student_id
    ).order_by(AttentionSession.session_start.desc()).all()

    def _flags(row) -> List[str]:
        if not row.flags:
            return []
        try:
            return json.loads(row.flags)
        except Exception:
            return []

    records = [
        {
            "session_id": s.id,
            "lecture_id": s.lecture_id,
            "video_id": s.video_id,
            "session_start": s.session_start.isoformat() if s.session_start else None,
            "session_end": s.session_end.isoformat() if s.session_end else None,
            "total_sampled_frames": s.total_sampled_frames,
            "attentive_frames": s.attentive_frames,
            "attention_ratio": round(s.attention_ratio or 0.0, 4),
            "status": s.status,
            "flags": _flags(s),
            "unrecognized_viewer": s.unrecognized_viewer,
            "is_complete": s.is_complete,
            "drowsy_events": getattr(s, "drowsy_events", None),
            "avg_perclos": getattr(s, "avg_perclos", None),
        }
        for s in sessions
    ]

    completed = [r for r in records if r["is_complete"]]
    present = sum(1 for r in completed if r["status"] == "Present")

    return {
        "student_id": student_id,
        "total_sessions": len(records),
        "completed_sessions": len(completed),
        "present_sessions": present,
        "sessions": records,
    }


# ══════════════════════════════════════════════════════════════════════════
#  Internals
# ══════════════════════════════════════════════════════════════════════════

def _set_if_has(obj, attr: str, value) -> None:
    """Set an attribute only if the ORM model actually declares it.

    Lets the API populate new v2 telemetry columns when present, while staying
    compatible with an older DB/model that hasn't been migrated yet.
    """
    if hasattr(obj, attr):
        try:
            setattr(obj, attr, value)
        except Exception:
            pass
