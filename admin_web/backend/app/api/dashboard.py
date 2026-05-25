"""
Student-facing Dashboard API — real data from database.
GET /api/dashboard        → stats computed from real enrollments, sessions, attendance
GET /api/dashboard/today-lectures  → lectures scheduled today from enrolled sections
GET /api/dashboard/active-quizzes  → post/mid quizzes not yet attempted
"""
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordBearer

from app.db.database import get_db
from app.models.models import (
    User, Student, Enrollment, Section, Lecture,
    LectureSession, Attendance, Quiz, QuizResponse
)
from app.services.auth_service import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


# ── Auth dependency ────────────────────────────────────────────────────────────
def _get_current_student(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Student:
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload.")
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive.")
    student = db.query(Student).filter(Student.user_id == user.id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student profile not found.")
    return student


# ── GET /api/dashboard ────────────────────────────────────────────────────────
@router.get("")
def get_dashboard_stats(
    student: Student = Depends(_get_current_student),
    db: Session = Depends(get_db),
):
    """Real stats computed from DB: enrollments, sessions, attendance."""

    # 1. Enrolled courses count (active)
    enrollments = db.query(Enrollment).filter(
        Enrollment.student_id == student.id,
        Enrollment.is_active == True,
    ).all()
    courses_count = len(enrollments)

    # 2. Attendance percentage — present / total lectures in enrolled sections
    section_ids = [e.section_id for e in enrollments]
    if section_ids:
        total_lectures = db.query(Lecture).filter(
            Lecture.section_id.in_(section_ids),
            Lecture.is_published == True,
        ).count()

        present_count = db.query(Attendance).filter(
            Attendance.student_id == student.id,
            Attendance.is_present == True,
        ).count()

        attendance_pct = (
            (present_count / total_lectures) * 100.0
            if total_lectures > 0 else 0.0
        )
    else:
        total_lectures = 0
        attendance_pct = 0.0

    # 3. Overall progress — average watch_percentage across all sessions
    sessions = db.query(LectureSession).filter(
        LectureSession.student_id == student.id,
    ).all()
    overall_progress = (
        sum(s.watch_percentage for s in sessions) / len(sessions)
        if sessions else 0.0
    )

    # 4. Active quizzes count — post/mid quizzes with no response yet
    if section_ids:
        lecture_ids = [
            l.id for l in db.query(Lecture).filter(
                Lecture.section_id.in_(section_ids),
                Lecture.is_published == True,
            ).all()
        ]
        attempted_quiz_ids = {
            r.quiz_id for r in db.query(QuizResponse).filter(
                QuizResponse.student_id == student.id,
            ).all()
        }
        active_quizzes_count = db.query(Quiz).filter(
            Quiz.lecture_id.in_(lecture_ids),
            Quiz.quiz_type.in_(["post", "mid"]),
            Quiz.id.notin_(attempted_quiz_ids),
        ).count()
    else:
        active_quizzes_count = 0

    return {
        "overall_progress":      round(overall_progress, 1),
        "total_courses":         courses_count,
        "attendance_percentage": round(attendance_pct, 1),
        "active_quizzes_count":  active_quizzes_count,
    }


# ── GET /api/dashboard/today-lectures ────────────────────────────────────────
@router.get("/today-lectures")
def get_today_lectures(
    student: Student = Depends(_get_current_student),
    db: Session = Depends(get_db),
):
    """
    Returns published lectures from the student's enrolled sections.
    'Today' = lectures published on/before today, ordered by publish_date.
    """
    enrollments = db.query(Enrollment).filter(
        Enrollment.student_id == student.id,
        Enrollment.is_active == True,
    ).all()
    section_ids = [e.section_id for e in enrollments]
    if not section_ids:
        return []

    today = date.today()
    lectures = db.query(Lecture).filter(
        Lecture.section_id.in_(section_ids),
        Lecture.is_published == True,
        Lecture.publish_date != None,
    ).order_by(Lecture.publish_date.desc()).limit(10).all()

    # Check which ones were already completed (>= 80% watched)
    attended_lecture_ids = {
        a.lecture_id for a in db.query(Attendance).filter(
            Attendance.student_id == student.id,
            Attendance.is_present == True,
        ).all()
    }

    result = []
    for lec in lectures:
        section = lec.section
        course = section.course if section else None
        result.append({
            "lecture_id":     lec.id,
            "title":          lec.title,
            "course_name":    course.name if course else "Unknown Course",
            "scheduled_time": lec.publish_date.isoformat() if lec.publish_date else datetime.utcnow().isoformat(),
            "is_completed":   lec.id in attended_lecture_ids,
        })

    return result


# ── GET /api/dashboard/active-quizzes ────────────────────────────────────────
@router.get("/active-quizzes")
def get_active_quizzes(
    student: Student = Depends(_get_current_student),
    db: Session = Depends(get_db),
):
    """
    Returns post/mid quizzes the student hasn't attempted yet.
    """
    enrollments = db.query(Enrollment).filter(
        Enrollment.student_id == student.id,
        Enrollment.is_active == True,
    ).all()
    section_ids = [e.section_id for e in enrollments]
    if not section_ids:
        return []

    lecture_ids = [
        l.id for l in db.query(Lecture).filter(
            Lecture.section_id.in_(section_ids),
            Lecture.is_published == True,
        ).all()
    ]
    if not lecture_ids:
        return []

    # Quiz IDs already attempted by this student
    attempted_quiz_ids = {
        r.quiz_id for r in db.query(QuizResponse).filter(
            QuizResponse.student_id == student.id,
        ).all()
    }

    quizzes = db.query(Quiz).filter(
        Quiz.lecture_id.in_(lecture_ids),
        Quiz.quiz_type.in_(["post", "mid"]),
        Quiz.id.notin_(attempted_quiz_ids),
    ).all()

    result = []
    for q in quizzes:
        result.append({
            "quiz_id":       q.id,
            "quiz_type":     q.quiz_type,
            "lecture_title": q.lecture.title,
            "due_date":      None,         # Can add deadline field to Quiz model later
            "is_attempted":  False,
        })

    return result
