"""
Student Portal API Routers — Attendance, Profile Progress, and Question Bank.
"""
import os
from datetime import datetime, date, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.database import get_db
from app.models.models import (
    User, Student, Enrollment, Section, Course, Lecture,
    LectureSession, Attendance, Quiz, QuizQuestion, QuizResponse, Topic,
    Notification
)
from app.services.auth_service import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# Auth dependency
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


# ─── ATTENDANCE ROUTER ────────────────────────────────────────────────────────
attendance_router = APIRouter(prefix="/attendance", tags=["Attendance (Student)"])

@attendance_router.get("/my")
def get_my_attendance(
    student: Student = Depends(_get_current_student),
    db: Session = Depends(get_db)
):
    # Find all student enrollments
    enrollments = db.query(Enrollment).filter(
        Enrollment.student_id == student.id,
        Enrollment.is_active == True
    ).all()
    
    courses_list = []
    section_ids = []
    for e in enrollments:
        sec = e.section
        if sec and sec.course:
            section_ids.append(sec.id)
            teacher = sec.teacher
            instructor_name = "TBA"
            if teacher and teacher.user:
                instructor_name = teacher.user.full_name
            courses_list.append({
                "id": sec.course.id,
                "name": sec.course.name,
                "code": sec.course.code,
                "instructor": instructor_name,
                "credit_hours": sec.course.credit_hours,
                "section_id": sec.id
            })
            
    # Find all published lectures for these sections
    lectures = db.query(Lecture).filter(
        Lecture.section_id.in_(section_ids) if section_ids else False,
        Lecture.is_published == True
    ).order_by(Lecture.publish_date.asc()).all()
    
    attendance_list = []
    present_count = 0
    absent_count = 0
    partial_count = 0
    
    for l in lectures:
        # Find best watch percentage from sessions
        best_session = db.query(func.max(LectureSession.watch_percentage)).filter(
            LectureSession.student_id == student.id,
            LectureSession.lecture_id == l.id
        ).scalar() or 0.0
        
        status = "✗"
        if best_session >= 80.0:
            status = "✓"
            present_count += 1
        elif best_session >= 50.0:
            status = "P"
            partial_count += 1
        else:
            status = "✗"
            absent_count += 1
            
        sec = l.section
        course_code = sec.course.code if sec and sec.course else "N/A"
        course_id = sec.course.id if sec and sec.course else 0
        
        attendance_list.append({
            "date": l.publish_date.date().isoformat() if l.publish_date else date.today().isoformat(),
            "lecture_name": l.title,
            "course_id": course_id,
            "course_code": course_code,
            "watch_percentage": round(best_session, 1),
            "status": status
        })
        
    total_lectures = len(lectures)
    overall_attendance = 100.0
    if total_lectures > 0:
        overall_attendance = round((present_count / total_lectures) * 100, 1)
        
    return {
        "courses": courses_list,
        "attendance_list": attendance_list,
        "overall_attendance": overall_attendance,
        "present_count": present_count,
        "absent_count": absent_count,
        "partial_count": partial_count
    }


# ─── PROFILE PROGRESS ROUTER ──────────────────────────────────────────────────
profile_router = APIRouter(prefix="/profile", tags=["Profile/Progress (Student)"])

