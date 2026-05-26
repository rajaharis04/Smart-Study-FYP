"""Semesters, Courses, Sections, Enrollments, and Reports API routers."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.database import get_db
from datetime import datetime
from app.models.models import (
    Semester, Course, Section, Enrollment, Student,
    Teacher, Department, User, AuditLog, GlobalAnnouncement,
    Attendance, QuizResponse, Quiz, Lecture, Notification
)
from app.schemas.schemas import (
    SemesterCreate, SemesterUpdate, SemesterOut,
    CourseCreate, CourseUpdate, CourseOut,
    SectionCreate, SectionUpdate, SectionOut,
    EnrollmentCreate, EnrollmentOut, BulkEnrollResult,
    AdminStats,
    GlobalAnnouncementCreate, GlobalAnnouncementOut,
)
from app.services.csv_service import parse_enrollment_csv
from app.core.deps import get_current_admin, log_action


# ─── SEMESTERS ────────────────────────────────────────────────────────────────
semesters_router = APIRouter(prefix="/semesters", tags=["Semesters"])


@semesters_router.get("/", response_model=List[SemesterOut])
def list_semesters(db: Session = Depends(get_db), _=Depends(get_current_admin)):
    return db.query(Semester).order_by(Semester.created_at.desc()).all()


@semesters_router.get("/active", response_model=SemesterOut)
def get_active_semester(db: Session = Depends(get_db), _=Depends(get_current_admin)):
    active_sem = db.query(Semester).filter(Semester.is_active == True).first()
    if not active_sem:
        raise HTTPException(status_code=404, detail="No active semester session found.")
    return active_sem


@semesters_router.post("/", response_model=SemesterOut, status_code=201)
def create_semester(payload: SemesterCreate, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    semester = Semester(**payload.model_dump())
    db.add(semester)
    db.commit()
    db.refresh(semester)
    log_action(db, admin.email, "CREATE_SEMESTER", f"Created semester '{semester.name}' (ID: {semester.id}).")
    return semester


@semesters_router.put("/{sem_id}", response_model=SemesterOut)
def update_semester(sem_id: int, payload: SemesterUpdate, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    sem = db.query(Semester).filter(Semester.id == sem_id).first()
    if not sem:
        raise HTTPException(status_code=404, detail="Semester not found.")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(sem, field, value)
    db.commit()
    db.refresh(sem)
    log_action(db, admin.email, "UPDATE_SEMESTER", f"Updated semester '{sem.name}' (ID: {sem.id}).")
    return sem


@semesters_router.delete("/{sem_id}")
def delete_semester(sem_id: int, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    sem = db.query(Semester).filter(Semester.id == sem_id).first()
    if not sem:
        raise HTTPException(status_code=404, detail="Semester not found.")
    sem_name = sem.name
    db.delete(sem)
    db.commit()
    log_action(db, admin.email, "DELETE_SEMESTER", f"Deleted semester '{sem_name}' (ID: {sem_id}).")
    return {"message": "Semester deleted."}


@semesters_router.post("/{sem_id}/rollover")
def rollover_semester(sem_id: int, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    sem = db.query(Semester).filter(Semester.id == sem_id).first()
    if not sem:
        raise HTTPException(status_code=404, detail="Semester not found.")
    if not sem.is_active:
        raise HTTPException(status_code=400, detail="Semester is already inactive.")
    
    # 1. Archive all courses linked to this semester
    courses = db.query(Course).filter(Course.semester_id == sem_id).all()
    for course in courses:
        course.is_archived = True

    # 2. Deactivate enrollments in sections linked to this semester
    sections = db.query(Section).filter(Section.semester_id == sem_id).all()
    section_ids = [s.id for s in sections]
    
    enrollments_deactivated = 0
    if section_ids:
        enrollments = db.query(Enrollment).filter(
            Enrollment.section_id.in_(section_ids),
            Enrollment.is_active == True
        ).all()
        for e in enrollments:
            e.is_active = False
            enrollments_deactivated += 1
            
    # 3. Mark semester inactive
    sem.is_active = False
    db.commit()
    
    log_action(
        db, 
        admin.email, 
        "SEMESTER_ROLLOVER", 
        f"Rolled over semester '{sem.name}' (ID: {sem_id}). Archived {len(courses)} courses, deactivated {enrollments_deactivated} enrollments across {len(sections)} sections."
    )
    return {
        "message": "Semester rolled over successfully.",
        "courses_archived": len(courses),
        "enrollments_deactivated": enrollments_deactivated
    }


# ─── COURSES ──────────────────────────────────────────────────────────────────
courses_router = APIRouter(prefix="/courses", tags=["Courses"])


def _course_to_out(c: Course) -> dict:
    return {
        "id": c.id,
        "name": c.name,
        "code": c.code,
        "credit_hours": c.credit_hours,
        "department_name": c.department.name if c.department else None,
        "semester_name": c.semester.name if c.semester else None,
        "is_archived": c.is_archived,
        "sections_count": len(c.sections),
        "created_at": c.created_at,
    }


@courses_router.get("/", response_model=List[CourseOut])
def list_courses(db: Session = Depends(get_db), _=Depends(get_current_admin)):
    courses = db.query(Course).all()
    return [_course_to_out(c) for c in courses]


@courses_router.post("/", status_code=201, response_model=CourseOut)
def create_course(payload: CourseCreate, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    course = Course(**payload.model_dump())
    db.add(course)
    db.commit()
    db.refresh(course)
    log_action(db, admin.email, "CREATE_COURSE", f"Created course '{course.name}' (Code: {course.code}, ID: {course.id}).")
    return _course_to_out(course)


@courses_router.put("/{course_id}", response_model=CourseOut)
def update_course(course_id: int, payload: CourseUpdate, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found.")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(course, field, value)
    db.commit()
    db.refresh(course)
    log_action(db, admin.email, "UPDATE_COURSE", f"Updated course '{course.name}' (Code: {course.code}, ID: {course.id}).")
    return _course_to_out(course)


@courses_router.delete("/{course_id}")
def delete_course(course_id: int, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found.")
    course_name = course.name
    course_code = course.code
    db.delete(course)
    db.commit()
    log_action(db, admin.email, "DELETE_COURSE", f"Deleted course '{course_name}' (Code: {course_code}, ID: {course_id}).")
    return {"message": "Course deleted."}


# ─── SECTIONS ─────────────────────────────────────────────────────────────────
sections_router = APIRouter(prefix="/sections", tags=["Sections"])


def _section_to_out(s: Section) -> dict:
    return {
        "id": s.id,
        "section_label": s.section_label,
        "course_name": s.course.name if s.course else "",
        "course_code": s.course.code if s.course else "",
        "teacher_name": s.teacher.user.full_name if s.teacher else None,
        "semester_name": s.semester.name if s.semester else None,
        "schedule": s.schedule,
        "room": s.room,
        "enrolled_count": len([e for e in s.enrollments if e.is_active]),
        "semester_id": s.semester_id,
        "is_registration_open": s.is_registration_open,
        "created_at": s.created_at,
    }


@sections_router.get("/", response_model=List[SectionOut])
def list_sections(db: Session = Depends(get_db), _=Depends(get_current_admin)):
    sections = db.query(Section).all()
    return [_section_to_out(s) for s in sections]


@sections_router.post("/", status_code=201, response_model=SectionOut)
def create_section(payload: SectionCreate, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    # Validate course exists
    course = db.query(Course).filter(Course.id == payload.course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found.")

    section = Section(**payload.model_dump())
    db.add(section)
    db.commit()
    db.refresh(section)
    log_action(db, admin.email, "CREATE_SECTION", f"Created section '{section.section_label}' for course '{course.name}' (ID: {section.id}).")
    return _section_to_out(section)


@sections_router.put("/{section_id}", response_model=SectionOut)
def update_section(section_id: int, payload: SectionUpdate, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    section = db.query(Section).filter(Section.id == section_id).first()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found.")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(section, field, value)
    db.commit()
    db.refresh(section)
    course_name = section.course.name if section.course else "Unknown"
    log_action(db, admin.email, "UPDATE_SECTION", f"Updated section '{section.section_label}' of course '{course_name}' (ID: {section.id}).")
    return _section_to_out(section)


@sections_router.delete("/{section_id}")
def delete_section(section_id: int, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    section = db.query(Section).filter(Section.id == section_id).first()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found.")
    label = section.section_label
    course_name = section.course.name if section.course else "Unknown"
    db.delete(section)
    db.commit()
    log_action(db, admin.email, "DELETE_SECTION", f"Deleted section '{label}' of course '{course_name}' (ID: {section_id}).")
    return {"message": "Section deleted."}


# ─── ENROLLMENTS ──────────────────────────────────────────────────────────────
enrollments_router = APIRouter(prefix="/enrollments", tags=["Enrollments"])


def _enrollment_to_out(e: Enrollment) -> dict:
    return {
        "id": e.id,
        "student_name": e.student.user.full_name,
        "student_reg": e.student.reg_number,
        "section_label": e.section.section_label,
        "course_name": e.section.course.name if e.section.course else "",
        "is_active": e.is_active,
        "enrolled_at": e.enrolled_at,
    }


@enrollments_router.get("/", response_model=List[EnrollmentOut])
def list_enrollments(db: Session = Depends(get_db), _=Depends(get_current_admin)):
    enrollments = db.query(Enrollment).all()
    return [_enrollment_to_out(e) for e in enrollments]


@enrollments_router.post("/", status_code=201)
def enroll_students(
    payload: EnrollmentCreate,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    section = db.query(Section).filter(Section.id == payload.section_id).first()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found.")

    enrolled = 0
    skipped = 0
    errors = []

    for student_id in payload.student_ids:
        student = db.query(Student).filter(Student.id == student_id).first()
        if not student:
            errors.append(f"Student ID {student_id} not found.")
            continue
        # Check if already enrolled
        existing = db.query(Enrollment).filter(
            Enrollment.student_id == student_id,
            Enrollment.section_id == payload.section_id,
        ).first()
        if existing:
            if not existing.is_active:
                existing.is_active = True
                enrolled += 1
            else:
                skipped += 1
            continue

        enrollment = Enrollment(student_id=student_id, section_id=payload.section_id)
        db.add(enrollment)
        enrolled += 1

    db.commit()
    course_name = section.course.name if section.course else "Unknown"
    log_action(db, admin.email, "ENROLL_STUDENTS", f"Enrolled {enrolled} students into section '{section.section_label}' for course '{course_name}'.")
    return {"enrolled": enrolled, "skipped": skipped, "errors": errors}


@enrollments_router.post("/bulk-upload/{section_id}", response_model=BulkEnrollResult)
async def bulk_enroll_from_csv(
    section_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    section = db.query(Section).filter(Section.id == section_id).first()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found.")

    contents = await file.read()
    try:
        reg_numbers = parse_enrollment_csv(contents)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    enrolled = 0
    skipped = 0
    errors = []

    for reg in reg_numbers:
        student = db.query(Student).filter(Student.reg_number == reg).first()
        if not student:
            errors.append(f"Student with RegNumber '{reg}' not found.")
            continue
        existing = db.query(Enrollment).filter(
            Enrollment.student_id == student.id,
            Enrollment.section_id == section_id,
        ).first()
        if existing:
            skipped += 1
            continue
        db.add(Enrollment(student_id=student.id, section_id=section_id))
        enrolled += 1

    db.commit()
    course_name = section.course.name if section.course else "Unknown"
    log_action(db, admin.email, "BULK_ENROLL", f"Bulk enrolled {enrolled} students via CSV into section '{section.section_label}' for course '{course_name}'.")
    return BulkEnrollResult(enrolled=enrolled, skipped=skipped, errors=errors)
@enrollments_router.delete("/{enrollment_id}")
def deactivate_enrollment(enrollment_id: int, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    enrollment = db.query(Enrollment).filter(Enrollment.id == enrollment_id).first()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found.")
    enrollment.is_active = False
    student_name = enrollment.student.user.full_name
    reg = enrollment.student.reg_number
    sec_label = enrollment.section.section_label
    course_name = enrollment.section.course.name if enrollment.section.course else "Unknown"
    db.commit()
    log_action(db, admin.email, "DEACTIVATE_ENROLLMENT", f"Deactivated enrollment for student '{student_name}' ({reg}) in section '{sec_label}' of course '{course_name}'.")
    return {"message": "Enrollment deactivated (student dropped)."}


# ─── REPORTS ──────────────────────────────────────────────────────────────────
reports_router = APIRouter(prefix="/reports", tags=["Reports"])


@reports_router.get("/stats", response_model=AdminStats)
def get_admin_stats(db: Session = Depends(get_db), _=Depends(get_current_admin)):
    active_sem = db.query(Semester).filter(Semester.is_active == True).first()
    return AdminStats(
        total_departments=db.query(Department).count(),
        total_teachers=db.query(Teacher).count(),
        total_students=db.query(Student).count(),
        total_courses=db.query(Course).filter(Course.is_archived == False).count(),
        total_sections=db.query(Section).count(),
        total_enrollments=db.query(Enrollment).filter(Enrollment.is_active == True).count(),
        active_semester=active_sem.name if active_sem else None,
    )


@reports_router.get("/students-per-section")
def students_per_section(db: Session = Depends(get_db), _=Depends(get_current_admin)):
    sections = db.query(Section).all()
    return [
        {
            "section": f"{s.course.code if s.course else '?'} - {s.section_label}",
            "teacher": s.teacher.user.full_name if s.teacher else "Unassigned",
            "enrolled": len([e for e in s.enrollments if e.is_active]),
        }
        for s in sections
    ]


@reports_router.get("/teachers-summary")
def teachers_summary(db: Session = Depends(get_db), _=Depends(get_current_admin)):
    teachers = db.query(Teacher).all()
    return [
        {
            "id": t.id,
            "name": t.user.full_name,
            "employee_id": t.employee_id,
            "department": t.department.name if t.department else "N/A",
            "sections_count": len(t.sections),
            "is_active": t.user.is_active,
        }
        for t in teachers
    ]


@reports_router.get("/at-risk-summary")
def get_at_risk_summary(db: Session = Depends(get_db), _=Depends(get_current_admin)):
    students = db.query(Student).all()
    at_risk_students = []

    for student in students:
        enrollments = db.query(Enrollment).filter(Enrollment.student_id == student.id, Enrollment.is_active == True).all()
        if not enrollments:
            continue
        
        # Global Attendance
        total_att = db.query(Attendance).filter(Attendance.student_id == student.id).count()
        present_att = db.query(Attendance).filter(Attendance.student_id == student.id, Attendance.is_present == True).count()
        attendance_rate = (present_att / total_att * 100) if total_att > 0 else 100.0

        # Global Quizzes
        total_quiz = db.query(QuizResponse).filter(QuizResponse.student_id == student.id, QuizResponse.is_correct.is_not(None)).count()
        correct_quiz = db.query(QuizResponse).filter(QuizResponse.student_id == student.id, QuizResponse.is_correct == True).count()
        quiz_grade = (correct_quiz / total_quiz * 100) if total_quiz > 0 else 100.0

        if attendance_rate < 75.0 or quiz_grade < 50.0:
            weakest_courses = []
            for enroll in enrollments:
                sec = enroll.section
                if not sec or not sec.course:
                    continue
                
                sec_total_att = db.query(Attendance).filter(
                    Attendance.student_id == student.id,
                    Attendance.section_id == sec.id
                ).count()
                sec_present_att = db.query(Attendance).filter(
                    Attendance.student_id == student.id,
                    Attendance.section_id == sec.id,
                    Attendance.is_present == True
                ).count()
                sec_att_rate = (sec_present_att / sec_total_att * 100) if sec_total_att > 0 else 100.0

                lectures = db.query(Lecture).filter(Lecture.section_id == sec.id).all()
                lecture_ids = [l.id for l in lectures]
                
                sec_quiz_rate = 100.0
                if lecture_ids:
                    sec_total_quiz = db.query(QuizResponse).filter(
                        QuizResponse.student_id == student.id,
                        QuizResponse.quiz_id.in_(
                            db.query(Quiz.id).filter(Quiz.lecture_id.in_(lecture_ids)).subquery()
                        ),
                        QuizResponse.is_correct.is_not(None)
                    ).count()
                    sec_correct_quiz = db.query(QuizResponse).filter(
                        QuizResponse.student_id == student.id,
                        QuizResponse.quiz_id.in_(
                            db.query(Quiz.id).filter(Quiz.lecture_id.in_(lecture_ids)).subquery()
                        ),
                        QuizResponse.is_correct == True
                    ).count()
                    sec_quiz_rate = (sec_correct_quiz / sec_total_quiz * 100) if sec_total_quiz > 0 else 100.0
                
                if sec_att_rate < 75.0 or sec_quiz_rate < 50.0:
                    weakest_courses.append({
                        "course_code": sec.course.code,
                        "course_name": sec.course.name,
                        "attendance_rate": round(sec_att_rate, 1),
                        "quiz_grade": round(sec_quiz_rate, 1)
                    })
            
            at_risk_students.append({
                "id": student.id,
                "name": student.user.full_name,
                "reg_number": student.reg_number,
                "department": student.department.name if student.department else "N/A",
                "attendance_rate": round(attendance_rate, 1),
                "quiz_grade": round(quiz_grade, 1),
                "weakest_courses": weakest_courses
            })
    
    return at_risk_students


@reports_router.get("/departmental-kpis")
def get_departmental_kpis(db: Session = Depends(get_db), _=Depends(get_current_admin)):
    departments = db.query(Department).all()
    kpis = []

    for dept in departments:
        student_count = db.query(Student).filter(Student.department_id == dept.id).count()
        teacher_count = db.query(Teacher).filter(Teacher.department_id == dept.id).count()

        student_ids = [s.id for s in db.query(Student.id).filter(Student.department_id == dept.id).all()]
        
        avg_attendance = 100.0
        avg_quiz = 100.0

        if student_ids:
            total_att = db.query(Attendance).filter(Attendance.student_id.in_(student_ids)).count()
            present_att = db.query(Attendance).filter(
                Attendance.student_id.in_(student_ids),
                Attendance.is_present == True
            ).count()
            avg_attendance = (present_att / total_att * 100) if total_att > 0 else 100.0

            total_quiz = db.query(QuizResponse).filter(
                QuizResponse.student_id.in_(student_ids),
                QuizResponse.is_correct.is_not(None)
            ).count()
            correct_quiz = db.query(QuizResponse).filter(
                QuizResponse.student_id.in_(student_ids),
                QuizResponse.is_correct == True
            ).count()
            avg_quiz = (correct_quiz / total_quiz * 100) if total_quiz > 0 else 100.0

        kpis.append({
            "department_id": dept.id,
            "name": dept.name,
            "code": dept.code,
            "hod_name": dept.hod_name,
            "total_students": student_count,
            "total_teachers": teacher_count,
            "average_attendance": round(avg_attendance, 1),
            "average_quiz_success": round(avg_quiz, 1)
        })
    
    return kpis


@reports_router.get("/audit-logs")
def get_audit_logs(db: Session = Depends(get_db), _=Depends(get_current_admin)):
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(100).all()
    return [
        {
            "id": log.id,
            "user_name": log.user_name,
            "action": log.action,
            "details": log.details,
            "timestamp": log.timestamp
        }
        for log in logs
    ]


# ─── GLOBAL ANNOUNCEMENTS ─────────────────────────────────────────────────────
announcements_router = APIRouter(prefix="/announcements", tags=["Global Announcements"])


@announcements_router.get("/", response_model=List[GlobalAnnouncementOut])
def list_announcements(db: Session = Depends(get_db), _=Depends(get_current_admin)):
    anns = db.query(GlobalAnnouncement).order_by(GlobalAnnouncement.created_at.desc()).all()
    result = []
    for a in anns:
        result.append({
            "id": a.id,
            "title": a.title,
            "content": a.content,
            "target_role": a.target_role,
            "department_id": a.department_id,
            "department_name": a.department.name if a.department else None,
            "created_at": a.created_at
        })
    return result


@announcements_router.post("/", response_model=GlobalAnnouncementOut, status_code=201)
def create_announcement(
    payload: GlobalAnnouncementCreate,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    ann = GlobalAnnouncement(**payload.model_dump())
    db.add(ann)
    db.commit()
    db.refresh(ann)
    
    # Propagate global announcements to individual users in the Notification table
    target_role = ann.target_role
    dept_id = ann.department_id
    users_to_notify = []

    if target_role == "teachers":
        t_query = db.query(User).join(Teacher, Teacher.user_id == User.id).filter(User.is_active == True)
        if dept_id:
            t_query = t_query.filter(Teacher.department_id == dept_id)
        users_to_notify = t_query.all()
    elif target_role == "students":
        s_query = db.query(User).join(Student, Student.user_id == User.id).filter(User.is_active == True)
        if dept_id:
            s_query = s_query.filter(Student.department_id == dept_id)
        users_to_notify = s_query.all()
    elif target_role == "all":
        t_query = db.query(User).join(Teacher, Teacher.user_id == User.id).filter(User.is_active == True)
        if dept_id:
            t_query = t_query.filter(Teacher.department_id == dept_id)
        
        s_query = db.query(User).join(Student, Student.user_id == User.id).filter(User.is_active == True)
        if dept_id:
            s_query = s_query.filter(Student.department_id == dept_id)
        
        users_to_notify = t_query.all() + s_query.all()

    for u in users_to_notify:
        notif = Notification(
            user_id=u.id,
            title=f"📢 {ann.title}",
            message=ann.content,
            created_at=ann.created_at
        )
        db.add(notif)
    db.commit()
    
    log_action(db, admin.email, "CREATE_GLOBAL_ANNOUNCEMENT", f"Created global announcement '{ann.title}' targeting '{ann.target_role}'.")
    
    return {
        "id": ann.id,
        "title": ann.title,
        "content": ann.content,
        "target_role": ann.target_role,
        "department_id": ann.department_id,
        "department_name": ann.department.name if ann.department else None,
        "created_at": ann.created_at
    }


@announcements_router.delete("/{ann_id}")
def delete_announcement(ann_id: int, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    ann = db.query(GlobalAnnouncement).filter(GlobalAnnouncement.id == ann_id).first()
    if not ann:
        raise HTTPException(status_code=404, detail="Global announcement not found.")
    title = ann.title
    db.delete(ann)
    db.commit()
    
    log_action(db, admin.email, "DELETE_GLOBAL_ANNOUNCEMENT", f"Deleted global announcement '{title}' (ID: {ann_id}).")
    
    return {"message": "Announcement deleted."}
