"""
Student-facing Courses API — GET /api/courses/
Returns the enrolled courses for the logged-in student.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.models import User, Student, Enrollment, Section, Course, Lecture, Attendance
from app.services.auth_service import decode_token
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

router = APIRouter(prefix="/courses", tags=["Courses (Student)"])


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


@router.get("")
@router.get("/my")
def get_student_courses(
    student: Student = Depends(_get_current_student),
    db: Session = Depends(get_db),
):
    """
    Returns all active enrolled courses with progress for the logged-in student.
    GET /api/courses/my
    """
    enrollments = db.query(Enrollment).filter(
        Enrollment.student_id == student.id,
        Enrollment.is_active == True,
    ).all()

    result = []
    for enrollment in enrollments:
        section = enrollment.section
        course = section.course if section else None
        teacher = section.teacher if section else None

        if not course:
            continue

        instructor_name = "TBA"
        if teacher and teacher.user:
            instructor_name = teacher.user.full_name

        # Calculate progress
        total_lectures = db.query(Lecture).filter(
            Lecture.section_id == section.id,
            Lecture.is_published == True
        ).count()
        
        completed_lectures = db.query(Attendance).filter(
            Attendance.student_id == student.id,
            Attendance.section_id == section.id,
            Attendance.is_present == True
        ).count()
        
        progress = (completed_lectures / total_lectures * 100) if total_lectures > 0 else 0.0

        result.append({
            "id": course.id,
            "name": course.name,
            "code": course.code,
            "instructor": instructor_name,
            "credit_hours": course.credit_hours,
            "progress": round(progress, 0),
            "section_id": section.id
        })

    return result