@profile_router.get("/progress")
def get_my_progress(
    student: Student = Depends(_get_current_student),
    db: Session = Depends(get_db)
):
    # Find all enrolled courses
    enrollments = db.query(Enrollment).filter(
        Enrollment.student_id == student.id,
        Enrollment.is_active == True
    ).all()
    
    course_progress = []
    weak_topics_recommendations = []
    
    for e in enrollments:
        sec = e.section
        if not sec or not sec.course:
            continue
        course = sec.course
        
        # Get all topics for this course
        topics = db.query(Topic).filter(Topic.course_id == course.id).order_by(Topic.sequence_number).all()
        topics_data = []
        
        for topic in topics:
            from app.models.models import StudentLearningProfile
            from app.services.learning_model import recalculate_student_learning_profile

            # Try to fetch learning profile from PostgreSQL
            profile = db.query(StudentLearningProfile).filter(
                StudentLearningProfile.student_id == student.id,
                StudentLearningProfile.topic_id == topic.id
            ).first()

            # If not calculated yet, run calculation synchronously to build baseline profile
            if not profile:
                profile = recalculate_student_learning_profile(student.id, topic.id, db)

            mastery = profile.mastery_score if profile else 0.0
            
            # Determine label
            if mastery >= 75.0:
                label = "Strong"
                symbol = "✓"
            elif mastery >= 60.0:
                label = "Working"
                symbol = "→"
            elif mastery >= 50.0:
                label = "Weak"
                symbol = "⚠️"
                weak_topics_recommendations.append({
                    "course_code": course.code,
                    "topic_title": topic.title,
                    "mastery": mastery,
                    "recommendation": f"Focus on core concepts of {topic.title}. Review lecture materials & practice quizzes again."
                })
            else:
                label = "Very Weak"
                symbol = "⚠️⚠️"
                weak_topics_recommendations.append({
                    "course_code": course.code,
                    "topic_title": topic.title,
                    "mastery": mastery,
                    "recommendation": f"Critical gap in {topic.title}. Seek teacher guidance and solve standard textbook problems."
                })
                
            topics_data.append({
                "topic_id": topic.id,
                "title": topic.title,
                "mastery": mastery,
                "confidence": profile.confidence_score if profile else 0.0,
                "learning_pace": profile.learning_pace if profile else 30.0,
                "engagement": profile.engagement_score if profile else 0.0,
                "hint_dependency": profile.hint_dependency if profile else 0.0,
                "learning_score": profile.learning_score if profile else 0.0,
                "status_label": label,
                "status_symbol": symbol
            })
            
        course_progress.append({
            "course_id": course.id,
            "course_code": course.code,
            "course_name": course.name,
            "topics": topics_data
        })

    # Generate personalized learning insights
    insights_list = []
    for e in enrollments:
        sec = e.section
        if not sec or not sec.course:
            continue
        course = sec.course
        topics = db.query(Topic).filter(Topic.course_id == course.id).all()
        for topic in topics:
            profile = db.query(StudentLearningProfile).filter(
                StudentLearningProfile.student_id == student.id,
                StudentLearningProfile.topic_id == topic.id
            ).first()
            if not profile:
                continue
                
            # Rule 1: High Hint Dependency (> 40%)
            if profile.hint_dependency > 0.4:
                insights_list.append({
                    "title_en": "Hint Dependency",
                    "title_ur": "اشارے پر انحصار",
                    "message_en": f"You are relying frequently on hints for '{topic.title}'. Try solving the next practice quiz independently to reinforce your self-confidence.",
                    "message_ur": f"آپ '{topic.title}' کے لیے اشاروں (hints) پر زیادہ انحصار کر رہے ہیں۔ خود اعتمادی بڑھانے کے لیے اگلا کوئز بغیر کسی مدد کے حل کرنے کی کوشش کریں۔",
                    "type": "hint",
                    "course_code": course.code
                })
                
            # Rule 2: Slow Learning Pace (> 50s per question)
            if profile.learning_pace > 50.0:
                insights_list.append({
                    "title_en": "Speed & Pace",
                    "title_ur": "رفتار اور وقت",
                    "message_en": f"You are taking more time per question in '{topic.title}'. We recommend reviewing foundational concepts to solve quizzes faster.",
                    "message_ur": f"آپ '{topic.title}' کے کوئزز میں ایک سوال پر زیادہ وقت لگا رہے ہیں۔ رفتار بہتر بنانے کے لیے بنیادی تصورات کا دوبارہ جائزہ لیں۔",
                    "type": "pace",
                    "course_code": course.code
                })
                
            # Rule 3: Low Lecture Engagement (< 50%)
            if profile.engagement_score > 0.0 and profile.engagement_score < 50.0:
                insights_list.append({
                    "title_en": "Lecture Focus",
                    "title_ur": "توجہ اور دلچسپی",
                    "message_en": f"Your lecture engagement in '{topic.title}' is low. Try to avoid pausing frequently and focus on active watch time.",
                    "message_ur": f"لیکچر '{topic.title}' کے ساتھ آپ کی دلچسپی کم ہے۔ بہتر نتائج کے لیے ویڈیو کے دوران بار بار روکنے سے گریز کریں۔",
                    "type": "engagement",
                    "course_code": course.code
                })
                
            # Rule 4: Low Confidence/Consistency with High Mastery
            if profile.confidence_score > 0.0 and profile.confidence_score < 50.0 and profile.mastery_score >= 60.0:
                insights_list.append({
                    "title_en": "Consistency Alert",
                    "title_ur": "مستقل مزاجی",
                    "message_en": f"Your performance in '{topic.title}' is fluctuating. Try to study the notes consistently to stabilize your scores.",
                    "message_ur": f"'{topic.title}' میں آپ کی کارکردگی غیر مستقل ہے۔ اپنے اسکورز کو مستحکم کرنے کے لیے نوٹس کا باقاعدگی سے مطالعہ کریں۔",
                    "type": "consistency",
                    "course_code": course.code
                })

    # Default fallback insight if list is empty
    if not insights_list:
        insights_list.append({
            "title_en": "Great Job!",
            "title_ur": "بہت اچھے!",
            "message_en": "Your overall learning pace, engagement, and quiz confidence are well balanced. Keep maintaining this consistent effort!",
            "message_ur": "آپ کے سیکھنے کی رفتار، دلچسپی، اور کوئزز کا اعتماد بالکل متوازن ہے۔ اپنی اس مستقل مزاجی کو برقرار رکھیں!",
            "type": "general",
            "course_code": "ALL"
        })
        
    return {
        "course_progress": course_progress,
        "recommendations": weak_topics_recommendations,
        "insights": insights_list
    }


