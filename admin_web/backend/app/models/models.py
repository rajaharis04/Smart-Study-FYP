"""
SQLAlchemy ORM Models — All database tables defined here.
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime,
    ForeignKey, Text, Float, Date
)
from sqlalchemy.orm import relationship
from app.db.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(200), nullable=False)
    email = Column(String(200), unique=True, index=True, nullable=False)
    hashed_password = Column(String(300), nullable=True)
    role = Column(String(20), nullable=False)  # admin | teacher | student
    is_active = Column(Boolean, default=True)
    must_change_password = Column(Boolean, default=True)
    otp_code = Column(String(10), nullable=True)
    otp_created_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    teacher_profile = relationship("Teacher", back_populates="user", uselist=False)
    student_profile = relationship("Student", back_populates="user", uselist=False)


class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    code = Column(String(20), unique=True, nullable=False)
    hod_name = Column(String(200), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    teachers = relationship("Teacher", back_populates="department")
    students = relationship("Student", back_populates="department")
    courses = relationship("Course", back_populates="department")
    academic_sections = relationship("AcademicSection", back_populates="department")


class Teacher(Base):
    __tablename__ = "teachers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    employee_id = Column(String(50), unique=True, nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="teacher_profile")
    department = relationship("Department", back_populates="teachers")
    sections = relationship("Section", back_populates="teacher")


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    reg_number = Column(String(50), unique=True, nullable=False)
    batch = Column(String(20), nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    academic_section_id = Column(Integer, ForeignKey("academic_sections.id"), nullable=True)
    profile_picture = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="student_profile")
    department = relationship("Department", back_populates="students")
    academic_section = relationship("AcademicSection", back_populates="students", foreign_keys="Student.academic_section_id")
    enrollments = relationship("Enrollment", back_populates="student")
    lecture_sessions = relationship("LectureSession", back_populates="student")
    attendance_records = relationship("Attendance", back_populates="student")
    quiz_responses = relationship("QuizResponse", back_populates="student")
    assignment_submissions = relationship("AssignmentSubmission", back_populates="student")



# ════════════════════════════════════════════════════════════════════
#  AcademicSection — Admin-defined class groups: Batch → Dept → Sec
#  e.g., SP23 → BCS → A   →  "SP23-BCS-A"
# ════════════════════════════════════════════════════════════════════
class AcademicSection(Base):
    __tablename__ = "academic_sections"

    id             = Column(Integer, primary_key=True, index=True)
    batch          = Column(String(20), nullable=False)    # e.g., SP23
    department_id  = Column(Integer, ForeignKey("departments.id"), nullable=False)
    section_name   = Column(String(10), nullable=False)    # e.g., A, B, C
    created_at     = Column(DateTime, default=datetime.utcnow)

    # Relationships
    department = relationship("Department", back_populates="academic_sections")
    students   = relationship("Student", back_populates="academic_section")

    @property
    def full_label(self):
        """Returns formatted label like SP23-BCS-A"""
        dept_code = self.department.code if self.department else "?"
        return f"{self.batch}-{dept_code}-{self.section_name}"


class Semester(Base):

    __tablename__ = "semesters"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)           # e.g., "Spring 2026"
    start_date = Column(Date, nullable=True)
    mid_start = Column(Date, nullable=True)
    mid_end = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    final_start = Column(Date, nullable=True)
    final_end = Column(Date, nullable=True)
    is_active = Column(Boolean, default=True)
    registration_deadline = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    courses = relationship("Course", back_populates="semester")
    sections = relationship("Section", back_populates="semester")


class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    code = Column(String(20), nullable=False)
    credit_hours = Column(Integer, default=3)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    semester_id = Column(Integer, ForeignKey("semesters.id"), nullable=True)
    is_archived = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    department = relationship("Department", back_populates="courses")
    semester = relationship("Semester", back_populates="courses")
    sections = relationship("Section", back_populates="course", cascade="all, delete-orphan")
    topics = relationship("Topic", back_populates="course", cascade="all, delete-orphan")
    student_qas = relationship("StudentQA", back_populates="course", cascade="all, delete-orphan")


class Section(Base):
    __tablename__ = "sections"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=True)
    semester_id = Column(Integer, ForeignKey("semesters.id"), nullable=True)
    academic_section_id = Column(Integer, ForeignKey("academic_sections.id", ondelete="SET NULL"), nullable=True)
    target_student_id = Column(Integer, ForeignKey("students.id", ondelete="SET NULL"), nullable=True)
    section_label = Column(String(10), nullable=False)   # A, B, C ...
    schedule = Column(String(200), nullable=True)         # "Mon/Wed 9:00-10:30 AM"
    room = Column(String(100), nullable=True)
    is_registration_open = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    course = relationship("Course", back_populates="sections")
    teacher = relationship("Teacher", back_populates="sections")
    semester = relationship("Semester", back_populates="sections")
    academic_section = relationship("AcademicSection")
    target_student = relationship("Student")
    enrollments = relationship("Enrollment", back_populates="section", cascade="all, delete-orphan")
    lectures = relationship("Lecture", back_populates="section", cascade="all, delete-orphan")
    announcements = relationship("Announcement", back_populates="section", cascade="all, delete-orphan")
    attendance_records = relationship("Attendance", back_populates="section", cascade="all, delete-orphan")
    assignments = relationship("Assignment", back_populates="section", cascade="all, delete-orphan")


class Enrollment(Base):
    __tablename__ = "enrollments"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    section_id = Column(Integer, ForeignKey("sections.id"), nullable=False)
    is_active = Column(Boolean, default=True)
    status = Column(String(20), default="ACTIVE")  # ACTIVE | PENDING | DROPPED
    enrolled_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    student = relationship("Student", back_populates="enrollments")
    section = relationship("Section", back_populates="enrollments")


# ════════════════════════════════════════════════════════════════════
#  Topic — Academic topic defined for a Course
# ════════════════════════════════════════════════════════════════════
class Topic(Base):
    __tablename__ = "topics"

    id              = Column(Integer, primary_key=True, index=True)
    course_id       = Column(Integer, ForeignKey("courses.id"), nullable=False)
    title           = Column(String(300), nullable=False)
    sequence_number = Column(Integer, default=1)
    blooms_level    = Column(String(50), default="Remember")  # Remember | Understand | Apply | Analyze
    created_at      = Column(DateTime, default=datetime.utcnow)

    # Relationships
    course              = relationship("Course", back_populates="topics")
    learning_objectives = relationship("LearningObjective", back_populates="topic", cascade="all, delete-orphan")
    materials           = relationship("TopicMaterial", back_populates="topic", cascade="all, delete-orphan")
    learning_profiles   = relationship("StudentLearningProfile", back_populates="topic", cascade="all, delete-orphan")


# ════════════════════════════════════════════════════════════════════
#  LearningObjective — Learning objectives aligned to a Topic
# ════════════════════════════════════════════════════════════════════
class LearningObjective(Base):
    __tablename__ = "learning_objectives"

    id          = Column(Integer, primary_key=True, index=True)
    topic_id    = Column(Integer, ForeignKey("topics.id"), nullable=False)
    description = Column(Text, nullable=False)
    created_at  = Column(DateTime, default=datetime.utcnow)

    # Relationships
    topic = relationship("Topic", back_populates="learning_objectives")


# ════════════════════════════════════════════════════════════════════
#  TopicMaterial — PDF/PPT material uploaded by teacher
# ════════════════════════════════════════════════════════════════════
class TopicMaterial(Base):
    __tablename__ = "topic_materials"

    id            = Column(Integer, primary_key=True, index=True)
    topic_id      = Column(Integer, ForeignKey("topics.id"), nullable=False)
    file_name     = Column(String(300), nullable=False)
    file_type     = Column(String(50), nullable=False)  # "pdf" | "ppt"
    file_path     = Column(String(1000), nullable=False)
    upload_status = Column(String(50), default="processing")  # processing | extraction_complete | ai_ready
    progress      = Column(Integer, default=0)
    extracted_text = Column(Text, nullable=True)
    created_at    = Column(DateTime, default=datetime.utcnow)

    # Relationships
    topic = relationship("Topic", back_populates="materials")


# ════════════════════════════════════════════════════════════════════
#  Notification — Teacher/Admin in-app notifications
# ════════════════════════════════════════════════════════════════════
class Notification(Base):
    __tablename__ = "notifications"

    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False)
    title      = Column(String(300), nullable=False)
    message    = Column(Text, nullable=False)
    is_read    = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


# ════════════════════════════════════════════════════════════════════
#  Lecture — Video lecture linked to a Section
# ════════════════════════════════════════════════════════════════════
class Lecture(Base):
    __tablename__ = "lectures"

    id          = Column(Integer, primary_key=True, index=True)
    section_id  = Column(Integer, ForeignKey("sections.id"), nullable=False)
    topic_id    = Column(Integer, ForeignKey("topics.id"), nullable=True)
    title       = Column(String(300), nullable=False)
    video_url   = Column(String(1000), nullable=False)   # Streaming URL
    duration    = Column(Integer, default=0)              # Seconds
    description = Column(Text, nullable=True)
    is_published = Column(Boolean, default=False)
    publish_date = Column(DateTime, nullable=True)
    created_at  = Column(DateTime, default=datetime.utcnow)

    # Relationships
    section  = relationship("Section",  back_populates="lectures")
    topic    = relationship("Topic")
    chapters = relationship("LectureChapter", back_populates="lecture",
                            cascade="all, delete-orphan", order_by="LectureChapter.start_seconds")
    sessions = relationship("LectureSession", back_populates="lecture",
                            cascade="all, delete-orphan")
    quizzes  = relationship("Quiz", back_populates="lecture",
                            cascade="all, delete-orphan")
    attendance_records = relationship("Attendance", back_populates="lecture", cascade="all, delete-orphan")


# ════════════════════════════════════════════════════════════════════
#  LectureChapter — Named timestamp markers inside a lecture video
# ════════════════════════════════════════════════════════════════════
class LectureChapter(Base):
    __tablename__ = "lecture_chapters"

    id             = Column(Integer, primary_key=True, index=True)
    lecture_id     = Column(Integer, ForeignKey("lectures.id"), nullable=False)
    title          = Column(String(200), nullable=False)
    start_seconds  = Column(Integer, nullable=False, default=0)  # Seek position
    created_at     = Column(DateTime, default=datetime.utcnow)

    # Relationships
    lecture = relationship("Lecture", back_populates="chapters")


# ════════════════════════════════════════════════════════════════════
#  LectureSession — One watching session per student per lecture
# ════════════════════════════════════════════════════════════════════
class LectureSession(Base):
    __tablename__ = "lecture_sessions"

    id               = Column(Integer, primary_key=True, index=True)
    lecture_id       = Column(Integer, ForeignKey("lectures.id"), nullable=False)
    student_id       = Column(Integer, ForeignKey("students.id"), nullable=False)
    started_at       = Column(DateTime, default=datetime.utcnow)
    ended_at         = Column(DateTime, nullable=True)
    watch_percentage = Column(Float, default=0.0)    # 0–100
    pause_count      = Column(Integer, default=0)
    playback_speed   = Column(Float, default=1.0)
    engagement_score = Column(Float, default=0.0)
    is_complete      = Column(Boolean, default=False)

    # Relationships
    lecture = relationship("Lecture",  back_populates="sessions")
    student = relationship("Student",  back_populates="lecture_sessions")


# ════════════════════════════════════════════════════════════════════
#  Attendance — Computed from LectureSession (>= 80% watch = present)
# ════════════════════════════════════════════════════════════════════
class Attendance(Base):
    __tablename__ = "attendance"

    id         = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    lecture_id = Column(Integer, ForeignKey("lectures.id"), nullable=False)
    section_id = Column(Integer, ForeignKey("sections.id"), nullable=False)
    is_present = Column(Boolean, default=False)
    marked_at  = Column(DateTime, default=datetime.utcnow)

    # Relationships
    student = relationship("Student", back_populates="attendance_records")
    lecture = relationship("Lecture", back_populates="attendance_records")
    section = relationship("Section", back_populates="attendance_records")


# ════════════════════════════════════════════════════════════════════
#  Quiz — Pre / Mid / Post quiz linked to a lecture
# ════════════════════════════════════════════════════════════════════
class Quiz(Base):
    __tablename__ = "quizzes"

    id              = Column(Integer, primary_key=True, index=True)
    lecture_id      = Column(Integer, ForeignKey("lectures.id"), nullable=False)
    quiz_type       = Column(String(10), nullable=False)  # pre | mid | post
    title           = Column(String(300), nullable=True)
    is_published    = Column(Boolean, default=False)
    publish_date    = Column(DateTime, nullable=True)
    time_limit_mins = Column(Integer, default=10, nullable=True)
    show_hints      = Column(Boolean, default=False)
    creation_type   = Column(String(20), default="manual")   # manual | ai_generated
    source_material_ids = Column(Text, nullable=True)        # JSON array of TopicMaterial IDs used by AI
    due_date        = Column(DateTime, nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow)

    # Relationships
    lecture   = relationship("Lecture",       back_populates="quizzes")
    questions = relationship("QuizQuestion",  back_populates="quiz",
                             cascade="all, delete-orphan")
    responses = relationship("QuizResponse",  back_populates="quiz",
                             cascade="all, delete-orphan")


# ════════════════════════════════════════════════════════════════════
#  QuizQuestion — MCQ question with 4 options
# ════════════════════════════════════════════════════════════════════
class QuizQuestion(Base):
    __tablename__ = "quiz_questions"

    id            = Column(Integer, primary_key=True, index=True)
    quiz_id       = Column(Integer, ForeignKey("quizzes.id"), nullable=False)
    question_text = Column(Text, nullable=False)
    option_a      = Column(String(500), nullable=False)
    option_b      = Column(String(500), nullable=False)
    option_c      = Column(String(500), nullable=False)
    option_d      = Column(String(500), nullable=False)
    correct_answer = Column(String(1), nullable=True)   # A/B/C/D (null = RAG-generated, not graded)
    difficulty    = Column(String(10), default="medium") # easy/medium/hard
    created_at    = Column(DateTime, default=datetime.utcnow)

    # Relationships
    quiz      = relationship("Quiz",         back_populates="questions")
    responses = relationship("QuizResponse", back_populates="question",
                             cascade="all, delete-orphan")


# ════════════════════════════════════════════════════════════════════
#  QuizResponse — Student's answer to one question
# ════════════════════════════════════════════════════════════════════
class QuizResponse(Base):
    __tablename__ = "quiz_responses"

    id                 = Column(Integer, primary_key=True, index=True)
    quiz_id            = Column(Integer, ForeignKey("quizzes.id"),         nullable=False)
    question_id        = Column(Integer, ForeignKey("quiz_questions.id"),  nullable=False)
    student_id         = Column(Integer, ForeignKey("students.id"),        nullable=False)
    answer             = Column(String(1), nullable=True)    # A/B/C/D — null = skipped
    is_correct         = Column(Boolean, nullable=True)      # null = diagnostic (not graded)
    time_taken_seconds = Column(Float, default=30.0)
    hint_used          = Column(Boolean, default=False)
    answered_at        = Column(DateTime, default=datetime.utcnow)

    # Relationships
    quiz     = relationship("Quiz",         back_populates="responses")
    question = relationship("QuizQuestion", back_populates="responses")
    student  = relationship("Student",      back_populates="quiz_responses")


# ════════════════════════════════════════════════════════════════════
#  Announcement — Teacher broadcasts to section
# ════════════════════════════════════════════════════════════════════
class Announcement(Base):
    __tablename__ = "announcements"

    id = Column(Integer, primary_key=True, index=True)
    section_id = Column(Integer, ForeignKey("sections.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    section = relationship("Section", back_populates="announcements")


# ════════════════════════════════════════════════════════════════════
#  GlobalAnnouncement — Admin broadcasts to department/institution
# ════════════════════════════════════════════════════════════════════
class GlobalAnnouncement(Base):
    __tablename__ = "global_announcements"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    target_role = Column(String(50), default="all")  # all | teachers | students
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    department = relationship("Department")


# ════════════════════════════════════════════════════════════════════
#  AuditLog — Administrative modifications audit trail
# ════════════════════════════════════════════════════════════════════
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_name = Column(String(200), nullable=False)
    action = Column(String(100), nullable=False)
    details = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)


# ════════════════════════════════════════════════════════════════════
#  StudentLearningProfile — Postgres storage for learning models
# ════════════════════════════════════════════════════════════════════
class StudentLearningProfile(Base):
    __tablename__ = "student_learning_profiles"

    id               = Column(Integer, primary_key=True, index=True)
    student_id       = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    topic_id         = Column(Integer, ForeignKey("topics.id", ondelete="CASCADE"), nullable=False)
    mastery_score    = Column(Float, default=0.0)      # 0.0 to 100.0
    confidence_score = Column(Float, default=0.0)      # 0.0 to 100.0
    learning_pace    = Column(Float, default=0.0)      # average seconds per question
    engagement_score = Column(Float, default=0.0)      # 0.0 to 100.0 (percentage scale)
    hint_dependency  = Column(Float, default=0.0)      # ratio of hint usage (0.0 to 1.0)
    learning_score   = Column(Float, default=0.0)      # 0.0 to 100.0
    is_weak          = Column(Boolean, default=False)
    updated_at       = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    student = relationship("Student")
    topic   = relationship("Topic", back_populates="learning_profiles")


# ════════════════════════════════════════════════════════════════════
#  StudentQA — Persistent doubt chat messages with RAG sources
# ════════════════════════════════════════════════════════════════════
class StudentQA(Base):
    __tablename__ = "student_qas"

    id         = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    course_id  = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    question   = Column(Text, nullable=False)
    answer     = Column(Text, nullable=False)
    sources    = Column(Text, nullable=True)           # pipe-separated or JSON list
    is_starred = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    student = relationship("Student")
    course  = relationship("Course", back_populates="student_qas")


# ════════════════════════════════════════════════════════════════════
#  Assignment — Teacher-created or AI-generated assignment
# ════════════════════════════════════════════════════════════════════
class Assignment(Base):
    __tablename__ = "assignments"

    id                  = Column(Integer, primary_key=True, index=True)
    section_id          = Column(Integer, ForeignKey("sections.id", ondelete="CASCADE"), nullable=False)
    title               = Column(String(300), nullable=False)
    description         = Column(Text, nullable=True)
    assignment_type     = Column(String(20), default="manual")  # manual | ai_generated
    source_material_ids = Column(Text, nullable=True)           # JSON array of TopicMaterial IDs
    due_date            = Column(DateTime, nullable=True)
    total_marks         = Column(Integer, default=100)
    is_published        = Column(Boolean, default=False)
    publish_date        = Column(DateTime, nullable=True)
    created_at          = Column(DateTime, default=datetime.utcnow)

    # Relationships
    section   = relationship("Section", back_populates="assignments")
    questions = relationship("AssignmentQuestion", back_populates="assignment",
                             cascade="all, delete-orphan", order_by="AssignmentQuestion.order_index")
    submissions = relationship("AssignmentSubmission", back_populates="assignment",
                               cascade="all, delete-orphan")


# ════════════════════════════════════════════════════════════════════
#  AssignmentQuestion — MCQ / Short Answer / True-False
# ════════════════════════════════════════════════════════════════════
class AssignmentQuestion(Base):
    __tablename__ = "assignment_questions"

    id             = Column(Integer, primary_key=True, index=True)
    assignment_id  = Column(Integer, ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False)
    question_text  = Column(Text, nullable=False)
    question_type  = Column(String(20), nullable=False, default="mcq")  # mcq | short_answer | true_false
    option_a       = Column(String(500), nullable=True)
    option_b       = Column(String(500), nullable=True)
    option_c       = Column(String(500), nullable=True)
    option_d       = Column(String(500), nullable=True)
    correct_answer = Column(Text, nullable=True)           # A/B/C/D for MCQ, text for short_answer, True/False
    marks          = Column(Integer, default=5)
    difficulty     = Column(String(10), default="medium")   # easy | medium | hard
    order_index    = Column(Integer, default=0)
    created_at     = Column(DateTime, default=datetime.utcnow)

    # Relationships
    assignment = relationship("Assignment", back_populates="questions")
    answers    = relationship("AssignmentAnswer", back_populates="question",
                              cascade="all, delete-orphan")


# ════════════════════════════════════════════════════════════════════
#  AssignmentSubmission — Student's submission for an assignment
# ════════════════════════════════════════════════════════════════════
class AssignmentSubmission(Base):
    __tablename__ = "assignment_submissions"

    id             = Column(Integer, primary_key=True, index=True)
    assignment_id  = Column(Integer, ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False)
    student_id     = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    submitted_at   = Column(DateTime, default=datetime.utcnow)
    total_score    = Column(Integer, nullable=True)
    max_score      = Column(Integer, nullable=True)
    status         = Column(String(20), default="pending")  # pending | submitted | graded

    # Relationships
    assignment = relationship("Assignment", back_populates="submissions")
    student    = relationship("Student",    back_populates="assignment_submissions")
    answers    = relationship("AssignmentAnswer", back_populates="submission",
                              cascade="all, delete-orphan")


# ════════════════════════════════════════════════════════════════════
#  AssignmentAnswer — Student's answer to one assignment question
# ════════════════════════════════════════════════════════════════════
class AssignmentAnswer(Base):
    __tablename__ = "assignment_answers"

    id              = Column(Integer, primary_key=True, index=True)
    submission_id   = Column(Integer, ForeignKey("assignment_submissions.id", ondelete="CASCADE"), nullable=False)
    question_id     = Column(Integer, ForeignKey("assignment_questions.id", ondelete="CASCADE"), nullable=False)
    answer_text     = Column(Text, nullable=True)
    is_correct      = Column(Boolean, nullable=True)
    marks_awarded   = Column(Integer, default=0)
    answered_at     = Column(DateTime, default=datetime.utcnow)

    # Relationships
    submission = relationship("AssignmentSubmission", back_populates="answers")
    question   = relationship("AssignmentQuestion",   back_populates="answers")
