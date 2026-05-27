"""
Student-facing Courses API — GET /api/courses/
Returns the enrolled courses for the logged-in student.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime, timezone

from app.db.database import get_db
from app.models.models import User, Student, Enrollment, Section, Course, Lecture, Attendance, Semester
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


def auto_finalize_registrations(db: Session):
    """
    Automatically transitions all PENDING registrations to ACTIVE for the active semester
    if the registration deadline has passed.
    """
    active_sem = db.query(Semester).filter(Semester.is_active == True).first()
    if active_sem and active_sem.registration_deadline:
        if datetime.utcnow() > active_sem.registration_deadline:
            # Find all pending enrollments in the active semester
            pending = db.query(Enrollment).join(Section).filter(
                Section.semester_id == active_sem.id,
                Enrollment.status == "PENDING"
            ).all()
            if pending:
                for e in pending:
                    e.status = "ACTIVE"
                db.commit()


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
    auto_finalize_registrations(db)

    enrollments = db.query(Enrollment).filter(
        Enrollment.student_id == student.id,
        Enrollment.is_active == True,
        Enrollment.status == "ACTIVE",
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


class RegistrationRequest(BaseModel):
    section_id: int


@router.get("/registration/offered")
def get_registration_offered_courses(
    student: Student = Depends(_get_current_student),
    db: Session = Depends(get_db),
):
    """
    Returns all sections offered for registration in the active semester,
    along with student enrollment status and registration deadline details.
    """
    from sqlalchemy import or_, and_
    active_semester = db.query(Semester).filter(Semester.is_active == True).first()
    if not active_semester:
        raise HTTPException(status_code=404, detail="No active academic semester found.")

    sections = db.query(Section).filter(
        Section.semester_id == active_semester.id,
        Section.is_registration_open == True,
        or_(
            Section.target_student_id == student.id,
            and_(
                Section.academic_section_id == student.academic_section_id,
                Section.target_student_id == None
            )
        )
    ).all()

    enrolled_section_ids = {
        e.section_id for e in db.query(Enrollment).filter(
            Enrollment.student_id == student.id,
            Enrollment.is_active == True
        ).all()
    }

    sections_list = []
    for sec in sections:
        course = sec.course
        if not course:
            continue

        teacher = sec.teacher
        instructor_name = "TBA"
        if teacher and teacher.user:
            instructor_name = teacher.user.full_name

        sections_list.append({
            "section_id": sec.id,
            "section_label": sec.section_label,
            "course_id": course.id,
            "course_name": course.name,
            "course_code": course.code,
            "credit_hours": course.credit_hours,
            "instructor": instructor_name,
            "schedule": sec.schedule,
            "room": sec.room,
            "is_registered": sec.id in enrolled_section_ids
        })

    return {
        "semester_name": active_semester.name,
        "registration_deadline": active_semester.registration_deadline.replace(tzinfo=timezone.utc).isoformat() if active_semester.registration_deadline else None,
        "server_time": datetime.utcnow().replace(tzinfo=timezone.utc).isoformat(),
        "sections": sections_list
    }


@router.post("/registration/register")
def register_course(
    payload: RegistrationRequest,
    student: Student = Depends(_get_current_student),
    db: Session = Depends(get_db),
):
    """
    Enrolls the student in the specified section if registration is open and deadline has not passed.
    """
    active_semester = db.query(Semester).filter(Semester.is_active == True).first()
    if not active_semester:
        raise HTTPException(status_code=404, detail="No active semester found.")

    if active_semester.registration_deadline and datetime.utcnow() > active_semester.registration_deadline:
        raise HTTPException(status_code=400, detail="Registration period has closed.")

    section = db.query(Section).filter(
        Section.id == payload.section_id,
        Section.semester_id == active_semester.id,
        Section.is_registration_open == True
    ).first()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found or not open for registration.")

    # Validate target student or academic section
    if section.target_student_id is not None:
        if section.target_student_id != student.id:
            raise HTTPException(status_code=403, detail="This section is not offered to you.")
    else:
        if section.academic_section_id != student.academic_section_id:
            raise HTTPException(status_code=403, detail="This section is not offered to your batch section.")

    # Check if student is already enrolled (active or inactive)
    existing = db.query(Enrollment).filter(
        Enrollment.student_id == student.id,
        Enrollment.section_id == section.id
    ).first()

    if existing:
        if existing.is_active:
            return {"message": "Already registered in this section."}
        else:
            existing.is_active = True
            existing.status = "PENDING"
            db.commit()
            return {"message": "Successfully registered."}

    # Create new enrollment record
    new_enrollment = Enrollment(
        student_id=student.id,
        section_id=section.id,
        is_active=True,
        status="PENDING"
    )
    db.add(new_enrollment)
    db.commit()
    return {"message": "Successfully registered."}


@router.post("/registration/withdraw")
def withdraw_course(
    payload: RegistrationRequest,
    student: Student = Depends(_get_current_student),
    db: Session = Depends(get_db),
):
    """
    Withdraws/deletes the student's enrollment from the specified section,
    permitted only before the active semester's registration deadline.
    """
    active_semester = db.query(Semester).filter(Semester.is_active == True).first()
    if not active_semester:
        raise HTTPException(status_code=404, detail="No active semester found.")

    if active_semester.registration_deadline and datetime.utcnow() > active_semester.registration_deadline:
        raise HTTPException(status_code=400, detail="Registration deadline has passed. You cannot withdraw from this course.")

    enrollment = db.query(Enrollment).filter(
        Enrollment.student_id == student.id,
        Enrollment.section_id == payload.section_id,
        Enrollment.is_active == True
    ).first()

    if not enrollment:
        raise HTTPException(status_code=404, detail="Active enrollment for this course not found.")

    # Completely remove/delete the enrollment record so they can register again
    db.delete(enrollment)
    db.commit()
    return {"message": "Successfully withdrawn from course."}