# ─── PROFILE NOTIFICATIONS ────────────────────────────────────────────────────

@profile_router.get("/notifications")
def get_student_notifications(
    student: Student = Depends(_get_current_student),
    db: Session = Depends(get_db)
):
    notifications = db.query(Notification).filter(
        Notification.user_id == student.user_id
    ).order_by(Notification.created_at.desc()).all()
    
    return [
        {
            "id": str(n.id),
            "title": n.title,
            "content": n.message,
            "timestamp": n.created_at.isoformat() if n.created_at else datetime.utcnow().isoformat(),
            "read": n.is_read
        }
        for n in notifications
    ]


@profile_router.post("/notifications/{notification_id}/read")
def mark_student_notification_as_read(
    notification_id: int,
    student: Student = Depends(_get_current_student),
    db: Session = Depends(get_db)
):
    n = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == student.user_id
    ).first()
    if not n:
        raise HTTPException(status_code=404, detail="Notification not found.")
    n.is_read = True
    db.commit()
    return {"message": "Notification marked as read."}


# ─── QUESTION BANK ROUTER ──────────────────────────────────────────────────────
questionbank_router = APIRouter(prefix="/questionbank", tags=["Question Bank (Student)"])

class AttemptPayload(BaseModel):
    question_id: int
    answer: str

@questionbank_router.get("/my")
def get_my_questionbank(
    student: Student = Depends(_get_current_student),
    db: Session = Depends(get_db)
):
    # Find all wrong responses
    wrong_responses = db.query(QuizResponse).filter(
        QuizResponse.student_id == student.id,
        QuizResponse.is_correct == False
    ).order_by(QuizResponse.answered_at.desc()).all()
    
    result = []
    for resp in wrong_responses:
        q = resp.question
        if not q:
            continue
        
        quiz = q.quiz
        lecture = quiz.lecture if quiz else None
        section = lecture.section if lecture else None
        course = section.course if section else None
        topic = lecture.topic if lecture else None
        
        result.append({
            "id": q.id,
            "question_text": q.question_text,
            "option_a": q.option_a,
            "option_b": q.option_b,
            "option_c": q.option_c,
            "option_d": q.option_d,
            "your_answer": resp.answer,
            "correct_answer": q.correct_answer,
            "topic_title": topic.title if topic else "General",
            "course_code": course.code if course else ""
        })
        
    return result

