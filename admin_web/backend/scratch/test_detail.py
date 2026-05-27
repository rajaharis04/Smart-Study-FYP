import sys
import os

# Add app to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import SessionLocal
from app.models.models import Student, Enrollment

db = SessionLocal()
try:
    student = db.query(Student).first()
    if not student:
        print("No students found in the database.")
    else:
        print(f"Testing student detail logic for student ID: {student.id} ({student.user.full_name})")
        
        enrollments_list = []
        for enrollment in student.enrollments:
            section = enrollment.section
            if not section:
                print("Skipped enrollment without section")
                continue
            course = section.course
            if not course:
                print("Skipped section without course")
                continue
            teacher = section.teacher
            instructor_name = teacher.user.full_name if teacher and teacher.user else "TBA"
            
            enrollments_list.append({
                "id": enrollment.id,
                "section_id": section.id,
                "section_label": section.section_label,
                "course_code": course.code,
                "course_name": course.name,
                "instructor_name": instructor_name,
                "status": enrollment.status,
                "is_active": enrollment.is_active,
                "enrolled_at": enrollment.enrolled_at,
            })
            
        result = {
            "id": student.id,
            "reg_number": student.reg_number,
            "full_name": student.user.full_name,
            "email": student.user.email,
            "batch": student.batch,
            "department_name": student.department.name if student.department else None,
            "academic_section_label": student.academic_section.full_label if student.academic_section else "Unassigned",
            "is_active": student.user.is_active,
            "profile_picture": student.profile_picture,
            "created_at": student.created_at,
            "enrollments": enrollments_list
        }
        print("Success! Result dictionary:")
        print(result)
except Exception as e:
    print("Failed with exception:", str(e))
    import traceback
    traceback.print_exc()
finally:
    db.close()
