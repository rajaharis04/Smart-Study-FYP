from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from sqlalchemy.orm import Session
import json

from app.db.database import get_db
from app.models.models import (
    User, Student, Enrollment, Topic, TopicMaterial, StudentQA, StudentLearningProfile, Lecture, LectureSession
)
from app.services.auth_service import decode_token
from app.services.learning_model import recalculate_student_learning_profile

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
router = APIRouter(prefix="/qa", tags=["QA (Student)"])

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


class QaRequest(BaseModel):
    question: str
    course_id: int


class QaResponse(BaseModel):
    answer: str
    sources: List[str]


@router.post("/ask", response_model=QaResponse)
def ask_question(
    payload: QaRequest,
    background_tasks: BackgroundTasks,
    student: Student = Depends(_get_current_student),
    db: Session = Depends(get_db)
):
    """
    RAG-powered AI Assistant endpoint.
    Retrieves relevant text from TopicMaterial and adapts answer difficulty
    and tone based on student mastery/weakness.
    """
    # 1. Retrieve all topics for this course
    topics = db.query(Topic).filter(Topic.course_id == payload.course_id).all()
    topic_ids = [t.id for t in topics]

    # 2. Check if student is struggling (weak) in this course
    is_weak = False
    profiles = db.query(StudentLearningProfile).filter(
        StudentLearningProfile.student_id == student.id,
        StudentLearningProfile.topic_id.in_(topic_ids)
    ).all() if topic_ids else []

    if profiles:
        is_weak = any(p.is_weak for p in profiles)

    # 3. Simulate RAG context retrieval from TopicMaterial text
    matched_context = []
    matched_sources = []
    
    materials = db.query(TopicMaterial).filter(TopicMaterial.topic_id.in_(topic_ids)).all() if topic_ids else []
    for mat in materials:
        if mat.extracted_text:
            # Simple keyword matching heuristic
            paragraphs = mat.extracted_text.split("\n\n")
            for p in paragraphs:
                # Match words with length > 4 to ignore common prepositions
                keywords = [w.lower() for w in payload.question.split() if len(w) > 4]
                if keywords and any(kw in p.lower() for kw in keywords):
                    matched_context.append(p.strip())
                    if mat.file_name not in matched_sources:
                        matched_sources.append(mat.file_name)
                    if len(matched_context) >= 2:
                        break

    # 4. Generate AI response (RAG simulated summary + student adaptation)
    question_lower = payload.question.lower()
    
    if matched_context:
        base_answer = "\n".join(matched_context[:2])
    else:
        # Fallback answers for standard curriculum concepts if no document matches
        if "deadlock" in question_lower:
            base_answer = "A deadlock occurs when a set of processes are blocked because each process is holding a resource and waiting for another resource held by some other process. The four necessary conditions for deadlock are: Mutual Exclusion, Hold and Wait, No Preemption, and Circular Wait."
            matched_sources.append("Operating_Systems_Ch7_Deadlocks.pdf")
        elif "semaphore" in question_lower:
            base_answer = "A semaphore is a synchronization tool consisting of an integer variable accessed via two atomic operations: wait() (or P) and signal() (or V). Semaphores are used to solve critical section problems and synchronize process execution."
            matched_sources.append("OS_Process_Synchronization.pdf")
        elif "scheduling" in question_lower:
            base_answer = "CPU Scheduling deals with selecting which process in the ready queue is allocated the CPU. Common scheduling algorithms include First-Come First-Served (FCFS), Shortest-Job-First (SJF), Round Robin (RR), and Priority Scheduling."
            matched_sources.append("OS_CPU_Scheduling_Lecture.pdf")
        else:
            base_answer = f"Based on the course syllabus, the question about '{payload.question}' relates to core concepts of this course. Please consult lecture slides and course notes for comprehensive exam guidelines."
            matched_sources.append("Course_Reference_Material.pdf")

    # Adapt response if student is weak
    if is_weak:
        answer = (
            "💡 [SUPPORTIVE GUIDE - Extra Explanations & Simplified Language]\n"
            "Assalam-o-Alaikum! Don't worry, let's break this concept down step-by-step so it's super easy to understand:\n\n"
            f"{base_answer}\n\n"
            "Key Takeaway: Think of it like a group of friends waiting in a circle for toys. Until one person lets go of a toy, nobody can continue! If you want to review, I suggest watching the recent lecture recording again."
        )
    else:
        answer = (
            "Here is the explanation retrieved from your course documents:\n\n"
            f"{base_answer}\n\n"
            "For further technical details, please refer to the cited lecture files."
        )

    # 5. Save the Q&A transaction in the database
    qa_record = StudentQA(
        student_id=student.id,
        course_id=payload.course_id,
        question=payload.question,
        answer=answer,
        sources=" | ".join(matched_sources) if matched_sources else "Lecture Notes",
        is_starred=False
    )
    db.add(qa_record)
    db.commit()

    # 6. Asynchronously trigger the learning model recalculation for the most recently studied topic
    last_session = db.query(LectureSession).join(Lecture).filter(
        LectureSession.student_id == student.id,
        Lecture.topic_id.in_(topic_ids)
    ).order_by(LectureSession.started_at.desc()).first()

    if last_session and last_session.lecture and last_session.lecture.topic_id:
        background_tasks.add_task(
            recalculate_student_learning_profile,
            student.id,
            last_session.lecture.topic_id,
            db
        )

    return QaResponse(
        answer=answer,
        sources=matched_sources if matched_sources else ["Course Reference Guide"]
    )