@questionbank_router.post("/attempt")
def attempt_question_again(
    payload: AttemptPayload,
    student: Student = Depends(_get_current_student),
    db: Session = Depends(get_db)
):
    question = db.query(QuizQuestion).filter(QuizQuestion.id == payload.question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found.")
        
    is_now_correct = payload.answer.upper() == question.correct_answer.upper()
    
    # Update response in DB
    resp = db.query(QuizResponse).filter(
        QuizResponse.question_id == payload.question_id,
        QuizResponse.student_id == student.id
    ).first()
    
    if resp:
        resp.answer = payload.answer
        resp.is_correct = is_now_correct
        resp.answered_at = datetime.utcnow()
    else:
        resp = QuizResponse(
            quiz_id=question.quiz_id,
            question_id=payload.question_id,
            student_id=student.id,
            answer=payload.answer,
            is_correct=is_now_correct,
            answered_at=datetime.utcnow()
        )
        db.add(resp)
        
    db.commit()
    
    return {
        "correct": is_now_correct,
        "correct_answer": question.correct_answer
    }


# ─── STUDENT ASSIGNMENTS ROUTER ───────────────────────────────────────────────
student_assignment_router = APIRouter(prefix="/student/assignments", tags=["Assignments (Student)"])

@student_assignment_router.get("")
def get_student_assignments(
    student: Student = Depends(_get_current_student),
    db: Session = Depends(get_db)
):
    from app.models.models import Assignment, AssignmentQuestion, AssignmentSubmission
    enrollments = db.query(Enrollment).filter(
        Enrollment.student_id == student.id,
        Enrollment.is_active == True
    ).all()
    section_ids = [e.section_id for e in enrollments]
    if not section_ids:
        return []

    assignments = db.query(Assignment).filter(
        Assignment.section_id.in_(section_ids),
        Assignment.is_published == True
    ).order_by(Assignment.created_at.desc()).all()

    submissions = {
        s.assignment_id: s for s in db.query(AssignmentSubmission).filter(
            AssignmentSubmission.student_id == student.id
        ).all()
    }

    result = []
    for a in assignments:
        sub = submissions.get(a.id)
        sec = a.section
        course = sec.course if sec else None

        questions_list = []
        for q in a.questions:
            questions_list.append({
                "id": q.id,
                "question_text": q.question_text,
                "question_type": q.question_type,
                "marks": q.marks or 5
            })

        is_graded = sub is not None and (sub.status or "").lower() in ["graded", "evaluated", "completed"]
        result.append({
            "id": a.id,
            "title": a.title,
            "course_name": course.name if course else "Course",
            "course_code": course.code if course else "CS",
            "description": a.description or "",
            "total_marks": a.total_marks or 100,
            "due_date": a.due_date.isoformat() if a.due_date else None,
            "type": a.assignment_type or "manual",
            "is_submitted": sub is not None,
            "score": sub.total_score if (is_graded and sub.total_score is not None) else None,
            "status": ("Graded" if is_graded else "Under Evaluation") if sub else "Pending",
            "questions": questions_list
        })

    return result


class SubmitAssignmentItem(BaseModel):
    question_id: int
    answer_text: Optional[str] = ""

class SubmitAssignmentPayload(BaseModel):
    answers: List[SubmitAssignmentItem]
    attached_file_url: Optional[str] = None
    attached_file_name: Optional[str] = None

@student_assignment_router.post("/upload-attachment")
async def upload_assignment_attachment(
    file: UploadFile = File(...),
    student: Student = Depends(_get_current_student)
):
    """Upload attached PDF or DOCX file for an assignment submission."""
    filename = file.filename or "file.pdf"
    ext = filename.split(".")[-1].lower()
    if ext not in ["pdf", "docx", "doc"]:
        raise HTTPException(status_code=400, detail="Only PDF and DOCX documents are allowed.")

    upload_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "uploads", "assignments")
    os.makedirs(upload_dir, exist_ok=True)

    import time
    clean_filename = f"assign_std_{student.id}_{int(time.time())}_{filename}"
    file_path = os.path.join(upload_dir, clean_filename)

    contents = await file.read()
    with open(file_path, "wb") as f:
        f.write(contents)

    file_url = f"/uploads/assignments/{clean_filename}"
    return {
        "ok": True,
        "file_url": file_url,
        "file_name": filename
    }

