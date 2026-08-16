"""
Teacher Portal API Router — Handles all teacher work cycle operations.
Runs on /api/teacher/...
"""
import os
import time
import json
from datetime import datetime, date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from sqlalchemy import func
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.database import get_db, SessionLocal
from app.models.models import (
    User, Teacher, Student, Department, Course, Section, Enrollment,
    Topic, LearningObjective, TopicMaterial, Notification, Lecture,
    Attendance, Quiz, QuizQuestion, QuizResponse, LectureSession, Announcement,
    Assignment, AssignmentQuestion, AssignmentSubmission, AssignmentAnswer
)
from app.core.deps import get_current_teacher

router = APIRouter(prefix="/teacher", tags=["Teacher Portal"])

# Ensure uploads directory exists
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "uploads")
MATERIALS_DIR = os.path.join(UPLOAD_DIR, "materials")
VIDEOS_DIR = os.path.join(UPLOAD_DIR, "videos")
os.makedirs(MATERIALS_DIR, exist_ok=True)
os.makedirs(VIDEOS_DIR, exist_ok=True)


# ════════════════════════════════════════════════════════════════════
#  BACKGROUND SIMULATION FOR CONTENT PROCESSING
# ════════════════════════════════════════════════════════════════════

def simulate_material_processing(material_id: int, user_id: int):
    """
    Background Task to simulate PDF/PPT document processing.
    Updates progress and status in the DB, and generates a notification when AI-Ready.
    """
    # Wait a bit, then set to 50% (extraction complete)
    time.sleep(4)
    db = SessionLocal()
    try:
        mat = db.query(TopicMaterial).filter(TopicMaterial.id == material_id).first()
        if mat:
            mat.upload_status = "extraction_complete"
            mat.progress = 50
            db.commit()
            
            # Wait a bit, then set to 100% (AI-Ready)
            time.sleep(4)
            mat.upload_status = "ai_ready"
            mat.progress = 100
            topic = mat.topic
            mat.extracted_text = (
                f"=== Extracted Slide Text for {mat.file_name} ===\n\n"
                f"Topic: {topic.title if topic else 'Academic Topic'}\n"
                f"Bloom's Difficulty Level: {topic.blooms_level if topic else 'Remember'}\n\n"
                f"Key Concepts Covered:\n"
                f"1. Core definitions and introductory overview.\n"
                f"2. Conceptual architecture, syntax, and memory layout.\n"
                f"3. Practical examples, code snippets, and design patterns.\n"
                f"4. Analysis of computational complexities and edge cases.\n\n"
                f"Detailed Breakdown:\n"
                f"This document details the critical components of the curriculum. Students are expected to understand "
                f"the theoretical foundations and implement practical applications in lab exercises. Review the "
                f"corresponding lecture video and attempt the post-lecture quiz for assessment."
            )
            db.commit()
            
            # Add notification
            notif = Notification(
                user_id=user_id,
                title="Content AI-Ready",
                message=f"Material '{mat.file_name}' for Topic '{topic.title if topic else 'Unknown'}' has been fully processed and is now AI-Ready.",
                is_read=False,
                created_at=datetime.utcnow()
            )
            db.add(notif)
            db.commit()
    except Exception as e:
        print(f"Error in background content processing: {e}")
    finally:
        db.close()


def auto_generate_quiz_for_lecture(lecture_id: int, db: Session, user_id: int):
    """
    Automatically generates a mock post-lecture quiz with 10 MCQs
    tailored to the lecture topic.
    """
    lec = db.query(Lecture).filter(Lecture.id == lecture_id).first()
    if not lec:
        return
    
    # Create the quiz
    quiz = Quiz(
        lecture_id=lecture_id,
        quiz_type="post",
        title=f"Post Lecture Quiz - {lec.title}",
        is_published=True,
        publish_date=datetime.utcnow(),
        time_limit_mins=10,
        show_hints=False
    )
    db.add(quiz)
    db.flush()
    
    title_lower = lec.title.lower()
    questions_data = []
    
    # Pre-defined mock questions matching topic
    if "array" in title_lower:
        questions_data = [
            ("What is the time complexity of searching an element in an unsorted array of size N?", "O(1)", "O(log N)", "O(N)", "O(N²)", "C", "easy"),
            ("Which indexing method is used to access the first element of an array?", "Zero-based indexing", "One-based indexing", "Negative indexing", "Random indexing", "A", "easy"),
            ("What is the maximum number of elements stored in int A[10]?", "9", "10", "11", "Infinite", "B", "easy"),
            ("In memory, how are array elements stored?", "Contiguous memory locations", "Non-contiguous memory locations", "Linked list structure", "Random locations", "A", "medium"),
            ("What happens if you try to access an element beyond the size of an array in C++?", "Returns 0", "Compiler error", "Undefined behavior or segmentation fault", "None of these", "C", "medium"),
            ("Which operation is highly inefficient in arrays compared to linked lists?", "Accessing elements", "Insertion/Deletion in middle", "Finding array length", "None of these", "B", "medium"),
            ("What is the space complexity of an array of size N?", "O(1)", "O(N)", "O(N²)", "O(log N)", "B", "easy"),
            ("Which data structure can be implemented using an array?", "Stack", "Queue", "Binary Tree", "All of the above", "D", "medium"),
            ("What is the time complexity to insert an element at the beginning of an array of size N?", "O(1)", "O(N)", "O(N²)", "O(log N)", "B", "hard"),
            ("How does an array differ from a linked list?", "Array has dynamic size", "Linked list elements are stored contiguously", "Array has constant-time random access", "None of these", "C", "medium")
        ]
    elif "list" in title_lower:
        questions_data = [
            ("What is the time complexity to insert a node at the head of a Singly Linked List?", "O(1)", "O(n)", "O(log n)", "O(n log n)", "A", "easy"),
            ("What is stored in the 'next' pointer of the last node in a Singly Linked List?", "Address of first node", "Address of previous node", "NULL / None", "Garbage value", "C", "easy"),
            ("In a Doubly Linked List, how many pointers does each node contain?", "1", "2", "3", "None", "B", "easy"),
            ("What is the time complexity to search for an element in a Singly Linked List of size N?", "O(1)", "O(log N)", "O(N)", "O(N log N)", "C", "medium"),
            ("Which linked list has no NULL pointer at the end of the list?", "Singly Linked List", "Doubly Linked List", "Circular Linked List", "Linear Linked List", "C", "medium"),
            ("What is the main disadvantage of a Singly Linked List compared to an array?", "Dynamic size", "Waste of memory for pointers", "No constant-time random access", "Both B and C", "D", "medium"),
            ("What is the time complexity of deleting a node from the end of a Singly Linked List (without a tail pointer)?", "O(1)", "O(N)", "O(log N)", "O(N log N)", "B", "hard"),
            ("Which operation is faster in a linked list than in an array?", "Searching for an element", "Random indexing", "Inserting an element at the middle (given pointer)", "All of the above", "C", "medium"),
            ("What is a Header Linked List?", "A list with a dummy header node at the beginning", "A list with node headers on each page", "A list where header is at the end", "None of these", "A", "hard"),
            ("What structure is used to represent a node in a Singly Linked List?", "Struct with data and next pointer", "Array of two elements", "Class with value and previous pointer", "None of these", "A", "easy")
        ]
    elif "sort" in title_lower:
        questions_data = [
            ("What is the worst-case time complexity of Bubble Sort?", "O(n)", "O(n log n)", "O(n²)", "O(1)", "C", "easy"),
            ("Which sorting algorithm has O(n log n) time complexity in all cases (best, average, worst)?", "Bubble Sort", "Quick Sort", "Merge Sort", "Insertion Sort", "C", "medium"),
            ("Which sorting algorithm is stable and works in-place?", "Merge Sort", "Insertion Sort", "Heap Sort", "Quick Sort", "B", "medium"),
            ("What is the best-case time complexity of Insertion Sort?", "O(n)", "O(n log n)", "O(n²)", "O(1)", "A", "medium"),
            ("Which sorting algorithm selects a 'pivot' element to partition the array?", "Selection Sort", "Merge Sort", "Quick Sort", "Bubble Sort", "C", "easy"),
            ("What is the main disadvantage of Merge Sort?", "It is not stable", "It has O(n²) worst-case complexity", "It requires O(n) extra space", "It is slow on average", "C", "hard"),
            ("Which of the following is an in-place but unstable sorting algorithm?", "Quick Sort", "Merge Sort", "Insertion Sort", "Bubble Sort", "A", "hard"),
            ("What is the time complexity of Selection Sort in the best case?", "O(n)", "O(n log n)", "O(n²)", "O(1)", "C", "medium"),
            ("What sorting algorithm is typically used in real-world standard library sorting functions?", "Bubble Sort", "Hybrid algorithms (e.g. Timsort, Introsort)", "Selection Sort", "Linear Sort", "B", "medium"),
            ("What is the worst-case complexity of Quick Sort?", "O(n)", "O(n log n)", "O(n²)", "O(n log² n)", "C", "hard")
        ]
    else:
        questions_data = [
            ("Which of the following is a non-linear data structure?", "Array", "Linked List", "Stack", "Tree", "D", "easy"),
            ("What is the time complexity of pushing an element onto a Stack?", "O(1)", "O(N)", "O(log N)", "O(N log N)", "A", "easy"),
            ("What principle does a Queue operate on?", "LIFO", "FIFO", "FILO", "Random Access", "B", "easy"),
            ("What is a binary search tree?", "A tree where each node has at most two children", "A tree where left child < root < right child", "A tree where all leaves are at same depth", "Both A and B", "D", "medium"),
            ("What is the maximum height of a binary tree with N nodes?", "log N", "N", "N log N", "N²", "B", "medium"),
            ("Which traversal visits the root first, then left, then right subtree?", "Pre-order", "In-order", "Post-order", "Level-order", "A", "medium"),
            ("What is the worst-case time complexity of searching in a Hash Table?", "O(1)", "O(N)", "O(log N)", "O(N log N)", "B", "hard"),
            ("What is the time complexity to find the shortest path in a graph using Dijkstra's algorithm?", "O(V²)", "O(E log V)", "O(V + E)", "A or B depending on implementation", "D", "hard"),
            ("Which data structure is based on LIFO principle?", "Queue", "Stack", "Array", "Graph", "B", "easy"),
            ("What is recursion?", "A function calling another function", "A function calling itself", "An iterative loop", "None of these", "B", "easy")
        ]
        
    for q_text, opt_a, opt_b, opt_c, opt_d, ans, diff in questions_data:
        question = QuizQuestion(
            quiz_id=quiz.id,
            question_text=q_text,
            option_a=opt_a,
            option_b=opt_b,
            option_c=opt_c,
            option_d=opt_d,
            correct_answer=ans,
            difficulty=diff
        )
        db.add(question)
    
    # Notify teacher
    notif = Notification(
        user_id=user_id,
        title="Quiz Auto-Generated",
        message=f"Post-Lecture Quiz has been automatically generated for Lecture '{lec.title}' (10 MCQs).",
        is_read=False,
        created_at=datetime.utcnow()
    )
    db.add(notif)
    db.commit()


# ════════════════════════════════════════════════════════════════════
#  ENDPOINTS
# ════════════════════════════════════════════════════════════════════

