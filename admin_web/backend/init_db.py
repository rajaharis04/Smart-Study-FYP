"""
Database initializer — creates tables and seeds the first admin account.
Run once: python init_db.py
"""
import sys
from datetime import datetime, date, timedelta
from app.db.database import Base, engine, SessionLocal
from app.models.models import (
    User, Department, Teacher, Student, Semester, Course, Section, Enrollment,
    Topic, LearningObjective, TopicMaterial, Lecture, Attendance, Quiz,
    QuizQuestion, QuizResponse, LectureSession, Announcement, GlobalAnnouncement, AuditLog,
    StudentLearningProfile, StudentQA, AcademicSection
)
from app.services.auth_service import hash_password
from app.core.config import settings

def init():
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tables created.")

    db = SessionLocal()
    try:
        # Seed default departments if none exist
        existing_depts = db.query(Department).count()
        if existing_depts == 0:
            print("Seeding default departments...")
            depts = [
                Department(name="Computer Science", code="CS", hod_name="Dr. Muhammad Sharif"),
                Department(name="Software Engineering", code="SE", hod_name="Dr. Nazir Ahmad"),
                Department(name="Electrical Engineering", code="EE", hod_name="Dr. Khalid Mahmood"),
            ]
            db.add_all(depts)
            db.commit()
            print("✅ Default departments seeded (CS, SE, EE).")

        # Seed Semester
        active_semester = db.query(Semester).filter(Semester.is_active == True).first()
        if not active_semester:
            print("Seeding active semester...")
            active_semester = Semester(
                name="Spring 2026",
                start_date=date.today() - timedelta(weeks=10),
                end_date=date.today() + timedelta(weeks=6),
                is_active=True
            )
            db.add(active_semester)
            db.commit()
            db.refresh(active_semester)

        # Seed admin
        existing_admin = db.query(User).filter(User.email == settings.ADMIN_EMAIL).first()
        if not existing_admin:
            admin = User(
                full_name="System Administrator",
                email=settings.ADMIN_EMAIL,
                hashed_password=hash_password(settings.ADMIN_PASSWORD),
                role="admin",
                is_active=True,
                must_change_password=False,
            )
            db.add(admin)
            db.commit()
            print(f"✅ Admin account created: {settings.ADMIN_EMAIL}")

        # Seed Audit Logs
        existing_audit_logs = db.query(AuditLog).count()
        if existing_audit_logs == 0:
            print("Seeding audit logs...")
            log1 = AuditLog(
                user_name="admin@smartstudy.edu",
                action="SYSTEM_INIT",
                details="System initialized successfully. Default departments, administrators, and default settings seeded.",
                timestamp=datetime.utcnow()
            )
            db.add(log1)
            db.commit()
            print("✅ Audit logs seeded.")

    finally:
        db.close()

if __name__ == "__main__":
    init()