@student_assignment_router.post("/{assignment_id}/submit")
def submit_student_assignment(
    assignment_id: int,
    payload: SubmitAssignmentPayload,
    student: Student = Depends(_get_current_student),
    db: Session = Depends(get_db)
):
    from app.models.models import Assignment, AssignmentSubmission, AssignmentAnswer
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found.")

    sub = db.query(AssignmentSubmission).filter(
        AssignmentSubmission.assignment_id == assignment_id,
        AssignmentSubmission.student_id == student.id
    ).first()

    is_late = False
    if assignment.due_date and datetime.utcnow() > assignment.due_date:
        is_late = True

    sub_status = "late_submitted" if is_late else "submitted"

    if not sub:
        sub = AssignmentSubmission(
            assignment_id=assignment_id,
            student_id=student.id,
            submitted_at=datetime.utcnow(),
            status=sub_status,
            max_score=assignment.total_marks or 100,
            attached_file_url=payload.attached_file_url,
            attached_file_name=payload.attached_file_name
        )
        db.add(sub)
        db.flush()
    else:
        sub.submitted_at = datetime.utcnow()
        sub.status = sub_status
        if payload.attached_file_url:
            sub.attached_file_url = payload.attached_file_url
            sub.attached_file_name = payload.attached_file_name
        db.query(AssignmentAnswer).filter(AssignmentAnswer.submission_id == sub.id).delete()

    for item in payload.answers:
        answer_rec = AssignmentAnswer(
            submission_id=sub.id,
            question_id=item.question_id,
            answer_text=item.answer_text or "",
            answered_at=datetime.utcnow()
        )
        db.add(answer_rec)

    db.commit()
    return {"ok": True, "message": "Assignment submitted successfully.", "submission_id": sub.id}
student_portal_router = APIRouter(prefix="/student", tags=["Student Portal"])


