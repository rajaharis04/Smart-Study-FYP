"""Pydantic schemas for all API requests and responses."""
from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr


# ─── AUTH ─────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    full_name: str
    must_change_password: bool = False

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

class VerifyEmailRequest(BaseModel):
    email: EmailStr

class VerifyEmailResponse(BaseModel):
    email: str
    full_name: str
    role: str
    has_password: bool
    message: str

class SendOtpRequest(BaseModel):
    email: EmailStr

class VerifyOtpRequest(BaseModel):
    email: EmailStr
    otp: str

class SetupPasswordRequest(BaseModel):
    email: EmailStr
    otp: str
    password: str


# ─── DEPARTMENT ───────────────────────────────────────────────────────────────

class DepartmentCreate(BaseModel):
    name: str
    code: str
    hod_name: str

class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    hod_name: Optional[str] = None

class DepartmentOut(BaseModel):
    id: int
    name: str
    code: str
    hod_name: str
    created_at: datetime

    class Config:
        from_attributes = True


# ─── TEACHER ──────────────────────────────────────────────────────────────────

class TeacherCreate(BaseModel):
    full_name: str
    email: EmailStr
    employee_id: str
    department_id: Optional[int] = None
    password: Optional[str] = None   # None = auto-generate

class TeacherUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    department_id: Optional[int] = None
    is_active: Optional[bool] = None

class TeacherOut(BaseModel):
    id: int
    employee_id: str
    full_name: str
    email: str
    department_name: Optional[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ─── STUDENT ──────────────────────────────────────────────────────────────────

class StudentCreate(BaseModel):
    full_name: str
    email: EmailStr
    reg_number: str
    batch: str
    department_id: Optional[int] = None

class StudentUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    batch: Optional[str] = None
    department_id: Optional[int] = None
    is_active: Optional[bool] = None

class StudentOut(BaseModel):
    id: int
    reg_number: str
    full_name: str
    email: str
    batch: str
    department_name: Optional[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class BulkStudentResult(BaseModel):
    created: int
    skipped: int
    errors: List[str]


# ─── SEMESTER ─────────────────────────────────────────────────────────────────

class SemesterCreate(BaseModel):
    name: str
    start_date: Optional[date] = None
    mid_start: Optional[date] = None
    mid_end: Optional[date] = None
    end_date: Optional[date] = None
    final_start: Optional[date] = None
    final_end: Optional[date] = None
    is_active: bool = True

class SemesterUpdate(BaseModel):
    name: Optional[str] = None
    start_date: Optional[date] = None
    mid_start: Optional[date] = None
    mid_end: Optional[date] = None
    end_date: Optional[date] = None
    final_start: Optional[date] = None
    final_end: Optional[date] = None
    is_active: Optional[bool] = None

class SemesterOut(BaseModel):
    id: int
    name: str
    start_date: Optional[date]
    mid_start: Optional[date]
    mid_end: Optional[date]
    end_date: Optional[date]
    final_start: Optional[date]
    final_end: Optional[date]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ─── COURSE ───────────────────────────────────────────────────────────────────

class CourseCreate(BaseModel):
    name: str
    code: str
    credit_hours: int = 3
    department_id: Optional[int] = None
    semester_id: Optional[int] = None

class CourseUpdate(BaseModel):
    name: Optional[str] = None
    credit_hours: Optional[int] = None
    department_id: Optional[int] = None
    semester_id: Optional[int] = None
    is_archived: Optional[bool] = None

class CourseOut(BaseModel):
    id: int
    name: str
    code: str
    credit_hours: int
    department_name: Optional[str]
    semester_name: Optional[str]
    is_archived: bool
    sections_count: int
    created_at: datetime

    class Config:
        from_attributes = True


# ─── SECTION ──────────────────────────────────────────────────────────────────

class SectionCreate(BaseModel):
    course_id: int
    section_label: str
    teacher_id: Optional[int] = None
    semester_id: Optional[int] = None
    schedule: Optional[str] = None
    room: Optional[str] = None

class SectionUpdate(BaseModel):
    teacher_id: Optional[int] = None
    section_label: Optional[str] = None
    schedule: Optional[str] = None
    room: Optional[str] = None
    semester_id: Optional[int] = None

class SectionOut(BaseModel):
    id: int
    section_label: str
    course_name: str
    course_code: str
    teacher_name: Optional[str]
    semester_name: Optional[str]
    schedule: Optional[str]
    room: Optional[str]
    enrolled_count: int
    created_at: datetime

    class Config:
        from_attributes = True


# ─── ENROLLMENT ───────────────────────────────────────────────────────────────

class EnrollmentCreate(BaseModel):
    section_id: int
    student_ids: List[int]

class EnrollmentOut(BaseModel):
    id: int
    student_name: str
    student_reg: str
    section_label: str
    course_name: str
    is_active: bool
    enrolled_at: datetime

    class Config:
        from_attributes = True

class BulkEnrollResult(BaseModel):
    enrolled: int
    skipped: int
    errors: List[str]


# ─── REPORTS ──────────────────────────────────────────────────────────────────

class AdminStats(BaseModel):
    total_departments: int
    total_teachers: int
    total_students: int
    total_courses: int
    total_sections: int
    total_enrollments: int
    active_semester: Optional[str]


# ─── PASSWORD RESET ───────────────────────────────────────────────────────────

class PasswordResetResponse(BaseModel):
    new_password: str
    message: str


# ─── GLOBAL ANNOUNCEMENTS ─────────────────────────────────────────────────────

class GlobalAnnouncementCreate(BaseModel):
    title: str
    content: str
    target_role: str = "all"  # all | teachers | students
    department_id: Optional[int] = None

class GlobalAnnouncementOut(BaseModel):
    id: int
    title: str
    content: str
    target_role: str
    department_id: Optional[int]
    department_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

