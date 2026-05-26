"""
Teacher Portal API Router — Handles all teacher work cycle operations.
Runs on /api/teacher/...
"""
import os
import time
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
    Attendance, Quiz, QuizQuestion, QuizResponse, LectureSession, Announcement
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
    
    # Automatically generate 10 MCQs
    auto_generate_quiz_for_lecture(lecture.id, db, teacher.user_id)
    
    db.commit()
    db.refresh(lecture)
    return {
        "message": "Lecture uploaded and published successfully. MCQ quiz auto-generated.",
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
        result.append({
            "id": q.id,
            "title": q.title or f"{q.quiz_type.upper()} - {q.lecture.title}",
            "lecture_title": q.lecture.title,
            "section_label": q.lecture.section.section_label,
            "course_name": q.lecture.section.course.name,
            "quiz_type": q.quiz_type,
            "is_published": q.is_published,
            "publish_date": q.publish_date.isoformat() if q.publish_date else None,
            "time_limit_mins": q.time_limit_mins,
            "show_hints": q.show_hints,
            "questions_count": len(q.questions),
            "attempts_count": attempts_count
        })
    return result


class QuestionEditModel(BaseModel):
    question_text: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    correct_answer: str
    difficulty: str

class QuizEditModel(BaseModel):
    title: str
    is_published: bool
    time_limit_mins: int
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
        "show_hints": quiz.show_hints,
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
        
        # Calculate grade
        total_questions = len(quiz.questions)
        correct_answers = sum(1 for r in responses if r.is_correct)
        score = (correct_answers / total_questions * 100.0) if total_questions > 0 else 0.0
        
        # Find submission timestamp (take latest answered_at)
        sub_time = max(r.answered_at for r in responses) if responses else datetime.utcnow()
        
        submissions.append({
            "student_name": student.user.full_name,
            "reg_number": student.reg_number,
            "correct_count": correct_answers,
            "total_questions": total_questions,
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
    total_graded = sum(1 for r in responses if r.is_correct is not None)
    if total_graded > 0:
        avg_score = (correct_count / total_graded * 100)
        
    # Question difficulty analysis (percentage of wrong attempts)
    questions_stats = []
    for q in quiz.questions:
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
                
        student_analytics = {
            "student_id": student.id,
            "name": student.user.full_name,
            "reg_number": student.reg_number,
            "overall_mastery": round(mastery, 1),
            "attendance_rate": round(attendance_rate, 1),
            "avg_watch_pct": round(avg_watch_pct, 1),
            "avg_engagement": round(avg_engagement * 100.0, 1),
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

    return {
        "class_avg_mastery": round(class_avg_mastery, 1),
        "class_avg_attendance": round(class_avg_attendance, 1),
        "total_enrolled": student_count,
        "students": students_stats,
        "topic_difficulty": topic_difficulty,
        "at_risk_students": at_risk_list,
        "high_performers": high_performers_list
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