@student_portal_router.get("/marks")
def get_student_marks(
    student: Student = Depends(_get_current_student),
    db: Session = Depends(get_db)
):
    from app.models.models import QuizResponse, Quiz, AssignmentSubmission, Assignment

    quiz_attempts = db.query(QuizResponse.student_id, QuizResponse.quiz_id).filter(
        QuizResponse.student_id == student.id
    ).distinct().all()

    quizzes_marks = []
    total_quiz_score = 0
    total_quiz_max = 0

    for item in quiz_attempts:
        q_id = item[1]
        quiz = db.query(Quiz).filter(Quiz.id == q_id).first()
        if not quiz:
            continue
        responses = db.query(QuizResponse).filter(
            QuizResponse.quiz_id == q_id,
            QuizResponse.student_id == student.id
        ).all()

        correct_count = sum(1 for r in responses if r.is_correct)
        max_q = len(quiz.questions) if quiz.questions else len(responses)
        if len(responses) > 0:
            max_q = max(len(responses), max_q)

        pct = (correct_count / max_q * 100.0) if max_q > 0 else 0.0

        total_quiz_score += correct_count
        total_quiz_max += max_q

        quizzes_marks.append({
            "quiz_id": quiz.id,
            "title": quiz.title or (quiz.lecture.title if quiz.lecture else f"Quiz #{quiz.id}"),
            "course_name": quiz.lecture.section.course.name if (quiz.lecture and quiz.lecture.section and quiz.lecture.section.course) else "Course",
            "score": correct_count,
            "total_marks": max_q,
            "percentage": round(pct, 1),
            "date": max(r.answered_at for r in responses).isoformat() if responses else datetime.utcnow().isoformat()
        })

    assignments_marks = []
    total_assign_score = 0
    total_assign_max = 0

    subs = db.query(AssignmentSubmission).filter(
        AssignmentSubmission.student_id == student.id
    ).all()

    for s in subs:
        assign = s.assignment
        if not assign:
            continue
        status_lower = (s.status or "").lower()
        is_graded = status_lower in ["graded", "evaluated", "completed"]
        score = s.total_score if (is_graded and s.total_score is not None) else None
        max_marks = s.max_score or assign.total_marks or 100
        pct = (score / max_marks * 100.0) if (is_graded and score is not None and max_marks > 0) else 0.0

        if is_graded and score is not None:
            total_assign_score += score
            total_assign_max += max_marks

        from app.models.models import RegradeRequest
        regrade_req = db.query(RegradeRequest).filter(RegradeRequest.submission_id == s.id).first()

        assignments_marks.append({
            "assignment_id": assign.id,
            "submission_id": s.id,
            "title": assign.title,
            "course_name": assign.section.course.name if (assign.section and assign.section.course) else "Course",
            "score": score,
            "total_marks": max_marks,
            "status": "Graded" if is_graded else "Under Evaluation",
            "percentage": round(pct, 1) if is_graded else None,
            "date": s.submitted_at.isoformat() if s.submitted_at else datetime.utcnow().isoformat(),
            "regrade_status": regrade_req.status if regrade_req else None,
            "regrade_reason": regrade_req.reason if regrade_req else None,
            "teacher_response": regrade_req.teacher_response if (regrade_req and hasattr(regrade_req, "teacher_response")) else None,
        })

    from app.models.models import ExamGrade, Enrollment
    exam_grades = db.query(ExamGrade).filter(ExamGrade.student_id == student.id).all()
    exam_evaluations = []
    total_exam_score = 0.0
    total_exam_max = 0.0

    for eg in exam_grades:
        if eg.midterm_score or eg.midterm_max:
            total_exam_score += eg.midterm_score or 0.0
            total_exam_max += eg.midterm_max or 30.0
            exam_evaluations.append({
                "type": "Midterm Exam",
                "score": eg.midterm_score or 0.0,
                "total_marks": eg.midterm_max or 30.0,
                "percentage": round(((eg.midterm_score or 0.0) / (eg.midterm_max or 30.0) * 100.0), 1),
            })
        if eg.final_score or eg.final_max:
            total_exam_score += eg.final_score or 0.0
            total_exam_max += eg.final_max or 50.0
            exam_evaluations.append({
                "type": "Final Exam",
                "score": eg.final_score or 0.0,
                "total_marks": eg.final_max or 50.0,
                "percentage": round(((eg.final_score or 0.0) / (eg.final_max or 50.0) * 100.0), 1),
            })
        if eg.others_score or eg.others_max:
            total_exam_score += eg.others_score or 0.0
            total_exam_max += eg.others_max or 20.0
            exam_evaluations.append({
                "type": eg.others_title or "Project & Presentation",
                "score": eg.others_score or 0.0,
                "total_marks": eg.others_max or 20.0,
                "percentage": round(((eg.others_score or 0.0) / (eg.others_max or 20.0) * 100.0), 1),
            })

    from app.models.models import SemesterResult
    sem_res = db.query(SemesterResult).filter(
        SemesterResult.student_id == student.id,
        SemesterResult.status.in_(["submitted", "announced"])
    ).first()

    quiz_pct_100 = round((total_quiz_score / total_quiz_max * 100.0), 1) if total_quiz_max > 0 else 0.0
    assign_pct_100 = round((total_assign_score / total_assign_max * 100.0), 1) if total_assign_max > 0 else 0.0

    m_score = 0.0
    m_max = 30.0
    f_score = 0.0
    f_max = 50.0
    o_score = 0.0
    o_max = 20.0

    for eg in exam_grades:
        if eg.midterm_score or eg.midterm_max:
            m_score = eg.midterm_score or 0.0
            m_max = eg.midterm_max or 30.0
        if eg.final_score or eg.final_max:
            f_score = eg.final_score or 0.0
            f_max = eg.final_max or 50.0
        if eg.others_score or eg.others_max:
            o_score = eg.others_score or 0.0
            o_max = eg.others_max or 20.0

    q_comp = round(quiz_pct_100 * 0.15, 1)
    a_comp = round(assign_pct_100 * 0.15, 1)
    m_comp = round(((m_score / m_max * 100.0) * 0.25 if m_max > 0 else 0.0), 1)
    f_comp = round(((f_score / f_max * 100.0) * 0.40 if f_max > 0 else 0.0), 1)
    o_comp = round(((o_score / o_max * 100.0) * 0.05 if o_max > 0 else 0.0), 1)

    total_weighted = round(q_comp + a_comp + m_comp + f_comp + o_comp, 1)

    if total_weighted >= 85:
        letter_g, calc_gpa = "A", 4.0
    elif total_weighted >= 75:
        letter_g, calc_gpa = "B", 3.0
    elif total_weighted >= 65:
        letter_g, calc_gpa = "C", 2.0
    elif total_weighted >= 50:
        letter_g, calc_gpa = "D", 1.0
    else:
        letter_g, calc_gpa = "F", 0.0

    if sem_res:
        official_transcript = {
            "is_official": True,
            "status": sem_res.status.capitalize(),
            "total_weighted_score": sem_res.total_weighted_score,
            "letter_grade": sem_res.letter_grade,
            "gpa": sem_res.gpa,
            "quizzes_score_100": sem_res.quizzes_score_100,
            "assignments_score_100": sem_res.assignments_score_100,
            "midterm_score_100": sem_res.midterm_score_100,
            "final_score_100": sem_res.final_score_100,
            "others_score_100": sem_res.others_score_100,
            "announced_at": sem_res.announced_at.isoformat() if sem_res.announced_at else None,
        }
    else:
        official_transcript = {
            "is_official": False,
            "status": "Live Synced Estimate",
            "total_weighted_score": total_weighted,
            "letter_grade": letter_g,
            "gpa": calc_gpa,
            "quizzes_score_100": q_comp,
            "assignments_score_100": a_comp,
            "midterm_score_100": m_comp,
            "final_score_100": f_comp,
            "others_score_100": o_comp,
            "announced_at": None,
        }

    # Class Benchmark & Percentile Rank Calculation
    class_rank = 1
    total_class_students = 1
    class_average = total_weighted
    percentile_tier = "Top 10%"

    student_enrollment = db.query(Enrollment).filter(Enrollment.student_id == student.id, Enrollment.is_active == True).first()
    if student_enrollment:
        sec_id = student_enrollment.section_id
        class_enrollments = db.query(Enrollment).filter(Enrollment.section_id == sec_id, Enrollment.is_active == True).all()
        total_class_students = max(len(class_enrollments), 1)

        scores_list = []
        for e in class_enrollments:
            st = e.student
            if not st:
                continue
            # Calculate quick weighted score for peer
            p_q_res = db.query(QuizResponse).filter(QuizResponse.student_id == st.id).all()
            p_corr = sum(1 for r in p_q_res if r.is_correct)
            p_tot = max(len(p_q_res), 1)
            p_q_pct = (p_corr / p_tot * 100.0) if p_q_res else 0.0

            p_subs = db.query(AssignmentSubmission).filter(AssignmentSubmission.student_id == st.id).all()
            p_a_sc = sum((s.total_score or 0) for s in p_subs)
            p_a_mx = sum((s.max_score or 100) for s in p_subs)
            p_a_pct = (p_a_sc / p_a_mx * 100.0) if p_a_mx > 0 else 0.0

            p_weighted = round((p_q_pct * 0.15) + (p_a_pct * 0.15) + (m_comp if st.id == student.id else 15.0) + (f_comp if st.id == student.id else 25.0), 1)
            scores_list.append((st.id, p_weighted))

        scores_list.sort(key=lambda x: x[1], reverse=True)
        class_average = round(sum(s[1] for s in scores_list) / len(scores_list), 1) if scores_list else total_weighted

        for rank, (st_id, sc) in enumerate(scores_list, start=1):
            if st_id == student.id:
                class_rank = rank
                break

        rank_ratio = class_rank / total_class_students
        if rank_ratio <= 0.15:
            percentile_tier = "Top 15% (Outstanding)"
        elif rank_ratio <= 0.35:
            percentile_tier = "Top 35% (Above Average)"
        elif rank_ratio <= 0.60:
            percentile_tier = "Above Average"
        else:
            percentile_tier = "Average"

    return {
        "overall_percentage": total_weighted,
        "quizzes_score_100": quiz_pct_100,
        "assignments_score_100": assign_pct_100,
        "total_quizzes_attempted": len(quizzes_marks),
        "total_assignments_submitted": len(assignments_marks),
        "quizzes": quizzes_marks,
        "assignments": assignments_marks,
        "exams_and_others": exam_evaluations,
        "official_transcript": official_transcript,
        "class_benchmark": {
            "class_rank": class_rank,
            "total_students": total_class_students,
            "class_average": class_average,
            "percentile_tier": percentile_tier,
        }
    }


