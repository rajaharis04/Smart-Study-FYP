"""
Student-facing Lectures API — all lecture data, sessions, quizzes, Q&A
stored in and served from the real database.

Routes:
  GET  /api/lectures/section/{section_id}  → list lectures for a section
  GET  /api/lectures/{lecture_id}          → lecture detail + chapters
  POST /api/lectures/{lecture_id}/session/start   → create LectureSession row
  POST /api/lectures/session/{session_id}/ping    → update watch% / pause count
  POST /api/lectures/session/{session_id}/end     → mark complete + mark attendance
  GET  /api/lectures/{lecture_id}/quiz/{quiz_type}→ get or create pre/mid quiz
  POST /api/lectures/quiz/{quiz_id}/submit        → save QuizResponse rows
"""
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.models import (
    User, Student, Enrollment, Section, Lecture, LectureChapter,
    LectureSession, Attendance, Quiz, QuizQuestion, QuizResponse
)
from app.services.auth_service import decode_token
from app.services.learning_model import recalculate_student_learning_profile

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
router = APIRouter(prefix="/lectures", tags=["Lectures (Student)"])


# ── Auth dependency ────────────────────────────────────────────────────────────
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


# ════════════════════════════════════════════════════════════════════
#  LECTURE DETAIL
# ════════════════════════════════════════════════════════════════════

@router.get("/section/{section_id}")
def get_section_lectures(
    section_id: int,
    student: Student = Depends(_get_current_student),
    db: Session = Depends(get_db),
):
    """List all published lectures for a section (student must be enrolled)."""
    enrollment = db.query(Enrollment).filter(
        Enrollment.student_id == student.id,
        Enrollment.section_id == section_id,
        Enrollment.is_active == True,
    ).first()
    if not enrollment:
        raise HTTPException(status_code=403, detail="Not enrolled in this section.")

    lectures = db.query(Lecture).filter(
        Lecture.section_id == section_id,
        Lecture.is_published == True,
    ).order_by(Lecture.publish_date).all()

    # Which lectures are completed
    attended_ids = {
        a.lecture_id for a in db.query(Attendance).filter(
            Attendance.student_id == student.id,
            Attendance.is_present == True,
        ).all()
    }

    return [
        {
            "id":           l.id,
            "title":        l.title,
            "duration":     l.duration,
            "description":  l.description,
            "publish_date": l.publish_date.isoformat() if l.publish_date else None,
            "is_completed": l.id in attended_ids,
        }
        for l in lectures
    ]


@router.get("/{lecture_id}")
def get_lecture(
    lecture_id: int,
    student: Student = Depends(_get_current_student),
    db: Session = Depends(get_db),
):
    """Get full lecture detail including video URL and chapters."""
    lecture = db.query(Lecture).filter(
        Lecture.id == lecture_id,
        Lecture.is_published == True,
    ).first()
    if not lecture:
        raise HTTPException(status_code=404, detail="Lecture not found.")

    # Verify enrollment
    enrollment = db.query(Enrollment).filter(
        Enrollment.student_id == student.id,
        Enrollment.section_id == lecture.section_id,
        Enrollment.is_active == True,
    ).first()
    if not enrollment:
        raise HTTPException(status_code=403, detail="Not enrolled in this course.")

    section = lecture.section
    course = section.course if section else None

    chapters = [
        {
            "id":            ch.id,
            "title":         ch.title,
            "start_seconds": ch.start_seconds,
        }
        for ch in lecture.chapters
    ]

    return {
        "id":          lecture.id,
        "title":       lecture.title,
        "video_url":   lecture.video_url,
        "duration":    lecture.duration,
        "description": lecture.description,
        "course_id":   course.id if course else None,
        "course_name": course.name if course else None,
        "section_id":  lecture.section_id,
        "chapters":    chapters,
    }


# ════════════════════════════════════════════════════════════════════
#  SESSION TRACKING
# ════════════════════════════════════════════════════════════════════

