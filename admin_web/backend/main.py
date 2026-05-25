"""
SmartStudy Admin API — FastAPI main application entry point.
Runs on port 8001 (Flutter backend uses 8000).
"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.db.database import Base, engine
from app.api.auth import router as auth_router
from app.api.departments import router as dept_router
from app.api.teachers import router as teacher_router
from app.api.students import router as student_router
from app.api.dashboard import router as dashboard_router
from app.api.student_courses import router as student_courses_router
from app.api.lectures import router as lectures_router
from app.api.qa import router as qa_router
from app.api.student_portal import attendance_router, profile_router, questionbank_router
from app.api.teachers_portal import router as teachers_portal_router
from app.api.resources import (
    semesters_router,
    courses_router,
    sections_router,
    enrollments_router,
    reports_router,
    announcements_router,
)

# ── Create all tables ───────────────────────────────────────────────────────
Base.metadata.create_all(bind=engine)

# ── FastAPI app ─────────────────────────────────────────────────────────────
app = FastAPI(
    title="SmartStudy Admin API",
    description="Admin portal for managing departments, teachers, students, courses, sections, enrollments, and semesters.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── Mount static files uploads ──────────────────────────────────────────────
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# ── CORS — allow React dev server (port 5173) and production ────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Register all routers ────────────────────────────────────────────────────
API_PREFIX = "/api"
app.include_router(auth_router,           prefix=API_PREFIX)
app.include_router(dept_router,           prefix=API_PREFIX)
app.include_router(teacher_router,        prefix=API_PREFIX)
app.include_router(student_router,        prefix=API_PREFIX)
app.include_router(dashboard_router,      prefix=API_PREFIX)
app.include_router(student_courses_router,prefix=API_PREFIX)
app.include_router(lectures_router,       prefix=API_PREFIX)  # Student lectures
app.include_router(teachers_portal_router,prefix=API_PREFIX)  # Teacher portal
app.include_router(semesters_router,      prefix=API_PREFIX)
app.include_router(courses_router,        prefix=API_PREFIX)
app.include_router(sections_router,       prefix=API_PREFIX)
app.include_router(enrollments_router,    prefix=API_PREFIX)
app.include_router(reports_router,        prefix=API_PREFIX)
app.include_router(announcements_router,  prefix=API_PREFIX)
app.include_router(attendance_router,     prefix=API_PREFIX)
app.include_router(profile_router,        prefix=API_PREFIX)
app.include_router(questionbank_router,   prefix=API_PREFIX)
app.include_router(qa_router,             prefix=API_PREFIX)


@app.get("/")
def root():
    return {
        "service": "SmartStudy Admin API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {"status": "ok"}
