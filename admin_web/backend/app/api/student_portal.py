"""
Student Portal API Routers — Attendance, Profile Progress, and Question Bank.
"""
from datetime import datetime, date, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.database import get_db
from app.models.models import (
    User, Student, Enrollment, Section, Course, Lecture,
    LectureSession, Attendance, Quiz, QuizQuestion, QuizResponse, Topic
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
            courses_list.append({
                "course_id": sec.course.id,
                "course_code": sec.course.code,
                "course_name": sec.course.name
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