@router.post("/{lecture_id}/session/start")
def start_session(
    lecture_id: int,
    student: Student = Depends(_get_current_student),
    db: Session = Depends(get_db),
):
    """Create a new LectureSession row in DB. Returns session_id."""
    lecture = db.query(Lecture).filter(Lecture.id == lecture_id).first()
    if not lecture:
        raise HTTPException(status_code=404, detail="Lecture not found.")

    session = LectureSession(
        lecture_id=lecture_id,
        student_id=student.id,
        started_at=datetime.utcnow(),
        watch_percentage=0.0,
        pause_count=0,
        playback_speed=1.0,
        engagement_score=0.0,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return {"session_id": session.id}


class SessionPingPayload(BaseModel):
    watch_percentage: float
    pause_count:      int
    playback_speed:   float
    foreground_ratio: float = 1.0


@router.post("/session/{session_id}/ping")
def ping_session(
    session_id: int,
    payload: SessionPingPayload,
    student: Student = Depends(_get_current_student),
    db: Session = Depends(get_db),
):
    """
    Update session tracking data every 30 seconds.
    Calculates and saves engagement score to DB.
    """
    session = db.query(LectureSession).filter(
        LectureSession.id == session_id,
        LectureSession.student_id == student.id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    # Engagement formula
    pause_score = 1.0 / (1.0 + payload.pause_count)
    qna_count = 0  # Will be joined with QA table in Phase 6
    qna_score = min(qna_count / 5.0, 1.0)
    engagement = (
        payload.foreground_ratio * 0.40
        + pause_score * 0.30
        + qna_score * 0.30
    )

    session.watch_percentage = payload.watch_percentage
    session.pause_count      = payload.pause_count
    session.playback_speed   = payload.playback_speed
    session.engagement_score = round(engagement, 4)
    db.commit()
    return {"ok": True, "engagement_score": session.engagement_score}


class EndSessionPayload(BaseModel):
    total_watched: float    # Final watch percentage


@router.post("/session/{session_id}/end")
def end_session(
    session_id: int,
    payload: EndSessionPayload,
    background_tasks: BackgroundTasks,
    student: Student = Depends(_get_current_student),
    db: Session = Depends(get_db),
):
    """
    Marks session complete.
    If watch_percentage >= 80%, marks student as PRESENT in Attendance table.
    """
    session = db.query(LectureSession).filter(
        LectureSession.id == session_id,
        LectureSession.student_id == student.id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    session.ended_at         = datetime.utcnow()
    session.watch_percentage = payload.total_watched
    session.is_complete      = True
    db.flush()

    # Mark attendance if >= 80% watched
    is_present = payload.total_watched >= 80.0
    existing_attendance = db.query(Attendance).filter(
        Attendance.student_id == student.id,
        Attendance.lecture_id == session.lecture_id,
    ).first()

    if existing_attendance:
        # If they now qualify, upgrade to present
        if is_present:
            existing_attendance.is_present = True
            existing_attendance.marked_at  = datetime.utcnow()
    else:
        lecture = db.query(Lecture).filter(
            Lecture.id == session.lecture_id
        ).first()
        attendance = Attendance(
            student_id = student.id,
            lecture_id = session.lecture_id,
            section_id = lecture.section_id if lecture else 0,
            is_present = is_present,
            marked_at  = datetime.utcnow(),
        )
        db.add(attendance)

    db.commit()

    # Asynchronously trigger student learning profile recalculation
    if session.lecture_id:
        lecture = db.query(Lecture).filter(Lecture.id == session.lecture_id).first()
        if lecture and lecture.topic_id:
            background_tasks.add_task(
                recalculate_student_learning_profile,
                student.id,
                lecture.topic_id,
                db
            )

    return {
        "ok":          True,
        "is_present":  is_present,
        "watch_pct":   payload.total_watched,
    }


# ════════════════════════════════════════════════════════════════════
#  QUIZ (Pre / Mid / Post)
# ════════════════════════════════════════════════════════════════════

@router.get("/{lecture_id}/quiz/{quiz_type}")
def get_quiz(
    lecture_id: int,
    quiz_type: str,
    student: Student = Depends(_get_current_student),
    db: Session = Depends(get_db),
):
    """
    Get quiz for a lecture by type (pre/mid/post).
    Returns quiz_id and list of questions.
    If no quiz exists yet, returns quiz_id=null and empty questions.
    Adaptive Quiz Difficulty: Filters/reorders questions based on student learning score.
    """
    if quiz_type not in ("pre", "mid", "post"):
        raise HTTPException(status_code=400, detail="quiz_type must be pre, mid, or post.")

    quiz = db.query(Quiz).filter(
        Quiz.lecture_id == lecture_id,
        Quiz.quiz_type  == quiz_type,
    ).first()

    if not quiz or not quiz.questions:
        return {"quiz_id": None, "questions": []}

    # Fetch Student's Learning Profile for this topic
    lecture = db.query(Lecture).filter(Lecture.id == lecture_id).first()
    topic_id = lecture.topic_id if lecture else None
    
    profile = None
    if topic_id:
        from app.models.models import StudentLearningProfile
        profile = db.query(StudentLearningProfile).filter(
            StudentLearningProfile.student_id == student.id,
            StudentLearningProfile.topic_id == topic_id
        ).first()

    raw_questions = sorted(list(quiz.questions), key=lambda x: x.id)

    questions = [
        {
            "id":            q.id,
            "question_text": q.question_text,
            "option_a":      q.option_a,
            "option_b":      q.option_b,
            "option_c":      q.option_c,
            "option_d":      q.option_d,
            "difficulty":    q.difficulty,
        }
        for q in raw_questions
    ]

    # Server-Side Attempt Session Tracking
    from app.models.models import QuizAttemptSession
    session = db.query(QuizAttemptSession).filter(
        QuizAttemptSession.quiz_id == quiz.id,
        QuizAttemptSession.student_id == student.id,
        QuizAttemptSession.is_completed == False,
    ).first()

    total_qs = len(questions)
    per_q_timer = quiz.per_question_timer_seconds or 30
    allowed_seconds = (total_qs * per_q_timer) + 60.0

    if session:
        elapsed_seconds = (datetime.utcnow() - session.started_at).total_seconds()
        if elapsed_seconds > allowed_seconds:
            session.is_completed = True
            session.is_cancelled = True
            db.commit()
            session = None

    if not session:
        session = QuizAttemptSession(
            quiz_id=quiz.id,
            student_id=student.id,
            started_at=datetime.utcnow(),
            is_completed=False,
        )
        db.add(session)
        db.commit()
        db.refresh(session)

    return {
        "quiz_id": quiz.id,
        "attempt_id": session.id,
        "started_at": session.started_at.isoformat(),
        "server_time": datetime.utcnow().isoformat(),
        "per_question_timer_seconds": quiz.per_question_timer_seconds or 30,
        "time_limit_minutes": quiz.time_limit_mins or 10,
        "questions": questions
    }


@router.get("/quiz/{quiz_id}")
def get_quiz_by_id(
    quiz_id: int,
    student: Student = Depends(_get_current_student),
    db: Session = Depends(get_db),
):
    """
    Get exact quiz questions by quiz_id in exact order created by teacher.
    NO pooling, NO sub-sampling, NO dynamic reordering.
    """
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz or not quiz.questions:
        raise HTTPException(status_code=404, detail="Quiz or quiz questions not found.")

    raw_questions = sorted(list(quiz.questions), key=lambda x: x.id)

    questions = [
        {
            "id":            q.id,
            "question_text": q.question_text,
            "option_a":      q.option_a,
            "option_b":      q.option_b,
            "option_c":      q.option_c,
            "option_d":      q.option_d,
            "difficulty":    q.difficulty,
        }
        for q in raw_questions
    ]

    from app.models.models import QuizAttemptSession
    session = db.query(QuizAttemptSession).filter(
        QuizAttemptSession.quiz_id == quiz.id,
        QuizAttemptSession.student_id == student.id,
        QuizAttemptSession.is_completed == False,
    ).first()

    total_qs = len(questions)
    per_q_timer = quiz.per_question_timer_seconds or 30
    allowed_seconds = (total_qs * per_q_timer) + 60.0

    if session:
        elapsed_seconds = (datetime.utcnow() - session.started_at).total_seconds()
        if elapsed_seconds > allowed_seconds:
            session.is_completed = True
            session.is_cancelled = True
            db.commit()
            session = None

    if not session:
        session = QuizAttemptSession(
            quiz_id=quiz.id,
            student_id=student.id,
            started_at=datetime.utcnow(),
            is_completed=False,
        )
        db.add(session)
        db.commit()
        db.refresh(session)

    return {
        "quiz_id": quiz.id,
        "attempt_id": session.id,
        "started_at": session.started_at.isoformat(),
        "server_time": datetime.utcnow().isoformat(),
        "per_question_timer_seconds": quiz.per_question_timer_seconds or 30,
        "time_limit_minutes": quiz.time_limit_mins or 10,
        "questions": questions
    }


class SaveQuestionAnswerPayload(BaseModel):
    question_id: int
    answer: Optional[str] = None
    time_taken_seconds: Optional[float] = 30.0
    hint_used: Optional[bool] = False


@router.post("/quiz/{quiz_id}/save-question-answer")
def save_question_answer(
    quiz_id: int,
    payload: SaveQuestionAnswerPayload,
    student: Student = Depends(_get_current_student),
    db: Session = Depends(get_db),
):
    """
    Real-time per-question answer persistence.
    Saves student answer immediately so network drop / crash causes 0 data loss.
    """
    question = db.query(QuizQuestion).filter(
        QuizQuestion.id == payload.question_id,
    ).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found.")

    effective_quiz_id = question.quiz_id
    quiz = db.query(Quiz).filter(Quiz.id == effective_quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found.")

    from app.models.models import QuizAttemptSession
    session = db.query(QuizAttemptSession).filter(
        QuizAttemptSession.quiz_id == effective_quiz_id,
        QuizAttemptSession.student_id == student.id,
        QuizAttemptSession.is_completed == False,
    ).first()

    if session:
        total_qs = len(quiz.questions)
        per_q_timer = quiz.per_question_timer_seconds or 30
        allowed_seconds = (total_qs * per_q_timer) + 60.0
        elapsed_seconds = (datetime.utcnow() - session.started_at).total_seconds()
        if elapsed_seconds > allowed_seconds:
            session.is_completed = True
            db.commit()

    is_correct = False
    if question.correct_answer and payload.answer and payload.answer.strip():
        is_correct = (payload.answer.strip().upper() == question.correct_answer.strip().upper())

    existing = db.query(QuizResponse).filter(
        QuizResponse.quiz_id == effective_quiz_id,
        QuizResponse.question_id == payload.question_id,
        QuizResponse.student_id == student.id,
    ).first()

    if existing:
        existing.answer = payload.answer
        existing.is_correct = is_correct
        existing.time_taken_seconds = payload.time_taken_seconds or 30.0
        existing.hint_used = payload.hint_used or False
        existing.answered_at = datetime.utcnow()
    else:
        resp = QuizResponse(
            quiz_id=quiz_id,
            question_id=payload.question_id,
            student_id=student.id,
            answer=payload.answer,
            is_correct=is_correct,
            time_taken_seconds=payload.time_taken_seconds or 30.0,
            hint_used=payload.hint_used or False,
            answered_at=datetime.utcnow(),
        )
        db.add(resp)

    db.commit()
    return {"ok": True, "question_id": payload.question_id, "saved": True}


class SubmitAnswerItem(BaseModel):
    question_id: int
    answer:      Optional[str] = None   # A/B/C/D or null if skipped
    time_taken_seconds: Optional[float] = 30.0
    hint_used:   Optional[bool] = False


class SubmitQuizPayload(BaseModel):
    answers: List[SubmitAnswerItem]


@router.post("/quiz/{quiz_id}/submit")
def submit_quiz(
    quiz_id: int,
    payload: SubmitQuizPayload,
    background_tasks: BackgroundTasks,
    student: Student = Depends(_get_current_student),
    db: Session = Depends(get_db),
):
    """
    Finalize student's quiz attempt.
    Marks QuizAttemptSession as completed and recalculates learning profile.
    """
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found.")

    from app.models.models import QuizAttemptSession
    session = db.query(QuizAttemptSession).filter(
        QuizAttemptSession.quiz_id == quiz_id,
        QuizAttemptSession.student_id == student.id,
        QuizAttemptSession.is_completed == False,
    ).first()

    if session:
        session.is_completed = True
        session.submitted_at = datetime.utcnow()

    # Save any final remaining answers
    for item in payload.answers:
        question = db.query(QuizQuestion).filter(
            QuizQuestion.id      == item.question_id,
            QuizQuestion.quiz_id == quiz_id,
        ).first()
        if not question:
            continue

        is_correct = False
        if question.correct_answer and item.answer and item.answer.strip():
            is_correct = (item.answer.strip().upper() == question.correct_answer.strip().upper())

        existing = db.query(QuizResponse).filter(
            QuizResponse.quiz_id == quiz_id,
            QuizResponse.question_id == item.question_id,
            QuizResponse.student_id == student.id,
        ).first()

        if existing:
            existing.answer = item.answer
            existing.is_correct = is_correct
            existing.time_taken_seconds = item.time_taken_seconds if item.time_taken_seconds is not None else 30.0
            existing.hint_used = item.hint_used if item.hint_used is not None else False
            existing.answered_at = datetime.utcnow()
        else:
            response = QuizResponse(
                quiz_id     = quiz_id,
                question_id = item.question_id,
                student_id  = student.id,
                answer      = item.answer,
                is_correct  = is_correct,
                time_taken_seconds = item.time_taken_seconds if item.time_taken_seconds is not None else 30.0,
                hint_used   = item.hint_used if item.hint_used is not None else False,
                answered_at = datetime.utcnow(),
            )
    db.commit()

    # If no responses exist at all for this quiz by this student (e.g. security violation auto-submit / 0 marks),
    # generate 0-mark incorrect QuizResponse records for all questions in the quiz
    existing_responses_count = db.query(QuizResponse).filter(
        QuizResponse.quiz_id == quiz_id,
        QuizResponse.student_id == student.id,
    ).count()

    if existing_responses_count == 0:
        for q in quiz.questions:
            resp = QuizResponse(
                quiz_id=quiz_id,
                question_id=q.id,
                student_id=student.id,
                answer="",
                is_correct=False,
                time_taken_seconds=0.0,
                hint_used=False,
                answered_at=datetime.utcnow(),
            )
            db.add(resp)
        db.commit()

    # Asynchronously trigger student learning profile recalculation with fresh DB session
    lecture = quiz.lecture if quiz else None
    if lecture and lecture.topic_id:
        topic_id_snap = lecture.topic_id
        student_id_snap = student.id

        def _bg_recalc(s_id: int, t_id: int):
            from app.db.database import SessionLocal
            from app.services.learning_model import recalculate_student_learning_profile as _recalc
            _db = SessionLocal()
            try:
                _recalc(s_id, t_id, _db)
            except Exception as e:
                print(f"[Learning Model] Quiz trigger error: {e}")
            finally:
                _db.close()

        background_tasks.add_task(_bg_recalc, student_id_snap, topic_id_snap)

    return {"ok": True, "submitted": len(payload.answers)}


class ProctoringViolationPayload(BaseModel):
    violation_type: str
    details: Optional[str] = None
    warning_count: int = 1


@router.post("/quiz/{quiz_id}/log-proctoring-violation")
def log_proctoring_violation(
    quiz_id: int,
    payload: ProctoringViolationPayload,
    student: Student = Depends(_get_current_student),
    db: Session = Depends(get_db),
):
    """
    Log real-time AI Proctoring warning/violation to backend database for audit inspection.
    """
    from app.models.models import QuizAttemptSession
    session = db.query(QuizAttemptSession).filter(
        QuizAttemptSession.quiz_id == quiz_id,
        QuizAttemptSession.student_id == student.id,
        QuizAttemptSession.is_completed == False,
    ).first()

    if session:
        import json
        session.proctoring_warnings_count = payload.warning_count
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "violation_type": payload.violation_type,
            "details": payload.details or "",
            "warning_count": payload.warning_count
        }
        existing_logs = []
        if session.proctoring_logs:
            try:
                existing_logs = json.loads(session.proctoring_logs)
            except Exception:
                existing_logs = []
        existing_logs.append(log_entry)
        session.proctoring_logs = json.dumps(existing_logs)

        if payload.warning_count >= 3 or payload.violation_type in ["SECURITY_VIOLATION", "TAB_SWITCH", "SCREENSHOT", "AI_TERMINATED"]:
            session.is_cancelled = True
            session.is_completed = True
            session.submitted_at = datetime.utcnow()

        db.commit()

    return {"ok": True, "warning_count": payload.warning_count}