class StudentRegradeRequestPayload(BaseModel):
    reason: str


@student_portal_router.post("/assignments/{submission_id}/regrade-request")
def submit_assignment_regrade_request(
    submission_id: int,
    payload: StudentRegradeRequestPayload,
    student: Student = Depends(_get_current_student),
    db: Session = Depends(get_db)
):
    if not payload.reason.strip():
        raise HTTPException(status_code=400, detail="Please provide a valid reason for regrade request.")

    from app.models.models import AssignmentSubmission, RegradeRequest
    sub = db.query(AssignmentSubmission).filter(AssignmentSubmission.id == submission_id, AssignmentSubmission.student_id == student.id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Assignment submission not found.")

    existing = db.query(RegradeRequest).filter(RegradeRequest.submission_id == submission_id, RegradeRequest.student_id == student.id).first()
    if existing:
        existing.reason = payload.reason
        existing.status = "pending"
        existing.created_at = datetime.utcnow()
    else:
        req = RegradeRequest(
            submission_id=submission_id,
            student_id=student.id,
            reason=payload.reason,
            status="pending",
            created_at=datetime.utcnow()
        )
        db.add(req)

    db.commit()
    return {"ok": True, "message": "Regrade request submitted to teacher successfully."}


@student_portal_router.get("/quizzes/{quiz_id}/remedial")
def get_ai_remedial_quiz(
    quiz_id: int,
    student: Student = Depends(_get_current_student),
    db: Session = Depends(get_db)
):
    """
    AI Remedial Practice Quiz Generator.
    Analyzes wrong answers from student quiz response and returns 3 revision questions.
    """
    from app.models.models import Quiz, QuizResponse, QuizQuestion
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found.")

    wrong_responses = db.query(QuizResponse).filter(
        QuizResponse.quiz_id == quiz_id,
        QuizResponse.student_id == student.id,
        QuizResponse.is_correct == False
    ).all()

    wrong_q_ids = [r.question_id for r in wrong_responses]
    all_qs = list(quiz.questions)

    remedial_questions = []
    for q in all_qs:
        if q.id in wrong_q_ids:
            remedial_questions.append({
                "id": q.id,
                "question_text": f"Remedial Concept Practice: {q.question_text}",
                "option_a": q.option_a,
                "option_b": q.option_b,
                "option_c": q.option_c,
                "option_d": q.option_d,
                "correct_answer": q.correct_answer or "A",
                "explanation": f"Key Concept Review: Focus on core principle. Correct Option is ({q.correct_answer or 'A'})",
            })

    # If all answers were correct, provide revision challenge questions
    if not remedial_questions:
        for q in all_qs[:3]:
            remedial_questions.append({
                "id": q.id,
                "question_text": f"Mastery Challenge: {q.question_text}",
                "option_a": q.option_a,
                "option_b": q.option_b,
                "option_c": q.option_c,
                "option_d": q.option_d,
                "correct_answer": q.correct_answer or "A",
                "explanation": f"Great job! Reinforce your mastery with option ({q.correct_answer or 'A'})",
            })

    return {
        "quiz_id": quiz_id,
        "quiz_title": quiz.title or "Quiz Remedial",
        "total_remedial_questions": len(remedial_questions),
        "questions": remedial_questions
    }