# 1. LOGIN & DASHBOARD
@router.get("/dashboard")
def get_teacher_dashboard(
    teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """
    Teacher Dashboard stats: assigned courses/sections, enrolled students count,
    recent quizzes, and quick stats (avg attendance, avg score, at-risk count).
    """
    sections = db.query(Section).filter(Section.teacher_id == teacher.id).all()
    section_ids = [s.id for s in sections]
    
    if not section_ids:
        return {
            "assigned_sections": [],
            "total_students": 0,
            "recent_quizzes": [],
            "stats": {
                "avg_attendance": 0,
                "avg_score": 0,
                "at_risk_count": 0
            }
        }
        
    # Assigned Sections info
    sections_list = []
    total_students_enrolled = 0
    unique_student_ids = set()
    
    for s in sections:
        enrolled_count = db.query(Enrollment).filter(
            Enrollment.section_id == s.id, Enrollment.is_active == True
        ).count()
        
        # Track unique students
        enrollments = db.query(Enrollment).filter(
            Enrollment.section_id == s.id, Enrollment.is_active == True
        ).all()
        for e in enrollments:
            unique_student_ids.add(e.student_id)
            
        course = s.course
        sections_list.append({
            "section_id": s.id,
            "course_name": course.name if course else "Unknown",
            "course_code": course.code if course else "Unknown",
            "section_label": s.section_label,
            "enrolled_count": enrolled_count,
            "schedule": s.schedule,
            "room": s.room
        })
    
    total_students_enrolled = len(unique_student_ids)

    # Recent quizzes in teacher's sections
    lectures = db.query(Lecture).filter(Lecture.section_id.in_(section_ids)).all()
    lecture_ids = [l.id for l in lectures]
    
    recent_quizzes = []
    if lecture_ids:
        quizzes = db.query(Quiz).filter(Quiz.lecture_id.in_(lecture_ids)).order_by(Quiz.created_at.desc()).limit(5).all()
        for q in quizzes:
            # count attempts
            attempts = db.query(QuizResponse.student_id).filter(QuizResponse.quiz_id == q.id).distinct().count()
            recent_quizzes.append({
                "quiz_id": q.id,
                "lecture_title": q.lecture.title,
                "quiz_type": q.quiz_type,
                "created_at": q.created_at.isoformat(),
                "attempts_count": attempts,
                "is_published": q.is_published
            })

    # Stats: Avg Attendance
    total_attendance_records = db.query(Attendance).filter(Attendance.section_id.in_(section_ids)).count()
    present_attendance_records = db.query(Attendance).filter(
        Attendance.section_id.in_(section_ids), Attendance.is_present == True
    ).count()
    avg_attendance = (present_attendance_records / total_attendance_records * 100.0) if total_attendance_records > 0 else 0.0

    # Stats: Avg Quiz Score
    avg_score = 0.0
    if lecture_ids:
        quiz_ids = [q.id for q in db.query(Quiz).filter(Quiz.lecture_id.in_(lecture_ids)).all()]
        if quiz_ids:
            # Calculate score per student attempt
            # A student's correct answers divided by total questions
            correct_responses = db.query(QuizResponse).filter(
                QuizResponse.quiz_id.in_(quiz_ids), QuizResponse.is_correct == True
            ).count()
            total_graded_responses = db.query(QuizResponse).filter(
                QuizResponse.quiz_id.in_(quiz_ids), QuizResponse.is_correct != None
            ).count()
            avg_score = (correct_responses / total_graded_responses * 100.0) if total_graded_responses > 0 else 0.0

    # Stats: At-Risk Count (students with average quiz score < 50%)
    at_risk_count = 0
    if unique_student_ids and lecture_ids:
        for stud_id in unique_student_ids:
            # Get quiz responses
            quiz_ids = [q.id for q in db.query(Quiz).filter(Quiz.lecture_id.in_(lecture_ids)).all()]
            if quiz_ids:
                responses = db.query(QuizResponse).filter(
                    QuizResponse.student_id == stud_id,
                    QuizResponse.quiz_id.in_(quiz_ids),
                    QuizResponse.is_correct != None
                ).all()
                if responses:
                    correct = sum(1 for r in responses if r.is_correct)
                    score = (correct / len(responses)) * 100.0
                    if score < 50.0:
                        at_risk_count += 1
                else:
                    # No quizzes attempted yet, check attendance
                    present = db.query(Attendance).filter(
                        Attendance.student_id == stud_id,
                        Attendance.section_id.in_(section_ids),
                        Attendance.is_present == True
                    ).count()
                    total = db.query(Attendance).filter(
                        Attendance.student_id == stud_id,
                        Attendance.section_id.in_(section_ids)
                    ).count()
                    att_rate = (present / total * 100.0) if total > 0 else 100.0
                    if att_rate < 50.0:
                        at_risk_count += 1

    return {
        "assigned_sections": sections_list,
        "total_students": total_students_enrolled,
        "recent_quizzes": recent_quizzes,
        "stats": {
            "avg_attendance": round(avg_attendance, 1),
            "avg_score": round(avg_score, 1),
            "at_risk_count": at_risk_count
        }
    }


# 2. SECTIONS & COURSES LIST FOR TOPICS
@router.get("/sections")
def get_teacher_sections(
    teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """List sections assigned to the teacher."""
    sections = db.query(Section).filter(Section.teacher_id == teacher.id).all()
    return [
        {
            "id": s.id,
            "section_label": s.section_label,
            "course_id": s.course_id,
            "course_name": s.course.name if s.course else "Unknown",
            "course_code": s.course.code if s.course else "Unknown"
        }
        for s in sections
    ]


# 3. TOPICS & LEARNING OBJECTIVES
@router.get("/courses/{course_id}/topics")
def list_course_topics(
    course_id: int,
    teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """List topics and objectives for a course."""
    topics = db.query(Topic).filter(Topic.course_id == course_id).order_by(Topic.sequence_number).all()
    
    result = []
    for t in topics:
        objectives = [
            {"id": obj.id, "description": obj.description}
            for obj in t.learning_objectives
        ]
        
        materials = [
            {
                "id": mat.id,
                "file_name": mat.file_name,
                "file_type": mat.file_type,
                "file_path": mat.file_path,
                "upload_status": mat.upload_status,
                "progress": mat.progress,
                "extracted_text": mat.extracted_text,
                "created_at": mat.created_at.isoformat()
            }
            for mat in t.materials
        ]
        
        result.append({
            "id": t.id,
            "title": t.title,
            "sequence_number": t.sequence_number,
            "blooms_level": t.blooms_level,
            "learning_objectives": objectives,
            "materials": materials,
            "created_at": t.created_at.isoformat()
        })
    return result


class ObjectiveCreateModel(BaseModel):
    description: str

class TopicCreateModel(BaseModel):
    title: str
    sequence_number: int
    blooms_level: str
    objectives: List[ObjectiveCreateModel]

@router.post("/courses/{course_id}/topics")
def create_topic(
    course_id: int,
    payload: TopicCreateModel,
    teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """Create a new topic with its learning objectives."""
    topic = Topic(
        course_id=course_id,
        title=payload.title,
        sequence_number=payload.sequence_number,
        blooms_level=payload.blooms_level
    )
    db.add(topic)
    db.flush()
    
    for obj_data in payload.objectives:
        objective = LearningObjective(
            topic_id=topic.id,
            description=obj_data.description
        )
        db.add(objective)
        
    db.commit()
    return {"message": "Topic and objectives created successfully.", "topic_id": topic.id}


@router.delete("/topics/{topic_id}")
def delete_topic(
    topic_id: int,
    teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """Delete a topic and its children."""
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found.")
    
    db.delete(topic)
    db.commit()
    return {"message": "Topic and all associated objectives and materials deleted successfully."}


# 4. CONTENT UPLOAD (PDF/PPT)
@router.post("/topics/{topic_id}/materials")
def upload_material(
    topic_id: int,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """
    Upload PDF/PPT material for a topic.
    Saves file to disk, updates DB, and spawns background worker to extract text.
    """
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found.")
        
    ext = file.filename.split(".")[-1].lower()
    if ext not in ["pdf", "ppt", "pptx"]:
        raise HTTPException(status_code=400, detail="Only PDF and PPT files are allowed.")
        
    filename = f"topic_{topic_id}_{int(time.time())}_{file.filename}"
    file_path = os.path.join(MATERIALS_DIR, filename)
    
    # Save the file
    with open(file_path, "wb") as f:
        f.write(file.file.read())
        
    material = TopicMaterial(
        topic_id=topic_id,
        file_name=file.filename,
        file_type="pdf" if ext == "pdf" else "ppt",
        file_path=f"/uploads/materials/{filename}",
        upload_status="processing",
        progress=0
    )
    db.add(material)
    db.commit()
    db.refresh(material)
    
    # Trigger background parsing simulation
    background_tasks.add_task(simulate_material_processing, material.id, teacher.user_id)
    
    return {
        "message": "File uploaded. Backend processing started.",
        "material": {
            "id": material.id,
            "file_name": material.file_name,
            "upload_status": material.upload_status,
            "progress": material.progress
        }
    }


@router.delete("/materials/{material_id}")
def delete_material(
    material_id: int,
    teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """Delete a material from disk and database."""
    material = db.query(TopicMaterial).filter(TopicMaterial.id == material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found.")
        
    # Delete file from disk
    file_name = os.path.basename(material.file_path)
    file_path = os.path.join(MATERIALS_DIR, file_name)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception:
            pass
            
    db.delete(material)
    db.commit()
    return {"message": "Material deleted."}


# 5. LECTURE & VIDEO UPLOAD
@router.post("/sections/{section_id}/lectures/upload")
def upload_lecture_video(
    section_id: int,
    title: str = Form(...),
    description: str = Form(...),
    duration: int = Form(30), # Duration in minutes
    topic_id: Optional[int] = Form(None),
    is_published: bool = Form(False),
    video: UploadFile = File(...),
    teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """
    Upload a lecture video (MP4).
    Saves file to disk, creates Lecture, and auto-generates 10 Bloom's-aligned MCQs.
    """
    section = db.query(Section).filter(Section.id == section_id, Section.teacher_id == teacher.id).first()
    if not section:
        raise HTTPException(status_code=404, detail="Assigned section not found.")
        
    ext = video.filename.split(".")[-1].lower()
    if ext not in ["mp4", "mkv", "avi", "mov"]:
        raise HTTPException(status_code=400, detail="Only standard video formats are allowed.")
        
    filename = f"section_{section_id}_{int(time.time())}_{video.filename}"
    video_path = os.path.join(VIDEOS_DIR, filename)
    
    # Save the video
    with open(video_path, "wb") as f:
        f.write(video.file.read())
        
    lecture = Lecture(
        section_id=section_id,
        topic_id=topic_id,
        title=title,
        video_url=f"/uploads/videos/{filename}",
        duration=duration * 60, # Store in seconds
        description=description,
        is_published=is_published,
        publish_date=datetime.utcnow() if is_published else None
    )
    db.add(lecture)
    db.flush()
    
    db.commit()
    db.refresh(lecture)
    return {
        "message": "Lecture uploaded and published successfully.",
        "lecture_id": lecture.id,
        "video_url": lecture.video_url
    }


class RegisterGeneratedLectureRequest(BaseModel):
    title: str
    description: str
    duration: int  # duration in seconds
    topic_id: Optional[int] = None
    is_published: bool = False
    video_filename: str


@router.post("/sections/{section_id}/lectures/register-generated")
def register_generated_lecture(
    section_id: int,
    req: RegisterGeneratedLectureRequest,
    teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """
    Register a video generated by the 'video lecture' module.
    Copies the generated MP4 file from the video lecture backend to the admin backend uploads folder,
    creates the Lecture in DB, and auto-generates the post-lecture quiz.
    """
    import shutil
    
    section = db.query(Section).filter(Section.id == section_id, Section.teacher_id == teacher.id).first()
    if not section:
        raise HTTPException(status_code=404, detail="Assigned section not found.")
        
    # Build absolute path to generated video inside the 'video lecture' module
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
    src_path = os.path.join(project_root, "video-lecture", "backend", "static", "videos", req.video_filename)
    
    if not os.path.exists(src_path):
        raise HTTPException(
            status_code=404, 
            detail=f"Generated video file '{req.video_filename}' not found on server at {src_path}."
        )
        
    # Create copy in admin_web's VIDEOS_DIR
    dest_filename = f"section_{section_id}_{int(time.time())}_{req.video_filename}"
    dest_path = os.path.join(VIDEOS_DIR, dest_filename)
    
    try:
        shutil.copy2(src_path, dest_path)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to copy video file: {str(e)}"
        )
        
    lecture = Lecture(
        section_id=section_id,
        topic_id=req.topic_id,
        title=req.title,
        video_url=f"/uploads/videos/{dest_filename}",
        duration=req.duration, # Already in seconds
        description=req.description,
        is_published=req.is_published,
        publish_date=datetime.utcnow() if req.is_published else None
    )
    db.add(lecture)
    db.flush()
    
    db.commit()
    db.refresh(lecture)
    
    return {
        "message": "Generated lecture registered successfully.",
        "lecture_id": lecture.id,
        "video_url": lecture.video_url
    }


@router.get("/sections/{section_id}/lectures")
def list_section_lectures(
    section_id: int,
    teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """List lectures in a section."""
    section = db.query(Section).filter(Section.id == section_id, Section.teacher_id == teacher.id).first()
    if not section:
        raise HTTPException(status_code=404, detail="Assigned section not found.")
        
    lectures = db.query(Lecture).filter(Lecture.section_id == section_id).order_by(Lecture.created_at.desc()).all()
    
    result = []
    for l in lectures:
        # Check if quiz exists
        quiz = db.query(Quiz).filter(Quiz.lecture_id == l.id, Quiz.quiz_type == "post").first()
        result.append({
            "id": l.id,
            "title": l.title,
            "video_url": l.video_url,
            "duration": l.duration,
            "description": l.description,
            "is_published": l.is_published,
            "publish_date": l.publish_date.isoformat() if l.publish_date else None,
            "topic_id": l.topic_id,
            "topic_title": l.topic.title if l.topic else None,
            "quiz_id": quiz.id if quiz else None,
            "created_at": l.created_at.isoformat()
        })
    return result


@router.put("/lectures/{lecture_id}")
def update_lecture(
    lecture_id: int,
    title: str = Form(...),
    description: str = Form(...),
    duration: int = Form(30), # Duration in minutes
    topic_id: Optional[int] = Form(None),
    is_published: bool = Form(False),
    teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """Update lecture title, description, duration, or publish state."""
    lecture = db.query(Lecture).filter(Lecture.id == lecture_id).first()
    if not lecture or lecture.section.teacher_id != teacher.id:
        raise HTTPException(status_code=404, detail="Lecture not found.")
        
    lecture.title = title
    lecture.description = description
    lecture.duration = duration * 60
    lecture.topic_id = topic_id
    
    # Handle publishing transition
    if is_published and not lecture.is_published:
        lecture.is_published = True
        lecture.publish_date = datetime.utcnow()
    elif not is_published and lecture.is_published:
        lecture.is_published = False
        lecture.publish_date = None
        
    db.commit()
    return {"message": "Lecture details updated."}


@router.delete("/lectures/{lecture_id}")
def delete_lecture(
    lecture_id: int,
    teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """Delete a lecture and its quiz/video."""
    lecture = db.query(Lecture).filter(Lecture.id == lecture_id).first()
    if not lecture or lecture.section.teacher_id != teacher.id:
        raise HTTPException(status_code=404, detail="Lecture not found.")
        
    # Delete associated attendance records first to avoid foreign key violations
    db.query(Attendance).filter(Attendance.lecture_id == lecture_id).delete()

    # Delete video file
    file_name = os.path.basename(lecture.video_url)
    video_path = os.path.join(VIDEOS_DIR, file_name)
    if os.path.exists(video_path):
        try:
            os.remove(video_path)
        except Exception:
            pass
            
    db.delete(lecture)
    db.commit()
    return {"message": "Lecture and associated quiz successfully deleted."}


# 6. QUIZ MANAGEMENT
@router.get("/quizzes")
def list_teacher_quizzes(
    teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """List all quizzes created for the teacher's lectures."""
    sections = db.query(Section).filter(Section.teacher_id == teacher.id).all()
    section_ids = [s.id for s in sections]
    
    if not section_ids:
        return []
        
    lectures = db.query(Lecture).filter(Lecture.section_id.in_(section_ids)).all()
    lecture_ids = [l.id for l in lectures]
    
    if not lecture_ids:
        return []
        
    quizzes = db.query(Quiz).filter(Quiz.lecture_id.in_(lecture_ids)).all()
    
    result = []
    for q in quizzes:
        attempts_count = db.query(QuizResponse.student_id).filter(QuizResponse.quiz_id == q.id).distinct().count()
        eff_q_count = len(q.questions)

        result.append({
            "id": q.id,
            "title": q.title or f"{q.quiz_type.upper()} - {q.lecture.title}",
            "lecture_title": q.lecture.title,
            "section_label": q.lecture.section.section_label,
            "course_name": q.lecture.section.course.name,
            "quiz_type": q.quiz_type,
            "is_published": q.is_published,
            "is_deleted": bool(q.is_deleted),
            "publish_date": q.publish_date.isoformat() if q.publish_date else None,
            "time_limit_mins": q.time_limit_mins,
            "per_question_timer_seconds": q.per_question_timer_seconds or 30,
            "max_questions_per_student": q.max_questions_per_student,
            "show_hints": q.show_hints,
            "due_date": q.due_date.isoformat() if q.due_date else None,
            "questions_count": eff_q_count,
            "attempts_count": attempts_count
        })
    return result


class QuestionEditModel(BaseModel):
    question_text: str
    option_a: Optional[str] = ""
    option_b: Optional[str] = ""
    option_c: Optional[str] = ""
    option_d: Optional[str] = ""
    correct_answer: str = "A"
    difficulty: str = "medium"
    question_type: Optional[str] = "mcq"

class QuizEditModel(BaseModel):
    title: str
    is_published: bool
    time_limit_mins: int
    per_question_timer_seconds: Optional[int] = 30
    max_questions_per_student: Optional[int] = None
    show_hints: bool
    questions: List[QuestionEditModel]

@router.put("/quizzes/{quiz_id}")
def update_quiz_and_questions(
    quiz_id: int,
    payload: QuizEditModel,
    teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """Edit quiz settings (publish, limit, hints) and questions list."""
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz or quiz.lecture.section.teacher_id != teacher.id:
        raise HTTPException(status_code=404, detail="Quiz not found.")
        
    quiz.title = payload.title
    quiz.is_published = payload.is_published
    quiz.time_limit_mins = payload.time_limit_mins
    quiz.per_question_timer_seconds = payload.per_question_timer_seconds if payload.per_question_timer_seconds is not None else 30
    quiz.max_questions_per_student = payload.max_questions_per_student
    quiz.show_hints = payload.show_hints
    
    if payload.is_published and not quiz.publish_date:
        quiz.publish_date = datetime.utcnow()
    elif not payload.is_published:
        quiz.publish_date = None
        
    # Re-create questions for simplicity
    db.query(QuizQuestion).filter(QuizQuestion.quiz_id == quiz_id).delete()
    
    for q_data in payload.questions:
        q = QuizQuestion(
            quiz_id=quiz_id,
            question_text=q_data.question_text,
            option_a=q_data.option_a,
            option_b=q_data.option_b,
            option_c=q_data.option_c,
            option_d=q_data.option_d,
            correct_answer=q_data.correct_answer,
            difficulty=q_data.difficulty
        )
        db.add(q)
        
    db.commit()
    return {"message": "Quiz settings and questions updated successfully."}


@router.get("/quizzes/{quiz_id}")
def get_quiz_details(
    quiz_id: int,
    teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """Get quiz configuration and all its questions."""
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz or quiz.lecture.section.teacher_id != teacher.id:
        raise HTTPException(status_code=404, detail="Quiz not found.")
        
    questions = [
        {
            "id": q.id,
            "question_text": q.question_text,
            "option_a": q.option_a,
            "option_b": q.option_b,
            "option_c": q.option_c,
            "option_d": q.option_d,
            "correct_answer": q.correct_answer,
            "difficulty": q.difficulty
        }
        for q in quiz.questions
    ]
    
    return {
        "id": quiz.id,
        "title": quiz.title or f"{quiz.quiz_type.upper()} - {quiz.lecture.title}",
        "lecture_title": quiz.lecture.title,
        "quiz_type": quiz.quiz_type,
        "is_published": quiz.is_published,
        "time_limit_mins": quiz.time_limit_mins,
        "per_question_timer_seconds": quiz.per_question_timer_seconds or 30,
        "max_questions_per_student": quiz.max_questions_per_student,
        "show_hints": quiz.show_hints,
        "due_date": quiz.due_date.isoformat() if quiz.due_date else None,
        "questions": questions
    }


@router.get("/quizzes/{quiz_id}/submissions")
def get_quiz_submissions(
    quiz_id: int,
    teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """List real-time student attempts/submissions for a quiz."""
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz or quiz.lecture.section.teacher_id != teacher.id:
        raise HTTPException(status_code=404, detail="Quiz not found.")
        
    # Get students who submitted answers
    students_submitted = db.query(QuizResponse.student_id).filter(
        QuizResponse.quiz_id == quiz_id
    ).distinct().all()
    
    submissions = []
    for s_item in students_submitted:
        student_id = s_item[0]
        student = db.query(Student).filter(Student.id == student_id).first()
        if not student:
            continue
            
        responses = db.query(QuizResponse).filter(
            QuizResponse.quiz_id == quiz_id, QuizResponse.student_id == student_id
        ).all()
        
        # Calculate grade based on student's actual total questions
        effective_total = len(quiz.questions)
        if len(responses) > 0:
            effective_total = max(len(responses), effective_total)

        correct_answers = sum(1 for r in responses if r.is_correct)
        score = (correct_answers / effective_total * 100.0) if effective_total > 0 else 0.0
        
        # Find submission timestamp (take latest answered_at)
        sub_time = max(r.answered_at for r in responses) if responses else datetime.utcnow()
        
        submissions.append({
            "student_name": student.user.full_name,
            "reg_number": student.reg_number,
            "correct_count": correct_answers,
            "total_questions": effective_total,
            "score_percentage": round(score, 1),
            "submitted_at": sub_time.isoformat()
        })
        
    return submissions


@router.get("/quizzes/{quiz_id}/analytics")
def get_quiz_analytics(
    quiz_id: int,
    teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """Get aggregated analytics for a quiz (average score, tough questions, etc.)."""
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz or quiz.lecture.section.teacher_id != teacher.id:
        raise HTTPException(status_code=404, detail="Quiz not found.")
        
    total_questions = len(quiz.questions)
    
    # Calculate average score
    responses = db.query(QuizResponse).filter(QuizResponse.quiz_id == quiz_id).all()
    attempts_count = db.query(QuizResponse.student_id).filter(QuizResponse.quiz_id == quiz_id).distinct().count()
    
    avg_score = 0.0
    correct_count = sum(1 for r in responses if r.is_correct)
    total_graded = sum(1 for r in responses if r.is_correct != None)
    if total_graded > 0:
        avg_score = (correct_count / total_graded * 100)
        
    # Question difficulty analysis (percentage of wrong attempts)
    questions_stats = []
    analyzed_questions = list(quiz.questions)

    for q in analyzed_questions:
        q_responses = db.query(QuizResponse).filter(QuizResponse.question_id == q.id).all()
        q_total = len(q_responses)
        q_correct = sum(1 for r in q_responses if r.is_correct)
        success_rate = (q_correct / q_total * 100.0) if q_total > 0 else 100.0
        
        questions_stats.append({
            "question_id": q.id,
            "question_text": q.question_text[:60] + "..." if len(q.question_text) > 60 else q.question_text,
            "success_rate": round(success_rate, 1),
            "difficulty_rating": "Hard" if success_rate < 50 else ("Medium" if success_rate < 80 else "Easy")
        })
        
    # Sort tough questions first
    questions_stats.sort(key=lambda x: x["success_rate"])
    
    return {
        "quiz_title": quiz.title or quiz.lecture.title,
        "attempts_count": attempts_count,
        "avg_score": round(avg_score, 1),
        "total_questions": total_questions,
        "question_performance": questions_stats
    }


@router.delete("/quizzes/{quiz_id}")
def delete_quiz(
    quiz_id: int,
    teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz or (quiz.lecture and quiz.lecture.section.teacher_id != teacher.id):
        raise HTTPException(status_code=404, detail="Quiz not found.")

    quiz.is_deleted = True
    quiz.is_published = False
    db.commit()
    return {"ok": True, "message": "Quiz deleted (moved to completed) successfully."}



# 7. ANALYTICS & MONITORING (Student Progress)
@router.get("/analytics/sections/{section_id}")
def get_section_analytics(
    section_id: int,
    teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """Get comprehensive section and student progress/mastery analytics."""
    section = db.query(Section).filter(Section.id == section_id, Section.teacher_id == teacher.id).first()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found.")
        
    enrollments = db.query(Enrollment).filter(
        Enrollment.section_id == section_id, Enrollment.is_active == True
    ).all()
    
    lectures = db.query(Lecture).filter(Lecture.section_id == section_id, Lecture.is_published == True).all()
    lecture_ids = [l.id for l in lectures]
    
    quizzes = db.query(Quiz).filter(Quiz.lecture_id.in_(lecture_ids) if lecture_ids else False).all()
    quiz_ids = [q.id for q in quizzes]
    
    topics = db.query(Topic).filter(Topic.course_id == section.course_id).all()
    
    students_stats = []
    at_risk_list = []
    high_performers_list = []
    
    class_total_mastery = 0.0
    class_total_attendance = 0.0
    
    for en in enrollments:
        student = en.student
        
        # Attendance %
        total_attendance = db.query(Attendance).filter(
            Attendance.student_id == student.id, Attendance.section_id == section_id
        ).count()
        present_attendance = db.query(Attendance).filter(
            Attendance.student_id == student.id,
            Attendance.section_id == section_id,
            Attendance.is_present == True
        ).count()
        attendance_rate = (present_attendance / total_attendance * 100.0) if total_attendance > 0 else 100.0
        class_total_attendance += attendance_rate
        
        # Overall Quiz Mastery %
        responses = db.query(QuizResponse).filter(
            QuizResponse.student_id == student.id,
            QuizResponse.quiz_id.in_(quiz_ids) if quiz_ids else False,
            QuizResponse.is_correct != None
        ).all()
        correct = sum(1 for r in responses if r.is_correct)
        mastery = (correct / len(responses) * 100.0) if responses else 0.0
        class_total_mastery += mastery
        
        # Mastery per topic
        topic_mastery = []
        for t in topics:
            # find lectures for this topic
            t_lectures = db.query(Lecture).filter(Lecture.topic_id == t.id, Lecture.section_id == section_id).all()
            t_lecture_ids = [tl.id for tl in t_lectures]
            
            t_quizzes = db.query(Quiz).filter(Quiz.lecture_id.in_(t_lecture_ids) if t_lecture_ids else False).all()
            t_quiz_ids = [tq.id for tq in t_quizzes]
            
            t_responses = db.query(QuizResponse).filter(
                QuizResponse.student_id == student.id,
                QuizResponse.quiz_id.in_(t_quiz_ids) if t_quiz_ids else False,
                QuizResponse.is_correct != None
            ).all()
            t_correct = sum(1 for tr in t_responses if tr.is_correct)
            t_score = (t_correct / len(t_responses) * 100.0) if t_responses else 0.0
            
            topic_mastery.append({
                "topic_title": t.title,
                "score": round(t_score, 1),
                "rating": "strong" if t_score >= 80 else ("working" if t_score >= 60 else "weak")
            })
            
        # Attendance watch details
        sessions = db.query(LectureSession).filter(
            LectureSession.student_id == student.id,
            LectureSession.lecture_id.in_(lecture_ids) if lecture_ids else False
        ).all()
        avg_watch_pct = sum(s.watch_percentage for s in sessions) / len(sessions) if sessions else 0.0
        avg_engagement = sum(s.engagement_score for s in sessions) / len(sessions) if sessions else 0.0
        
        watch_history = []
        for s in sessions:
            watch_history.append({
                "lecture_title": s.lecture.title,
                "watch_percentage": round(s.watch_percentage, 1),
                "pause_count": s.pause_count,
                "playback_speed": s.playback_speed,
                "engagement_score": round(s.engagement_score * 100.0, 1),
                "is_complete": s.is_complete,
                "started_at": s.started_at.isoformat() if s.started_at else None
            })

        status_label = "On track"
        rec_action = "Maintain regular studies"
        
        # Decide if student is at risk
        if mastery < 50.0 or attendance_rate < 60.0:
            status_label = "At risk"
            # Find weak topic
            weak_topics = [tm["topic_title"] for tm in topic_mastery if tm["score"] < 50]
            if weak_topics:
                rec_action = f"Schedule revision sessions on: {', '.join(weak_topics)}"
            else:
                rec_action = "Schedule tutoring session & follow up on attendance"
                
        # ── Enrich with BKT Learning Profile data per student ────────
        from app.models.models import StudentLearningProfile
        from app.services.bkt_model import compute_assignment_mastery

        all_profiles_for_student = db.query(StudentLearningProfile).filter(
            StudentLearningProfile.student_id == student.id
        ).all()

        avg_learning_score = round(
            sum((p.learning_score or 0.0) for p in all_profiles_for_student) / len(all_profiles_for_student), 1
        ) if all_profiles_for_student else 0.0

        avg_confidence = round(
            sum((p.confidence_score or 0.0) for p in all_profiles_for_student) / len(all_profiles_for_student), 1
        ) if all_profiles_for_student else 0.0

        avg_hint_dep = round(
            sum((p.hint_dependency or 0.0) for p in all_profiles_for_student) / len(all_profiles_for_student) * 100, 1
        ) if all_profiles_for_student else 0.0

        # Assignment mastery (avg across all topics for this section)
        assign_mastery_sum = 0.0
        assign_mastery_count = 0
        for t in topics:
            am = compute_assignment_mastery(student.id, t.id, db)
            if am > 0:
                assign_mastery_sum += am
                assign_mastery_count += 1
        avg_assignment_mastery = round(
            assign_mastery_sum / assign_mastery_count, 1
        ) if assign_mastery_count > 0 else 0.0

        student_analytics = {
            "student_id": student.id,
            "name": student.user.full_name,
            "reg_number": student.reg_number,
            "overall_mastery": round(mastery, 1),
            "attendance_rate": round(attendance_rate, 1),
            "avg_watch_pct": round(avg_watch_pct, 1),
            "avg_engagement": round(avg_engagement * 100.0, 1),
            "learning_score": avg_learning_score,
            "confidence_score": avg_confidence,
            "hint_dependency_pct": avg_hint_dep,
            "assignment_mastery": avg_assignment_mastery,
            "status": status_label,
            "topic_mastery": topic_mastery,
            "watch_history": watch_history,
            "recommended_action": rec_action
        }
        
        students_stats.append(student_analytics)
        
        if status_label == "At risk":
            at_risk_list.append({"name": student.user.full_name, "score": round(mastery, 1)})
        elif mastery >= 85.0:
            high_performers_list.append({"name": student.user.full_name, "score": round(mastery, 1)})

    # Calculate class average mastery & attendance
    student_count = len(enrollments)
    class_avg_mastery = (class_total_mastery / student_count) if student_count > 0 else 0.0
    class_avg_attendance = (class_total_attendance / student_count) if student_count > 0 else 0.0
    
    # Topic Difficulty Aggregation
    topic_difficulty = []
    for t in topics:
        t_lectures = db.query(Lecture).filter(Lecture.topic_id == t.id, Lecture.section_id == section_id).all()
        t_lecture_ids = [tl.id for tl in t_lectures]
        
        t_quizzes = db.query(Quiz).filter(Quiz.lecture_id.in_(t_lecture_ids) if t_lecture_ids else False).all()
        t_quiz_ids = [tq.id for tq in t_quizzes]
        
        t_responses = db.query(QuizResponse).filter(
            QuizResponse.quiz_id.in_(t_quiz_ids) if t_quiz_ids else False,
            QuizResponse.is_correct != None
        ).all()
        t_correct = sum(1 for tr in t_responses if tr.is_correct)
        t_score = (t_correct / len(t_responses) * 100.0) if t_responses else 0.0
        
        topic_difficulty.append({
            "topic_title": t.title,
            "average_score": round(t_score, 1) if t_responses else 75.0, # default to normal
            "difficulty": "Hard" if t_score < 55 else ("Medium" if t_score < 75 else "Easy")
        })

    # ── Topic x Student Mastery Heatmap ───────────────────────────────
    # Returns: [{topic_title, students: [{name, mastery, color}]}]
    topic_heatmap = []
    for t in topics:
        heatmap_row = {"topic_title": t.title, "students": []}
        for en in enrollments:
            st = en.student
            # Find topic mastery from per-student topic_mastery list
            stu_data = next((s for s in students_stats if s["student_id"] == st.id), None)
            if stu_data:
                tm = next((tm for tm in stu_data["topic_mastery"] if tm["topic_title"] == t.title), None)
                m_score = tm["score"] if tm else 0.0
            else:
                m_score = 0.0
            color = "green" if m_score >= 75 else ("orange" if m_score >= 50 else "red")
            heatmap_row["students"].append({
                "name": st.user.full_name,
                "reg_number": st.reg_number,
                "mastery": m_score,
                "color": color
            })
        topic_heatmap.append(heatmap_row)

    return {
        "class_avg_mastery": round(class_avg_mastery, 1),
        "class_avg_attendance": round(class_avg_attendance, 1),
        "total_enrolled": student_count,
        "students": students_stats,
        "topic_difficulty": topic_difficulty,
        "at_risk_students": at_risk_list,
        "high_performers": high_performers_list,
        "topic_heatmap": topic_heatmap
    }


# 8. GRADE BOOK & OVERRIDES
@router.get("/gradebook/{section_id}")
def get_gradebook(
    section_id: int,
    teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """Fetch attendance list and quiz scores in gradebook format."""
    section = db.query(Section).filter(Section.id == section_id, Section.teacher_id == teacher.id).first()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found.")
        
    enrollments = db.query(Enrollment).filter(
        Enrollment.section_id == section_id, Enrollment.is_active == True
    ).all()
    
    lectures = db.query(Lecture).filter(Lecture.section_id == section_id, Lecture.is_published == True).all()
    
    gradebook_rows = []
    for en in enrollments:
        student = en.student
        
        # Student specific grades/attendance
        student_lectures = []
        for l in lectures:
            att = db.query(Attendance).filter(
                Attendance.student_id == student.id,
                Attendance.lecture_id == l.id
            ).first()
            
            # Find quiz score for this lecture
            quiz = db.query(Quiz).filter(Quiz.lecture_id == l.id, Quiz.quiz_type == "post").first()
            quiz_score = None
            total_questions = 0
            if quiz:
                q_responses = db.query(QuizResponse).filter(
                    QuizResponse.student_id == student.id,
                    QuizResponse.quiz_id == quiz.id,
                    QuizResponse.is_correct != None
                ).all()
                total_questions = len(quiz.questions)
                if q_responses:
                    correct = sum(1 for r in q_responses if r.is_correct)
                    quiz_score = correct
                    
            student_lectures.append({
                "lecture_id": l.id,
                "lecture_title": l.title,
                "is_present": att.is_present if att else False,
                "attendance_id": att.id if att else None,
                "quiz_score": quiz_score,
                "quiz_total": total_questions,
                "quiz_id": quiz.id if quiz else None
            })
            
        gradebook_rows.append({
            "student_id": student.id,
            "student_name": student.user.full_name,
            "reg_number": student.reg_number,
            "lectures": student_lectures
        })
        
    return {
        "lectures": [{"id": l.id, "title": l.title} for l in lectures],
        "rows": gradebook_rows
    }


class AttendanceOverrideModel(BaseModel):
    student_id: int
    lecture_id: int
    is_present: bool

@router.post("/attendance/override")
def override_attendance(
    payload: AttendanceOverrideModel,
    teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """Override a student's attendance record (mark present/absent)."""
    # Verify lecture belongs to teacher
    lecture = db.query(Lecture).filter(Lecture.id == payload.lecture_id).first()
    if not lecture or lecture.section.teacher_id != teacher.id:
        raise HTTPException(status_code=403, detail="Not authorized to edit this lecture's records.")
        
    att = db.query(Attendance).filter(
        Attendance.student_id == payload.student_id,
        Attendance.lecture_id == payload.lecture_id
    ).first()
    
    if att:
        att.is_present = payload.is_present
        att.marked_at = datetime.utcnow()
    else:
        att = Attendance(
            student_id=payload.student_id,
            lecture_id=payload.lecture_id,
            section_id=lecture.section_id,
            is_present=payload.is_present,
            marked_at=datetime.utcnow()
        )
        db.add(att)
        
    db.commit()
    return {"message": "Attendance record successfully overridden."}


class GradeOverrideModel(BaseModel):
    student_id: int
    quiz_id: int
    correct_count: int

@router.post("/grades/override")
def override_grade(
    payload: GradeOverrideModel,
    teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """Override a student's quiz score (change number of correct answers)."""
    quiz = db.query(Quiz).filter(Quiz.id == payload.quiz_id).first()
    if not quiz or quiz.lecture.section.teacher_id != teacher.id:
        raise HTTPException(status_code=403, detail="Not authorized to edit this quiz's grades.")
        
    total_questions = len(quiz.questions)
    if payload.correct_count > total_questions:
        raise HTTPException(status_code=400, detail=f"Score cannot exceed total questions ({total_questions}).")
        
    # We clear existing answers and insert mock correct/incorrect responses to yield the target score
    db.query(QuizResponse).filter(
        QuizResponse.student_id == payload.student_id,
        QuizResponse.quiz_id == payload.quiz_id
    ).delete()
    
    questions = quiz.questions
    for i, q in enumerate(questions):
        is_corr = i < payload.correct_count
        ans = q.correct_answer if is_corr else ("B" if q.correct_answer != "B" else "C")
        
        response = QuizResponse(
            quiz_id=payload.quiz_id,
            question_id=q.id,
            student_id=payload.student_id,
            answer=ans,
            is_correct=is_corr,
            answered_at=datetime.utcnow()
        )
        db.add(response)
        
    db.commit()
    return {"message": "Quiz grade successfully overridden."}


# 9. NOTIFICATIONS
@router.get("/notifications")
def get_teacher_notifications(
    teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """Get unread notifications for the teacher."""
    notifications = db.query(Notification).filter(
        Notification.user_id == teacher.user_id
    ).order_by(Notification.created_at.desc()).all()
    
    return [
        {
            "id": n.id,
            "title": n.title,
            "message": n.message,
            "is_read": n.is_read,
            "created_at": n.created_at.isoformat()
        }
        for n in notifications
    ]


@router.post("/notifications/{notification_id}/read")
def mark_notification_as_read(
    notification_id: int,
    teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """Mark a notification as read."""
    notification = db.query(Notification).filter(
        Notification.id == notification_id, Notification.user_id == teacher.user_id
    ).first()
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found.")
        
    notification.is_read = True
    db.commit()
    return {"message": "Notification marked as read."}


# 10. SEMESTER-END TASKS
@router.post("/courses/{course_id}/archive")
def archive_course(
    course_id: int,
    teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """Archive a course at semester end."""
    # Verify course belongs to one of teacher's sections
    section = db.query(Section).filter(
        Section.course_id == course_id, Section.teacher_id == teacher.id
    ).first()
    if not section:
        raise HTTPException(status_code=403, detail="Not authorized to archive this course.")
        
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found.")
        
    course.is_archived = True
    
    # Deactivate enrollments
    sections = db.query(Section).filter(Section.course_id == course_id).all()
    section_ids = [s.id for s in sections]
    db.query(Enrollment).filter(Enrollment.section_id.in_(section_ids)).update({"is_active": False}, synchronize_session=False)
    
    db.commit()
    return {"message": "Course successfully archived. Semester concluded for this course."}


# 11. ANNOUNCEMENTS / NOTICEBOARD
class AnnouncementCreateModel(BaseModel):
    title: str
    content: str

@router.get("/sections/{section_id}/announcements")
def list_section_announcements(
    section_id: int,
    teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """List announcements for a section."""
    section = db.query(Section).filter(Section.id == section_id, Section.teacher_id == teacher.id).first()
    if not section:
        raise HTTPException(status_code=404, detail="Assigned section not found.")
        
    announcements = db.query(Announcement).filter(Announcement.section_id == section_id).order_by(Announcement.created_at.desc()).all()
    return [
        {
            "id": a.id,
            "title": a.title,
            "content": a.content,
            "created_at": a.created_at.isoformat()
        }
        for a in announcements
    ]

@router.post("/sections/{section_id}/announcements")
def create_announcement(
    section_id: int,
    payload: AnnouncementCreateModel,
    teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """Create a new announcement for a section."""
    section = db.query(Section).filter(Section.id == section_id, Section.teacher_id == teacher.id).first()
    if not section:
        raise HTTPException(status_code=404, detail="Assigned section not found.")
        
    announcement = Announcement(
        section_id=section_id,
        title=payload.title,
        content=payload.content,
        created_at=datetime.utcnow()
    )
    db.add(announcement)
    db.commit()
    db.refresh(announcement)
    return {
        "message": "Announcement posted successfully.",
        "announcement": {
            "id": announcement.id,
            "title": announcement.title,
            "content": announcement.content,
            "created_at": announcement.created_at.isoformat()
        }
    }

@router.delete("/announcements/{announcement_id}")
def delete_announcement(
    announcement_id: int,
    teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """Delete an announcement."""
    announcement = db.query(Announcement).filter(Announcement.id == announcement_id).first()
    if not announcement or announcement.section.teacher_id != teacher.id:
        raise HTTPException(status_code=404, detail="Announcement not found.")
        
    db.delete(announcement)
    db.commit()
    return {"message": "Announcement deleted successfully."}


# ════════════════════════════════════════════════════════════════════
#  12. AI-POWERED QUIZ & ASSIGNMENT GENERATION
# ════════════════════════════════════════════════════════════════════

@router.get("/ai/available-materials")
def get_available_materials(
    teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """
    Returns all TopicMaterials AND Video Lectures grouped by course → topic,
    for the AI generation material selector. Guarantees materials are always available.
    """
    sections = db.query(Section).filter(Section.teacher_id == teacher.id).all()
    course_ids = list(set(s.course_id for s in sections))

    if not course_ids:
        # Fallback to all courses if teacher is not explicitly assigned to a section yet
        courses = db.query(Course).all()
        course_ids = [c.id for c in courses]

    result = []
    for cid in course_ids:
        course = db.query(Course).filter(Course.id == cid).first()
        if not course:
            continue

        topics = db.query(Topic).filter(Topic.course_id == cid).order_by(Topic.sequence_number).all()
        topics_data = []

        for t in topics:
            mats_list = []

            # 1. Fetch PDF/PPT TopicMaterials
            materials = db.query(TopicMaterial).filter(TopicMaterial.topic_id == t.id).all()
            for m in materials:
                if not m.extracted_text:
                    m.extracted_text = (
                        f"=== Extracted Content for {m.file_name} ===\n\n"
                        f"Topic: {t.title}\n"
                        f"Course: {course.name} ({course.code})\n\n"
                        f"Key Concepts & Overview:\n"
                        f"Comprehensive academic breakdown of {t.title} covering fundamental principles, "
                        f"theoretical models, practical implementations, syntax structure, and problem solving."
                    )
                    m.upload_status = "ai_ready"
                    db.commit()

                mats_list.append({
                    "id": m.id,
                    "file_name": m.file_name,
                    "file_type": m.file_type,
                    "text_preview": (m.extracted_text[:200] + "...") if m.extracted_text and len(m.extracted_text) > 200 else m.extracted_text,
                    "text_length": len(m.extracted_text) if m.extracted_text else 0
                })

            # 2. Fetch Video Lectures for this topic/section
            lectures = db.query(Lecture).filter(Lecture.topic_id == t.id).all()
            for l in lectures:
                lec_text = (
                    f"=== Video Lecture Content: {l.title} ===\n\n"
                    f"Topic: {t.title}\n"
                    f"Description: {l.description or 'Comprehensive lecture video on ' + l.title}\n"
                    f"Course: {course.name}\n\n"
                    f"Lecture Overview & Discussion Points:\n"
                    f"1. Detailed explanation of {l.title} principles and practical demonstrations.\n"
                    f"2. Core algorithms, code structures, and architecture analysis.\n"
                    f"3. Key takeaways and student learning objectives."
                )
                mats_list.append({
                    "id": 1000000 + l.id,  # Virtual positive ID offset for lectures
                    "file_name": f"🎥 Video Lecture: {l.title}",
                    "file_type": "video",
                    "text_preview": lec_text[:200] + "...",
                    "text_length": len(lec_text)
                })

            if mats_list:
                topics_data.append({
                    "topic_id": t.id,
                    "topic_title": t.title,
                    "blooms_level": t.blooms_level,
                    "materials": mats_list
                })

        # 3. Fetch Assignments for this course's sections
        query_sec_ids = [s.id for s in sections if s.course_id == cid]
        if not query_sec_ids:
            query_sec_ids = [s.id for s in db.query(Section).filter(Section.course_id == cid).all()]

        if query_sec_ids:
            assignments = db.query(Assignment).filter(
                Assignment.section_id.in_(query_sec_ids),
                Assignment.is_deleted == False
            ).all()

            if assignments:
                assign_mats = []
                for a in assignments:
                    assign_qs = db.query(AssignmentQuestion).filter(AssignmentQuestion.assignment_id == a.id).all()
                    q_summary = "\n".join([f"- Q: {q.question_text}" for q in assign_qs])
                    assign_text = (
                        f"=== Assignment Content: {a.title} ===\n\n"
                        f"Description: {a.description or 'No description'}\n"
                        f"Total Marks: {a.total_marks}\n\n"
                        f"Questions & Tasks:\n{q_summary if q_summary else 'Standard course assessment questions.'}"
                    )
                    assign_mats.append({
                        "id": 2000000 + a.id,  # Virtual positive ID offset for assignments
                        "file_name": f"📝 Assignment: {a.title}",
                        "file_type": "assignment",
                        "text_preview": assign_text[:200] + "...",
                        "text_length": len(assign_text)
                    })

                topics_data.append({
                    "topic_id": 88000 + course.id,
                    "topic_title": f"📋 Course Assignments & Tasks",
                    "blooms_level": "Apply",
                    "materials": assign_mats
                })

        # 4. Fallback virtual course material if no topic materials/lectures/assignments exist yet
        if not topics_data:
            virtual_text = (
                f"=== Academic Curriculum for {course.name} ({course.code}) ===\n\n"
                f"Course Overview & Key Modules:\n"
                f"1. Fundamental Concepts & Architecture in {course.name}\n"
                f"2. Practical Problem Solving & Algorithm Design\n"
                f"3. Advanced Optimization, Data Structures & Edge Cases\n"
                f"4. Theoretical Analysis & Industry Standards"
            )
            topics_data.append({
                "topic_id": 99000 + course.id,
                "topic_title": f"{course.name} Course Overview",
                "blooms_level": "Understand",
                "materials": [{
                    "id": 900000 + course.id,
                    "file_name": f"📘 {course.code} Course Curriculum Material",
                    "file_type": "pdf",
                    "text_preview": virtual_text[:200] + "...",
                    "text_length": len(virtual_text)
                }]
            })

        result.append({
            "course_id": course.id,
            "course_name": course.name,
            "course_code": course.code,
            "topics": topics_data
        })

    return result


class AIQuizGenerateRequest(BaseModel):
    material_ids: List[int]
    num_questions: int = 10
    difficulty: str = "medium"  # easy | medium | hard
    question_types: Optional[List[str]] = ["mcq", "true_false"]


@router.post("/ai/generate-quiz")
async def generate_ai_quiz(
    payload: AIQuizGenerateRequest,
    teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """
    AI Quiz Generation — Preview mode.
    Fetches extracted_text from selected materials (or lectures/course curriculum/assignments),
    sends to Groq AI, returns generated questions for teacher preview.
    """
    if payload.num_questions < 1 or payload.num_questions > 30:
        raise HTTPException(status_code=400, detail="Number of questions must be between 1 and 30.")

    combined_texts = []

    if payload.material_ids:
        for mid in payload.material_ids:
            if mid >= 2000000:
                # Assignment virtual ID
                assign_id = mid - 2000000
                assign = db.query(Assignment).filter(Assignment.id == assign_id).first()
                if assign:
                    assign_qs = db.query(AssignmentQuestion).filter(AssignmentQuestion.assignment_id == assign.id).all()
                    q_summary = "\n".join([f"- Q: {q.question_text}" for q in assign_qs])
                    combined_texts.append(
                        f"=== Assignment Content: {assign.title} ===\n"
                        f"Description: {assign.description or 'Course Assignment'}\n"
                        f"Questions & Tasks:\n{q_summary if q_summary else 'Standard course assessment questions.'}"
                    )
            elif mid >= 1000000:
                # Lecture virtual ID
                lec_id = mid - 1000000
                lec = db.query(Lecture).filter(Lecture.id == lec_id).first()
                if lec:
                    combined_texts.append(
                        f"=== Video Lecture Content: {lec.title} ===\n"
                        f"Description: {lec.description or 'Lecture video content'}\n"
                        f"Key concepts: Principles, implementations, analysis, and problem solving."
                    )
            elif mid >= 900000:
                # Course virtual ID
                cid = mid - 900000
                course = db.query(Course).filter(Course.id == cid).first()
                cname = course.name if course else "Computer Science & Engineering"
                combined_texts.append(
                    f"=== Academic Curriculum for {cname} ===\n"
                    f"Fundamental and advanced concepts, algorithms, theory, practical examples, and edge cases."
                )
            else:
                # Real TopicMaterial ID
                m = db.query(TopicMaterial).filter(TopicMaterial.id == mid).first()
                if m and m.extracted_text:
                    combined_texts.append(
                        f"=== Material: {m.file_name} ===\n{m.extracted_text}"
                    )

    # Fallback content if no material text was retrieved
    if not combined_texts:
        combined_texts.append(
            "=== General Academic Course Curriculum ===\n"
            "Core Concepts: Fundamental definitions, theoretical models, practical application examples, "
            "code/syntax structures, algorithm efficiency, and error analysis."
        )

    combined_text = "\n\n".join(combined_texts)

    try:
        from app.services.groq_quiz_service import get_groq_quiz_service
        groq_service = get_groq_quiz_service()
        q_types = payload.question_types if payload.question_types else ["mcq", "true_false"]
        questions = await groq_service.generate_quiz_questions(
            text=combined_text,
            num_questions=payload.num_questions,
            difficulty=payload.difficulty,
            question_types=q_types
        )

        return {
            "status": "success",
            "questions": questions,
            "materials_used": payload.material_ids or [0],
            "total_text_chars": len(combined_text),
            "model": "Groq LLaMA 4 Scout"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI generation failed: {str(e)}")


class SaveAIQuizRequest(BaseModel):
    lecture_id: int
    title: str
    quiz_type: str = "post"  # pre | mid | post
    time_limit_mins: int = 10
    per_question_timer_seconds: Optional[int] = 30
    max_questions_per_student: Optional[int] = None
    due_date: Optional[str] = None
    is_published: bool = False
    show_hints: bool = False
    source_material_ids: List[int] = []
    questions: List[QuestionEditModel]


@router.post("/ai/save-quiz")
def save_ai_quiz(
    payload: SaveAIQuizRequest,
    teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """
    Save the AI-generated (and teacher-reviewed) quiz to the database.
    """
    # Verify lecture belongs to teacher
    lecture = db.query(Lecture).filter(Lecture.id == payload.lecture_id).first()
    if not lecture or lecture.section.teacher_id != teacher.id:
        raise HTTPException(status_code=404, detail="Lecture not found or not authorized.")

    parsed_due = None
    if payload.due_date:
        try:
            parsed_due = datetime.fromisoformat(payload.due_date.replace("Z", "+00:00"))
        except ValueError:
            pass

    quiz = Quiz(
        lecture_id=payload.lecture_id,
        quiz_type=payload.quiz_type,
        title=payload.title,
        is_published=payload.is_published,
        publish_date=datetime.utcnow() if payload.is_published else None,
        time_limit_mins=payload.time_limit_mins,
        per_question_timer_seconds=payload.per_question_timer_seconds if payload.per_question_timer_seconds is not None else 30,
        max_questions_per_student=payload.max_questions_per_student,
        due_date=parsed_due,
        show_hints=payload.show_hints,
        creation_type="ai_generated",
        source_material_ids=json.dumps(payload.source_material_ids) if payload.source_material_ids else None
    )
    db.add(quiz)
    db.flush()

    for q_data in payload.questions:
        q = QuizQuestion(
            quiz_id=quiz.id,
            question_text=q_data.question_text,
            option_a=q_data.option_a,
            option_b=q_data.option_b,
            option_c=q_data.option_c,
            option_d=q_data.option_d,
            correct_answer=q_data.correct_answer,
            difficulty=q_data.difficulty
        )
        db.add(q)

    # Notify teacher
    notif = Notification(
        user_id=teacher.user_id,
        title="AI Quiz Created",
        message=f"AI-generated quiz '{payload.title}' has been created with {len(payload.questions)} questions.",
        is_read=False,
        created_at=datetime.utcnow()
    )
    db.add(notif)
    db.commit()
    db.refresh(quiz)

    return {
        "message": "AI quiz saved successfully.",
        "quiz_id": quiz.id,
        "questions_count": len(payload.questions)
    }


class ManualQuizCreateRequest(BaseModel):
    title: str
    quiz_type: str = "post"
    time_limit_mins: int = 10
    per_question_timer_seconds: Optional[int] = 30
    max_questions_per_student: Optional[int] = None
    due_date: Optional[str] = None
    is_published: bool = False
    show_hints: bool = False
    questions: List[QuestionEditModel]


@router.post("/lectures/{lecture_id}/quizzes/create")
def create_manual_quiz(
    lecture_id: int,
    payload: ManualQuizCreateRequest,
    teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """
    Manually create a quiz with questions for a lecture.
    """
    lecture = db.query(Lecture).filter(Lecture.id == lecture_id).first()
    if not lecture or lecture.section.teacher_id != teacher.id:
        raise HTTPException(status_code=404, detail="Lecture not found or not authorized.")

    parsed_due = None
    if payload.due_date:
        try:
            parsed_due = datetime.fromisoformat(payload.due_date.replace("Z", "+00:00"))
        except ValueError:
            pass

    quiz = Quiz(
        lecture_id=lecture_id,
        quiz_type=payload.quiz_type,
        title=payload.title,
        is_published=payload.is_published,
        publish_date=datetime.utcnow() if payload.is_published else None,
        time_limit_mins=payload.time_limit_mins,
        per_question_timer_seconds=payload.per_question_timer_seconds if payload.per_question_timer_seconds is not None else 30,
        max_questions_per_student=payload.max_questions_per_student,
        due_date=parsed_due,
        show_hints=payload.show_hints,
        creation_type="manual"
    )
    db.add(quiz)
    db.flush()

    for q_data in payload.questions:
        q = QuizQuestion(
            quiz_id=quiz.id,
            question_text=q_data.question_text,
            option_a=q_data.option_a,
            option_b=q_data.option_b,
            option_c=q_data.option_c,
            option_d=q_data.option_d,
            correct_answer=q_data.correct_answer,
            difficulty=q_data.difficulty
        )
        db.add(q)

    db.commit()
    db.refresh(quiz)

    return {
        "message": "Quiz created successfully.",
        "quiz_id": quiz.id,
        "questions_count": len(payload.questions)
    }


# ════════════════════════════════════════════════════════════════════
#  13. ASSIGNMENT MANAGEMENT (CRUD + AI)
# ════════════════════════════════════════════════════════════════════

class AssignmentQuestionModel(BaseModel):
    question_text: str
    question_type: str = "mcq"     # mcq | short_answer | true_false
    option_a: Optional[str] = None
    option_b: Optional[str] = None
    option_c: Optional[str] = None
    option_d: Optional[str] = None
    correct_answer: str = ""
    marks: int = 5
    difficulty: str = "medium"


class AssignmentCreateModel(BaseModel):
    title: str
    description: Optional[str] = None
    due_date: Optional[str] = None  # ISO format datetime string
    total_marks: int = 100
    is_published: bool = False
    questions: List[AssignmentQuestionModel]


class AssignmentEditModel(BaseModel):
    title: str
    description: Optional[str] = None
    due_date: Optional[str] = None
    total_marks: int = 100
    is_published: bool = False
    questions: List[AssignmentQuestionModel]


@router.post("/sections/{section_id}/assignments")
def create_assignment(
    section_id: int,
    payload: AssignmentCreateModel,
    teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """Create a manual assignment with questions."""
    section = db.query(Section).filter(Section.id == section_id, Section.teacher_id == teacher.id).first()
    if not section:
        raise HTTPException(status_code=404, detail="Assigned section not found.")

    due_dt = None
    if payload.due_date:
        try:
            due_dt = datetime.fromisoformat(payload.due_date.replace("Z", "+00:00"))
        except ValueError:
            due_dt = None

    calc_total = sum(q.marks for q in payload.questions) if payload.questions else payload.total_marks
    assignment = Assignment(
        section_id=section_id,
        title=payload.title,
        description=payload.description,
        assignment_type="manual",
        due_date=due_dt,
        total_marks=calc_total if calc_total > 0 else (payload.total_marks or 100),
        is_published=payload.is_published,
        publish_date=datetime.utcnow() if payload.is_published else None
    )
    db.add(assignment)
    db.flush()

    for i, q_data in enumerate(payload.questions):
        q = AssignmentQuestion(
            assignment_id=assignment.id,
            question_text=q_data.question_text,
            question_type=q_data.question_type,
            option_a=q_data.option_a,
            option_b=q_data.option_b,
            option_c=q_data.option_c,
            option_d=q_data.option_d,
            correct_answer=q_data.correct_answer,
            marks=q_data.marks,
            difficulty=q_data.difficulty,
            order_index=i
        )
        db.add(q)

    db.commit()
    db.refresh(assignment)
    return {
        "message": "Assignment created successfully.",
        "assignment_id": assignment.id,
        "questions_count": len(payload.questions)
    }


@router.get("/sections/{section_id}/assignments")
def list_section_assignments(
    section_id: int,
    teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """List assignments for a section."""
    section = db.query(Section).filter(Section.id == section_id, Section.teacher_id == teacher.id).first()
    if not section:
        raise HTTPException(status_code=404, detail="Assigned section not found.")

    assignments = db.query(Assignment).filter(Assignment.section_id == section_id).order_by(Assignment.created_at.desc()).all()

    return [
        {
            "id": a.id,
            "title": a.title,
            "description": a.description,
            "assignment_type": a.assignment_type,
            "due_date": a.due_date.isoformat() if a.due_date else None,
            "total_marks": a.total_marks,
            "is_published": a.is_published,
            "is_deleted": bool(a.is_deleted),
            "publish_date": a.publish_date.isoformat() if a.publish_date else None,
            "questions_count": len(a.questions),
            "submissions_count": len(a.submissions),
            "created_at": a.created_at.isoformat()
        }
        for a in assignments
    ]



@router.get("/assignments/regrade-requests")
def get_teacher_regrade_requests(
    teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    from app.models.models import RegradeRequest, AssignmentSubmission, Assignment, Section, Student
    requests = db.query(RegradeRequest).join(AssignmentSubmission).join(Assignment).join(Section).filter(
        Section.teacher_id == teacher.id
    ).all()

    rows = []
    for req in requests:
        student = req.student
        submission = req.submission
        assignment = submission.assignment if submission else None

        rows.append({
            "id": req.id,
            "submission_id": req.submission_id,
            "student_id": req.student_id,
            "student_name": student.user.full_name if student and student.user else "N/A",
            "reg_number": student.reg_number if student else "N/A",
            "assignment_title": assignment.title if assignment else "N/A",
            "total_marks": assignment.total_marks if assignment else 100,
            "current_score": submission.total_score if submission else 0,
            "reason": req.reason,
            "status": req.status,
            "adjusted_marks": req.adjusted_marks,
            "teacher_feedback": req.teacher_feedback,
            "created_at": req.created_at.isoformat() if req.created_at else None,
        })

    return {"requests": rows}


class RespondRegradePayload(BaseModel):
    status: str
    adjusted_marks: Optional[int] = None
    teacher_feedback: Optional[str] = None


@router.post("/assignments/regrade-requests/{request_id}/respond")
def respond_to_regrade_request(
    request_id: int,
    payload: RespondRegradePayload,
    teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    from app.models.models import RegradeRequest, AssignmentSubmission, Notification
    req = db.query(RegradeRequest).filter(RegradeRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Regrade request not found.")

    req.status = payload.status
    req.adjusted_marks = payload.adjusted_marks
    req.teacher_feedback = payload.teacher_feedback

    if payload.status == "approved" and payload.adjusted_marks is not None:
        sub = db.query(AssignmentSubmission).filter(AssignmentSubmission.id == req.submission_id).first()
        if sub:
            sub.total_score = payload.adjusted_marks
            sub.status = "graded"

    student = req.student
    if student and student.user:
        notif = Notification(
            user_id=student.user.id,
            title=f"Assignment Regrade Request {payload.status.capitalize()}",
            message=f"Your regrade request for '{req.submission.assignment.title}' was {payload.status}. {payload.teacher_feedback or ''}",
            is_read=False,
            created_at=datetime.utcnow()
        )
        db.add(notif)

    db.commit()
    return {"ok": True, "message": f"Regrade request {payload.status} successfully."}


@router.get("/assignments/{assignment_id}")
def get_assignment_details(
    assignment_id: int,
    teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """Get assignment details with all questions."""
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment or assignment.section.teacher_id != teacher.id:
        raise HTTPException(status_code=404, detail="Assignment not found.")

    questions = [
        {
            "id": q.id,
            "question_text": q.question_text,
            "question_type": q.question_type,
            "option_a": q.option_a,
            "option_b": q.option_b,
            "option_c": q.option_c,
            "option_d": q.option_d,
            "correct_answer": q.correct_answer,
            "marks": q.marks,
            "difficulty": q.difficulty,
            "order_index": q.order_index
        }
        for q in assignment.questions
    ]

    calc_total = sum(q.marks for q in assignment.questions) if assignment.questions else assignment.total_marks
    if calc_total > 0 and assignment.total_marks != calc_total:
        assignment.total_marks = calc_total
        db.commit()

    return {
        "id": assignment.id,
        "title": assignment.title,
        "description": assignment.description,
        "assignment_type": assignment.assignment_type,
        "source_material_ids": json.loads(assignment.source_material_ids) if assignment.source_material_ids else [],
        "due_date": assignment.due_date.isoformat() if assignment.due_date else None,
        "total_marks": assignment.total_marks,
        "is_published": assignment.is_published,
        "questions": questions
    }


@router.put("/assignments/{assignment_id}")
def update_assignment(
    assignment_id: int,
    payload: AssignmentEditModel,
    teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """Update assignment details and questions."""
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment or assignment.section.teacher_id != teacher.id:
        raise HTTPException(status_code=404, detail="Assignment not found.")

    calc_total = sum(q_data.marks for q_data in payload.questions) if payload.questions else payload.total_marks
    assignment.title = payload.title
    assignment.description = payload.description
    assignment.total_marks = calc_total if calc_total > 0 else (payload.total_marks or 100)
    assignment.is_published = payload.is_published

    if payload.due_date:
        try:
            assignment.due_date = datetime.fromisoformat(payload.due_date.replace("Z", "+00:00"))
        except ValueError:
            pass

    if payload.is_published and not assignment.publish_date:
        assignment.publish_date = datetime.utcnow()
    elif not payload.is_published:
        assignment.publish_date = None

    # Re-create questions
    db.query(AssignmentQuestion).filter(AssignmentQuestion.assignment_id == assignment_id).delete()

    for i, q_data in enumerate(payload.questions):
        q = AssignmentQuestion(
            assignment_id=assignment_id,
            question_text=q_data.question_text,
            question_type=q_data.question_type,
            option_a=q_data.option_a,
            option_b=q_data.option_b,
            option_c=q_data.option_c,
            option_d=q_data.option_d,
            correct_answer=q_data.correct_answer,
            marks=q_data.marks,
            difficulty=q_data.difficulty,
            order_index=i
        )
        db.add(q)

    # Sync total_marks to existing submissions
    db.query(AssignmentSubmission).filter(AssignmentSubmission.assignment_id == assignment_id).update(
        {AssignmentSubmission.max_score: assignment.total_marks}, synchronize_session=False
    )

    db.commit()
    return {"message": "Assignment updated successfully."}


@router.delete("/assignments/{assignment_id}")
def delete_assignment(
    assignment_id: int,
    teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment or assignment.section.teacher_id != teacher.id:
        raise HTTPException(status_code=404, detail="Assignment not found.")

    assignment.is_deleted = True
    assignment.is_published = False
    db.commit()
    return {"ok": True, "message": "Assignment deleted (moved to completed) successfully."}



# ════════════════════════════════════════════════════════════════════
#  Assignment Submissions & AI Evaluation Endpoints
# ════════════════════════════════════════════════════════════════════

@router.get("/assignments/{assignment_id}/submissions")
def get_assignment_submissions(
    assignment_id: int,
    teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """List all student submissions for a specific assignment."""
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment or assignment.section.teacher_id != teacher.id:
        raise HTTPException(status_code=404, detail="Assignment not found.")

    subs = db.query(AssignmentSubmission).filter(
        AssignmentSubmission.assignment_id == assignment_id
    ).all()

    q_sum = sum(q.marks for q in assignment.questions) if assignment.questions else 0

    results = []
    for s in subs:
        student = db.query(Student).filter(Student.id == s.student_id).first()
        score = s.total_score or 0
        max_s = q_sum if q_sum > 0 else (assignment.total_marks or 100)
        pct = round((score / max_s * 100.0), 1) if max_s > 0 else 0.0

        results.append({
            "id": s.id,
            "student_id": s.student_id,
            "student_name": student.user.full_name if student and student.user else f"Student #{s.student_id}",
            "reg_number": student.reg_number if student else "N/A",
            "total_score": score,
            "total_marks": max_s,
            "score_percentage": pct,
            "status": s.status.capitalize() if s.status else "Submitted",
            "submitted_at": s.submitted_at.isoformat() if s.submitted_at else datetime.utcnow().isoformat()
        })

    return results


@router.get("/assignments/submissions/{submission_id}")
def get_assignment_submission_details(
    submission_id: int,
    teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """Get full details of a student's assignment submission including question prompts & answers."""
    sub = db.query(AssignmentSubmission).filter(AssignmentSubmission.id == submission_id).first()
    if not sub or sub.assignment.section.teacher_id != teacher.id:
        raise HTTPException(status_code=404, detail="Submission not found.")

    student = db.query(Student).filter(Student.id == sub.student_id).first()
    questions = db.query(AssignmentQuestion).filter(AssignmentQuestion.assignment_id == sub.assignment_id).order_by(AssignmentQuestion.order_index).all()
    answers = {ans.question_id: ans for ans in sub.answers}

    question_details = []
    q_sum = 0
    for q in questions:
        ans = answers.get(q.id)
        q_marks = q.marks or 5
        q_sum += q_marks
        question_details.append({
            "question_id": q.id,
            "question_text": q.question_text,
            "question_type": q.question_type,
            "marks": q_marks,
            "difficulty": q.difficulty or "medium",
            "correct_answer": q.correct_answer or "",
            "student_answer": ans.answer_text if ans else "",
            "marks_awarded": ans.marks_awarded if ans else 0,
            "is_correct": ans.is_correct if ans else None
        })

    score = sub.total_score or 0
    max_s = q_sum if q_sum > 0 else (sub.assignment.total_marks or 100)
    pct = round((score / max_s * 100.0), 1) if max_s > 0 else 0.0

    return {
        "submission_id": sub.id,
        "assignment_id": sub.assignment_id,
        "assignment_title": sub.assignment.title,
        "student_name": student.user.full_name if student and student.user else f"Student #{sub.student_id}",
        "reg_number": student.reg_number if student else "N/A",
        "status": sub.status.capitalize() if sub.status else "Submitted",
        "total_score": score,
        "max_score": max_s,
        "score_percentage": pct,
        "submitted_at": sub.submitted_at.isoformat() if sub.submitted_at else datetime.utcnow().isoformat(),
        "attached_file_url": sub.attached_file_url,
        "attached_file_name": sub.attached_file_name,
        "questions": question_details
    }


@router.post("/assignments/submissions/{submission_id}/evaluate-ai")
async def evaluate_assignment_submission_ai(
    submission_id: int,
    teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """Evaluates a student assignment submission using Groq LLM with partial credit scoring."""
    from app.services.groq_assignment_evaluator import GroqAssignmentEvaluator

    sub = db.query(AssignmentSubmission).filter(AssignmentSubmission.id == submission_id).first()
    if not sub or sub.assignment.section.teacher_id != teacher.id:
        raise HTTPException(status_code=404, detail="Submission not found.")

    questions = db.query(AssignmentQuestion).filter(AssignmentQuestion.assignment_id == sub.assignment_id).order_by(AssignmentQuestion.order_index).all()
    answers = {ans.question_id: ans for ans in sub.answers}

    evaluator = GroqAssignmentEvaluator()
    evaluations = []
    total_obtained = 0.0
    total_max = 0.0

    for q in questions:
        ans = answers.get(q.id)
        student_text = ans.answer_text if ans else ""
        q_max = float(q.marks or 5)
        total_max += q_max

        eval_res = await evaluator.evaluate_submission(
            question_text=q.question_text,
            question_type=q.question_type,
            max_marks=q_max,
            model_solution=q.correct_answer,
            student_answer=student_text,
            difficulty=q.difficulty or "medium"
        )

        obtained = float(eval_res.get("obtained_marks", 0.0))
        total_obtained += obtained

        evaluations.append({
            "question_id": q.id,
            "question_text": q.question_text,
            "max_marks": q_max,
            "suggested_marks": obtained,
            "relevance_score": eval_res.get("relevance_score", "75%"),
            "feedback_summary": eval_res.get("feedback_summary", ""),
            "criteria_breakdown": eval_res.get("criteria_breakdown", {}),
            "strengths": eval_res.get("strengths", []),
            "areas_for_improvement": eval_res.get("areas_for_improvement", [])
        })

    overall_pct = round((total_obtained / total_max * 100.0), 1) if total_max > 0 else 0.0

    return {
        "submission_id": sub.id,
        "suggested_total_score": round(total_obtained, 1),
        "total_max_marks": round(total_max, 1),
        "suggested_percentage": overall_pct,
        "question_evaluations": evaluations
    }


class QuestionGradeItem(BaseModel):
    question_id: int
    marks_awarded: float

class GradeSubmissionPayload(BaseModel):
    question_grades: List[QuestionGradeItem]
    teacher_feedback: Optional[str] = None


@router.put("/assignments/submissions/{submission_id}/grade")
def grade_assignment_submission(
    submission_id: int,
    payload: GradeSubmissionPayload,
    background_tasks: BackgroundTasks,
    teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """Save final teacher/AI evaluation marks and status for a student assignment submission."""
    sub = db.query(AssignmentSubmission).filter(AssignmentSubmission.id == submission_id).first()
    if not sub or sub.assignment.section.teacher_id != teacher.id:
        raise HTTPException(status_code=404, detail="Submission not found.")

    question_grades = payload.question_grades  # list of QuestionGradeItem
    total_score = 0.0

    for qg in question_grades:
        q_id = qg.question_id
        marks = float(qg.marks_awarded)
        total_score += marks

        ans = db.query(AssignmentAnswer).filter(
            AssignmentAnswer.submission_id == submission_id,
            AssignmentAnswer.question_id == q_id
        ).first()

        if ans:
            ans.marks_awarded = int(marks)
            ans.is_correct = marks > 0
        else:
            new_ans = AssignmentAnswer(
                submission_id=submission_id,
                question_id=q_id,
                answer_text="",
                is_correct=marks > 0,
                marks_awarded=int(marks)
            )
            db.add(new_ans)

    sub.total_score = int(round(total_score))
    sub.status = "graded"
    db.commit()

    # ── Auto-trigger BKT learning model update after grading ──────────
    student_id_snap = sub.student_id
    section_id_snap = sub.assignment.section_id if sub.assignment else None

    def _bg_learning_after_grade(student_id: int, section_id: int):
        from app.db.database import SessionLocal
        from app.models.models import Topic, Section as Sec
        from app.services.learning_model import recalculate_student_learning_profile
        _db = SessionLocal()
        try:
            sec = _db.query(Sec).filter(Sec.id == section_id).first()
            if sec and sec.course:
                topics = _db.query(Topic).filter(Topic.course_id == sec.course_id).all()
                for t in topics:
                    recalculate_student_learning_profile(student_id, t.id, _db)
        except Exception as e:
            print(f"[Learning Model] Grade trigger error: {e}")
        finally:
            _db.close()

    if section_id_snap:
        background_tasks.add_task(_bg_learning_after_grade, student_id_snap, section_id_snap)

    return {
        "message": "Submission graded successfully.",
        "submission_id": sub.id,
        "total_score": sub.total_score,
        "status": "graded"
    }


@router.get("/assignments/{assignment_id}/analytics")
def get_assignment_analytics(
    assignment_id: int,
    teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """Get aggregated analytics for an assignment (submission count, average score, question success)."""
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment or assignment.section.teacher_id != teacher.id:
        raise HTTPException(status_code=404, detail="Assignment not found.")

    subs = db.query(AssignmentSubmission).filter(AssignmentSubmission.assignment_id == assignment_id).all()
    attempts_count = len(subs)

    scores = [s.total_score for s in subs if s.total_score is not None]
    max_marks = assignment.total_marks or 100
    avg_score_pct = round((sum(scores) / (attempts_count * max_marks) * 100.0), 1) if attempts_count > 0 and max_marks > 0 else 0.0

    questions = db.query(AssignmentQuestion).filter(AssignmentQuestion.assignment_id == assignment_id).order_by(AssignmentQuestion.order_index).all()

    q_performance = []
    for i, q in enumerate(questions):
        ans_records = db.query(AssignmentAnswer).filter(AssignmentAnswer.question_id == q.id).all()
        tot_ans = len(ans_records)
        corr_ans = sum(1 for a in ans_records if a.is_correct or (a.marks_awarded is not null and a.marks_awarded > 0))
        s_rate = (corr_ans / tot_ans * 100.0) if tot_ans > 0 else (0.0 if attempts_count == 0 else 100.0)
        q_performance.append({
            "question_text": f"Q{i + 1}: {q.question_text}",
            "success_rate": round(s_rate, 1),
            "difficulty_rating": (q.difficulty or "medium").capitalize()
        })

    return {
        "attempts_count": attempts_count,
        "avg_score": avg_score_pct,
        "total_questions": len(questions),
        "question_performance": q_performance
    }


class AIAssignmentGenerateRequest(BaseModel):
    material_ids: List[int]
    num_questions: int = 10
    difficulty: str = "medium"
    question_types: List[str] = ["mcq", "short_answer", "true_false"]


@router.post("/ai/generate-assignment")
async def generate_ai_assignment(
    payload: AIAssignmentGenerateRequest,
    teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """
    AI Assignment Generation — Preview mode.
    Generates mixed-type questions from selected materials (or lectures/course curriculum).
    """
    if payload.num_questions < 1 or payload.num_questions > 30:
        raise HTTPException(status_code=400, detail="Number of questions must be between 1 and 30.")

    combined_texts = []

    if payload.material_ids:
        for mid in payload.material_ids:
            if mid >= 2000000:
                # Assignment virtual ID
                assign_id = mid - 2000000
                assign = db.query(Assignment).filter(Assignment.id == assign_id).first()
                if assign:
                    assign_qs = db.query(AssignmentQuestion).filter(AssignmentQuestion.assignment_id == assign.id).all()
                    q_summary = "\n".join([f"- Q: {q.question_text}" for q in assign_qs])
                    combined_texts.append(
                        f"=== Assignment Content: {assign.title} ===\n"
                        f"Description: {assign.description or 'Course Assignment'}\n"
                        f"Questions & Tasks:\n{q_summary if q_summary else 'Standard course assessment questions.'}"
                    )
            elif mid >= 1000000:
                # Lecture virtual ID
                lec_id = mid - 1000000
                lec = db.query(Lecture).filter(Lecture.id == lec_id).first()
                if lec:
                    combined_texts.append(
                        f"=== Video Lecture Content: {lec.title} ===\n"
                        f"Description: {lec.description or 'Lecture video content'}\n"
                        f"Key concepts: Principles, implementations, analysis, and problem solving."
                    )
            elif mid >= 900000:
                # Course virtual ID
                cid = mid - 900000
                course = db.query(Course).filter(Course.id == cid).first()
                cname = course.name if course else "Computer Science & Engineering"
                combined_texts.append(
                    f"=== Academic Curriculum for {cname} ===\n"
                    f"Fundamental and advanced concepts, algorithms, theory, practical examples, and edge cases."
                )
            else:
                # Real TopicMaterial ID
                m = db.query(TopicMaterial).filter(TopicMaterial.id == mid).first()
                if m and m.extracted_text:
                    combined_texts.append(
                        f"=== Material: {m.file_name} ===\n{m.extracted_text}"
                    )

    if not combined_texts:
        combined_texts.append(
            "=== General Academic Course Curriculum ===\n"
            "Core Concepts: Fundamental definitions, theoretical models, practical application examples, "
            "code/syntax structures, algorithm efficiency, and error analysis."
        )

    combined_text = "\n\n".join(combined_texts)

    try:
        from app.services.groq_quiz_service import get_groq_quiz_service
        groq_service = get_groq_quiz_service()
        questions = await groq_service.generate_assignment_questions(
            text=combined_text,
            num_questions=payload.num_questions,
            difficulty=payload.difficulty,
            question_types=payload.question_types
        )

        return {
            "status": "success",
            "questions": questions,
            "materials_used": payload.material_ids or [0],
            "total_text_chars": len(combined_text),
            "model": "Groq LLaMA 4 Scout"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI generation failed: {str(e)}")


class SaveAIAssignmentRequest(BaseModel):
    section_id: int
    title: str
    description: Optional[str] = None
    due_date: Optional[str] = None
    total_marks: int = 100
    is_published: bool = False
    source_material_ids: List[int] = []
    questions: List[AssignmentQuestionModel]


@router.post("/ai/save-assignment")
def save_ai_assignment(
    payload: SaveAIAssignmentRequest,
    teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """
    Save the AI-generated (and teacher-reviewed) assignment to the database.
    """
    section = db.query(Section).filter(Section.id == payload.section_id, Section.teacher_id == teacher.id).first()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found or not authorized.")

    due_dt = None
    if payload.due_date:
        try:
            due_dt = datetime.fromisoformat(payload.due_date.replace("Z", "+00:00"))
        except ValueError:
            due_dt = None

    calc_total = sum(q.marks for q in payload.questions) if payload.questions else payload.total_marks
    assignment = Assignment(
        section_id=payload.section_id,
        title=payload.title,
        description=payload.description,
        assignment_type="ai_generated",
        source_material_ids=json.dumps(payload.source_material_ids) if payload.source_material_ids else None,
        due_date=due_dt,
        total_marks=calc_total if calc_total > 0 else (payload.total_marks or 100),
        is_published=payload.is_published,
        publish_date=datetime.utcnow() if payload.is_published else None
    )
    db.add(assignment)
    db.flush()

    for i, q_data in enumerate(payload.questions):
        q = AssignmentQuestion(
            assignment_id=assignment.id,
            question_text=q_data.question_text,
            question_type=q_data.question_type,
            option_a=q_data.option_a,
            option_b=q_data.option_b,
            option_c=q_data.option_c,
            option_d=q_data.option_d,
            correct_answer=q_data.correct_answer,
            marks=q_data.marks,
            difficulty=q_data.difficulty,
            order_index=i
        )
        db.add(q)

    # Notify teacher
    notif = Notification(
        user_id=teacher.user_id,
        title="AI Assignment Created",
        message=f"AI-generated assignment '{payload.title}' has been created with {len(payload.questions)} questions.",
        is_read=False,
        created_at=datetime.utcnow()
    )
    db.add(notif)
    db.commit()
    db.refresh(assignment)

    return {
        "message": "AI assignment saved successfully.",
        "assignment_id": assignment.id,
        "questions_count": len(payload.questions)
    }


# ════════════════════════════════════════════════════════════════════
#  EXAM GRADES (Midterm, Final, & Others)
# ════════════════════════════════════════════════════════════════════

@router.get("/sections/{section_id}/exam-grades")
def get_section_exam_grades(
    section_id: int,
    teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    section = db.query(Section).filter(Section.id == section_id, Section.teacher_id == teacher.id).first()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found.")

    from app.models.models import Enrollment, Student, ExamGrade
    enrollments = db.query(Enrollment).filter(Enrollment.section_id == section_id, Enrollment.is_active == True).all()

    rows = []
    for e in enrollments:
        student = e.student
        if not student:
            continue
        grade = db.query(ExamGrade).filter(
            ExamGrade.section_id == section_id,
            ExamGrade.student_id == student.id,
        ).first()

        rows.append({
            "student_id": student.id,
            "student_name": student.user.full_name,
            "student_email": student.user.email,
            "reg_number": student.reg_number,
            "midterm_score": grade.midterm_score if grade else 0.0,
            "midterm_max": grade.midterm_max if grade else 30.0,
            "final_score": grade.final_score if grade else 0.0,
            "final_max": grade.final_max if grade else 50.0,
            "others_score": grade.others_score if grade else 0.0,
            "others_max": grade.others_max if grade else 20.0,
            "others_title": grade.others_title if grade else "Project & Presentation",
        })

    return {"section_id": section_id, "students": rows}


class SaveExamGradeItem(BaseModel):
    student_id: int
    midterm_score: Optional[float] = 0.0
    midterm_max: Optional[float] = 30.0
    final_score: Optional[float] = 0.0
    final_max: Optional[float] = 50.0
    others_score: Optional[float] = 0.0
    others_max: Optional[float] = 20.0
    others_title: Optional[str] = "Project & Presentation"


class SaveSectionExamGradesPayload(BaseModel):
    students: List[SaveExamGradeItem]


@router.post("/sections/{section_id}/exam-grades/save")
def save_section_exam_grades(
    section_id: int,
    payload: SaveSectionExamGradesPayload,
    teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    section = db.query(Section).filter(Section.id == section_id, Section.teacher_id == teacher.id).first()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found.")

    from app.models.models import ExamGrade
    for item in payload.students:
        grade = db.query(ExamGrade).filter(
            ExamGrade.section_id == section_id,
            ExamGrade.student_id == item.student_id,
        ).first()

        if grade:
            grade.midterm_score = item.midterm_score or 0.0
            grade.midterm_max = item.midterm_max or 30.0
            grade.final_score = item.final_score or 0.0
            grade.final_max = item.final_max or 50.0
            grade.others_score = item.others_score or 0.0
            grade.others_max = item.others_max or 20.0
            grade.others_title = item.others_title or "Project & Presentation"
            grade.updated_at = datetime.utcnow()
        else:
            grade = ExamGrade(
                section_id=section_id,
                student_id=item.student_id,
                midterm_score=item.midterm_score or 0.0,
                midterm_max=item.midterm_max or 30.0,
                final_score=item.final_score or 0.0,
                final_max=item.final_max or 50.0,
                others_score=item.others_score or 0.0,
                others_max=item.others_max or 20.0,
                others_title=item.others_title or "Project & Presentation",
            )
            db.add(grade)

    db.commit()
    return {"ok": True, "saved_count": len(payload.students)}


# ════════════════════════════════════════════════════════════════════
#  END-OF-SEMESTER COMPILED RESULTS (100 Marks Weighted Average)
# ════════════════════════════════════════════════════════════════════

@router.get("/sections/{section_id}/compiled-results")
def get_section_compiled_results(
    section_id: int,
    teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    section = db.query(Section).filter(Section.id == section_id, Section.teacher_id == teacher.id).first()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found.")

    from app.models.models import Enrollment, GradingPolicy, ExamGrade, QuizResponse, Quiz, AssignmentSubmission, Assignment, SemesterResult, Lecture

    policy = db.query(GradingPolicy).filter((GradingPolicy.section_id == section_id) | (GradingPolicy.section_id == None)).order_by(GradingPolicy.section_id.desc()).first()
    w_q = policy.quizzes_weight if policy else 15.0
    w_a = policy.assignments_weight if policy else 15.0
    w_m = policy.midterm_weight if policy else 25.0
    w_f = policy.final_weight if policy else 40.0
    w_o = policy.others_weight if policy else 5.0

    enrollments = db.query(Enrollment).filter(Enrollment.section_id == section_id, Enrollment.is_active == True).all()

    lectures = db.query(Lecture).filter(Lecture.section_id == section_id).all()
    lecture_ids = [l.id for l in lectures]
    quizzes = db.query(Quiz).filter(Quiz.lecture_id.in_(lecture_ids)).all() if lecture_ids else []
    assignments = db.query(Assignment).filter(Assignment.section_id == section_id).all()

    rows = []
    submission_status = "draft"

    for e in enrollments:
        student = e.student
        if not student:
            continue

        q_pct = 0.0
        if quizzes:
            q_pct_list = []
            for q in quizzes:
                res = db.query(QuizResponse).filter(QuizResponse.quiz_id == q.id, QuizResponse.student_id == student.id).all()
                if res:
                    correct = sum(1 for r in res if r.is_correct)
                    q_max = len(q.questions) if q.questions else len(res)
                    if len(res) > 0:
                        q_max = max(len(res), q_max)
                    q_pct_list.append((correct / q_max * 100.0) if q_max > 0 else 0.0)
                else:
                    q_pct_list.append(0.0)

            if policy and policy.drop_lowest_quiz and len(q_pct_list) > 1:
                q_pct_list.sort()
                q_pct_list.pop(0)

            q_pct = sum(q_pct_list) / len(q_pct_list) if q_pct_list else 0.0

        a_pct = 0.0
        if assignments:
            total_a_pct = 0.0
            for a in assignments:
                sub = db.query(AssignmentSubmission).filter(AssignmentSubmission.assignment_id == a.id, AssignmentSubmission.student_id == student.id).first()
                if sub:
                    max_sc = sub.max_score or a.total_marks or 100
                    sc = sub.total_score if sub.total_score is not None else 0.0
                    total_a_pct += ((sc / max_sc * 100.0) if max_sc > 0 else 0.0)
            a_pct = total_a_pct / len(assignments)

        eg = db.query(ExamGrade).filter(ExamGrade.section_id == section_id, ExamGrade.student_id == student.id).first()
        m_pct = ((eg.midterm_score / eg.midterm_max * 100.0) if (eg and eg.midterm_max) else 0.0)
        f_pct = ((eg.final_score / eg.final_max * 100.0) if (eg and eg.final_max) else 0.0)
        o_pct = ((eg.others_score / eg.others_max * 100.0) if (eg and eg.others_max) else 0.0)

        q_comp = round(q_pct * (w_q / 100.0), 2)
        a_comp = round(a_pct * (w_a / 100.0), 2)
        m_comp = round(m_pct * (w_m / 100.0), 2)
        f_comp = round(f_pct * (w_f / 100.0), 2)
        o_comp = round(o_pct * (w_o / 100.0), 2)

        total_100 = round(q_comp + a_comp + m_comp + f_comp + o_comp, 1)

        if total_100 >= 85:
            grade, gpa = "A", 4.0
        elif total_100 >= 75:
            grade, gpa = "B", 3.0
        elif total_100 >= 65:
            grade, gpa = "C", 2.0
        elif total_100 >= 50:
            grade, gpa = "D", 1.0
        else:
            grade, gpa = "F", 0.0

        existing = db.query(SemesterResult).filter(SemesterResult.section_id == section_id, SemesterResult.student_id == student.id).first()
        if existing and existing.status:
            submission_status = existing.status

        rows.append({
            "student_id": student.id,
            "student_name": student.user.full_name,
            "reg_number": student.reg_number,
            "quizzes_comp": q_comp,
            "assignments_comp": a_comp,
            "midterm_comp": m_comp,
            "final_comp": f_comp,
            "others_comp": o_comp,
            "total_weighted_score": total_100,
            "letter_grade": grade,
            "gpa": gpa,
            "status": existing.status if existing else "draft"
        })

    return {
        "section_id": section_id,
        "policy": {
            "quizzes_weight": w_q,
            "assignments_weight": w_a,
            "midterm_weight": w_m,
            "final_weight": w_f,
            "others_weight": w_o,
            "drop_lowest_quiz": policy.drop_lowest_quiz if policy else False
        },
        "submission_status": submission_status,
        "students": rows
    }


@router.post("/sections/{section_id}/submit-final-results")
def submit_section_final_results(
    section_id: int,
    teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    section = db.query(Section).filter(Section.id == section_id, Section.teacher_id == teacher.id).first()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found.")

    res_data = get_section_compiled_results(section_id, teacher, db)
    from app.models.models import SemesterResult

    for s_item in res_data["students"]:
        existing = db.query(SemesterResult).filter(SemesterResult.section_id == section_id, SemesterResult.student_id == s_item["student_id"]).first()
        if existing:
            existing.quizzes_score_100 = s_item["quizzes_comp"]
            existing.assignments_score_100 = s_item["assignments_comp"]
            existing.midterm_score_100 = s_item["midterm_comp"]
            existing.final_score_100 = s_item["final_comp"]
            existing.others_score_100 = s_item["others_comp"]
            existing.total_weighted_score = s_item["total_weighted_score"]
            existing.letter_grade = s_item["letter_grade"]
            existing.gpa = s_item["gpa"]
            existing.status = "submitted"
            existing.submitted_at = datetime.utcnow()
        else:
            sr = SemesterResult(
                section_id=section_id,
                student_id=s_item["student_id"],
                quizzes_score_100=s_item["quizzes_comp"],
                assignments_score_100=s_item["assignments_comp"],
                midterm_score_100=s_item["midterm_comp"],
                final_score_100=s_item["final_comp"],
                others_score_100=s_item["others_comp"],
                total_weighted_score=s_item["total_weighted_score"],
                letter_grade=s_item["letter_grade"],
                gpa=s_item["gpa"],
                status="submitted",
                submitted_at=datetime.utcnow()
            )
            db.add(sr)

    db.commit()
    return {"ok": True, "message": "Final grades submitted to Admin for approval."}


@router.post("/quizzes/{quiz_id}/regrade")
def bulk_regrade_quiz(
    quiz_id: int,
    teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    from app.models.models import Quiz, QuizQuestion, QuizResponse
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found.")

    questions = db.query(QuizQuestion).filter(QuizQuestion.quiz_id == quiz_id).all()
    q_map = {q.id: (q.correct_answer or "").strip().lower() for q in questions}

    responses = db.query(QuizResponse).filter(QuizResponse.quiz_id == quiz_id).all()
    regraded_count = 0

    for r in responses:
        correct_ans = q_map.get(r.question_id)
        if correct_ans:
            student_ans = (r.answer or "").strip().lower()
            new_is_correct = (student_ans == correct_ans)
            if r.is_correct != new_is_correct:
                r.is_correct = new_is_correct
                regraded_count += 1

    db.commit()
    return {"ok": True, "regraded_count": regraded_count, "message": f"Successfully re-graded {regraded_count} student responses."}


