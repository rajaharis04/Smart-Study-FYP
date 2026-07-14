"""
Database seeder script.
Populates the database with comprehensive dummy data for testing purposes.
Excludes Course Sections (Point 7) and Enrollments (Point 8) per instructions.
"""
import sys
import os
import random
from datetime import date, timedelta, datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.database import SessionLocal, engine, Base
from app.models.models import (
    User, Department, Teacher, Student, Semester, Course, AcademicSection, AuditLog
)
from app.services.auth_service import hash_password

def seed():
    print("Connecting to database...")
    db = SessionLocal()
    
    try:
        # 1. Seed Departments
        print("\n--- Seeding Departments ---")
        departments_data = [
            {"name": "Computer Science", "code": "CS", "hod_name": "Dr. Muhammad Sharif"},
            {"name": "Software Engineering", "code": "SE", "hod_name": "Dr. Nazir Ahmad"},
            {"name": "Electrical Engineering", "code": "EE", "hod_name": "Dr. Khalid Mahmood"},
            {"name": "Business Administration", "code": "BA", "hod_name": "Dr. Farooq Ali"},
            {"name": "Mathematics", "code": "MATH", "hod_name": "Dr. Tariq Shah"}
        ]
        
        dept_map = {} # code -> Department object
        for dept_info in departments_data:
            dept = db.query(Department).filter(Department.code == dept_info["code"]).first()
            if not dept:
                dept = Department(
                    name=dept_info["name"],
                    code=dept_info["code"],
                    hod_name=dept_info["hod_name"]
                )
                db.add(dept)
                db.flush()
                print(f"Created Department: {dept.name} ({dept.code})")
            else:
                print(f"Department {dept.code} already exists.")
            dept_map[dept_info["code"]] = dept
        
        db.commit()

        # 2. Seed Semesters
        print("\n--- Seeding Semesters ---")
        semesters_data = [
            {"name": "Fall 2024", "is_active": False, "offset_weeks_start": -80, "offset_weeks_end": -60},
            {"name": "Spring 2025", "is_active": False, "offset_weeks_start": -50, "offset_weeks_end": -30},
            {"name": "Fall 2025", "is_active": False, "offset_weeks_start": -25, "offset_weeks_end": -5},
            {"name": "Spring 2026", "is_active": True, "offset_weeks_start": -10, "offset_weeks_end": 10}
        ]
        
        semester_map = {} # name -> Semester object
        today = date.today()
        for sem_info in semesters_data:
            sem = db.query(Semester).filter(Semester.name == sem_info["name"]).first()
            if not sem:
                sem = Semester(
                    name=sem_info["name"],
                    start_date=today + timedelta(weeks=sem_info["offset_weeks_start"]),
                    end_date=today + timedelta(weeks=sem_info["offset_weeks_end"]),
                    is_active=sem_info["is_active"]
                )
                db.add(sem)
                db.flush()
                print(f"Created Semester: {sem.name} (Active: {sem.is_active})")
            else:
                # Update is_active to ensure we match expectations
                sem.is_active = sem_info["is_active"]
                db.flush()
                print(f"Semester {sem.name} already exists. Set Active={sem.is_active}")
            semester_map[sem_info["name"]] = sem
            
        db.commit()

        # 3. Seed Teachers
        print("\n--- Seeding Teachers ---")
        teachers_data = [
            # CS
            {"name": "Dr. Asif Minhas", "email": "asif.minhas@smartstudy.edu", "emp_id": "T-CS-001", "dept": "CS"},
            {"name": "Dr. Sana Fatima", "email": "sana.fatima@smartstudy.edu", "emp_id": "T-CS-002", "dept": "CS"},
            {"name": "Prof. Tariq Mahmood", "email": "tariq.mahmood@smartstudy.edu", "emp_id": "T-CS-003", "dept": "CS"},
            {"name": "Dr. Maria Yusuf", "email": "maria.yusuf@smartstudy.edu", "emp_id": "T-CS-004", "dept": "CS"},
            # SE
            {"name": "Dr. Sajid Hussain", "email": "sajid.hussain@smartstudy.edu", "emp_id": "T-SE-001", "dept": "SE"},
            {"name": "Dr. Faiza Bashir", "email": "faiza.bashir@smartstudy.edu", "emp_id": "T-SE-002", "dept": "SE"},
            {"name": "Dr. Adnan Idrees", "email": "adnan.idrees@smartstudy.edu", "emp_id": "T-SE-003", "dept": "SE"},
            # EE
            {"name": "Dr. Khalid Rizwan", "email": "khalid.rizwan@smartstudy.edu", "emp_id": "T-EE-001", "dept": "EE"},
            {"name": "Dr. Ayesha Siddiqa", "email": "ayesha.siddiqa@smartstudy.edu", "emp_id": "T-EE-002", "dept": "EE"},
            {"name": "Prof. Haroon Rasheed", "email": "haroon.rasheed@smartstudy.edu", "emp_id": "T-EE-003", "dept": "EE"},
            # BA
            {"name": "Dr. Bilal Qureshi", "email": "bilal.qureshi@smartstudy.edu", "emp_id": "T-BA-001", "dept": "BA"},
            {"name": "Dr. Hina Jamil", "email": "hina.jamil@smartstudy.edu", "emp_id": "T-BA-002", "dept": "BA"},
            {"name": "Prof. Imran Khan", "email": "imran.khan@smartstudy.edu", "emp_id": "T-BA-003", "dept": "BA"},
            # MATH
            {"name": "Dr. Noman Arshad", "email": "noman.arshad@smartstudy.edu", "emp_id": "T-MT-001", "dept": "MATH"},
            {"name": "Dr. Zainab Bibi", "email": "zainab.bibi@smartstudy.edu", "emp_id": "T-MT-002", "dept": "MATH"},
            {"name": "Dr. Zubair Ahmed", "email": "zubair.ahmed@smartstudy.edu", "emp_id": "T-MT-003", "dept": "MATH"}
        ]
        
        shared_password = hash_password("Teacher@123")
        for t_info in teachers_data:
            user = db.query(User).filter(User.email == t_info["email"]).first()
            if not user:
                user = User(
                    full_name=t_info["name"],
                    email=t_info["email"],
                    hashed_password=shared_password,
                    role="teacher",
                    is_active=True,
                    must_change_password=False
                )
                db.add(user)
                db.flush()
            
            teacher = db.query(Teacher).filter(Teacher.employee_id == t_info["emp_id"]).first()
            if not teacher:
                teacher = Teacher(
                    user_id=user.id,
                    employee_id=t_info["emp_id"],
                    department_id=dept_map[t_info["dept"]].id
                )
                db.add(teacher)
                print(f"Created Teacher: {user.full_name} ({t_info['emp_id']})")
            else:
                print(f"Teacher {t_info['emp_id']} already exists.")
        
        db.commit()

        # 4. Seed Academic Sections
        print("\n--- Seeding Academic Sections (Class Groups) ---")
        batches = ["FA22", "SP23", "FA23", "SP24", "FA24", "SP25"]
        section_names = ["A", "B"]
        
        academic_sec_map = {} # (batch, dept_code, sec_name) -> AcademicSection object
        
        for batch in batches:
            for dept_code, dept_obj in dept_map.items():
                for sec_name in section_names:
                    # Let's see if this academic section exists
                    academic_sec = db.query(AcademicSection).filter(
                        AcademicSection.batch == batch,
                        AcademicSection.department_id == dept_obj.id,
                        AcademicSection.section_name == sec_name
                    ).first()
                    
                    if not academic_sec:
                        academic_sec = AcademicSection(
                            batch=batch,
                            department_id=dept_obj.id,
                            section_name=sec_name
                        )
                        db.add(academic_sec)
                        db.flush()
                        print(f"Created Academic Section: {batch}-{dept_code}-{sec_name}")
                    else:
                        print(f"Academic Section {batch}-{dept_code}-{sec_name} already exists.")
                    
                    academic_sec_map[(batch, dept_code, sec_name)] = academic_sec
                    
        db.commit()

        # 5. Seed Courses
        print("\n--- Seeding Courses ---")
        courses_data = [
            # CS
            {"name": "Introduction to ICT", "code": "CS101", "dept": "CS", "credit": 3, "semester": "Fall 2024"},
            {"name": "Programming Fundamentals", "code": "CS102", "dept": "CS", "credit": 4, "semester": "Fall 2024"},
            {"name": "Object Oriented Programming", "code": "CS201", "dept": "CS", "credit": 4, "semester": "Spring 2025"},
            {"name": "Data Structures & Algorithms", "code": "CS202", "dept": "CS", "credit": 4, "semester": "Fall 2025"},
            {"name": "Database Systems", "code": "CS301", "dept": "CS", "credit": 4, "semester": "Spring 2026"},
            {"name": "Operating Systems", "code": "CS302", "dept": "CS", "credit": 4, "semester": "Spring 2026"},
            {"name": "Computer Networks", "code": "CS303", "dept": "CS", "credit": 4, "semester": "Spring 2026"},
            {"name": "Artificial Intelligence", "code": "CS401", "dept": "CS", "credit": 4, "semester": "Spring 2026"},
            # SE
            {"name": "Software Engineering Concepts", "code": "SE101", "dept": "SE", "credit": 3, "semester": "Fall 2024"},
            {"name": "Software Requirements Engineering", "code": "SE201", "dept": "SE", "credit": 3, "semester": "Spring 2025"},
            {"name": "Software Design & Architecture", "code": "SE301", "dept": "SE", "credit": 3, "semester": "Fall 2025"},
            {"name": "Software Quality Assurance", "code": "SE302", "dept": "SE", "credit": 3, "semester": "Spring 2026"},
            {"name": "Software Project Management", "code": "SE401", "dept": "SE", "credit": 3, "semester": "Spring 2026"},
            # EE
            {"name": "Linear Circuit Analysis", "code": "EE101", "dept": "EE", "credit": 4, "semester": "Fall 2024"},
            {"name": "Digital Logic Design", "code": "EE201", "dept": "EE", "credit": 4, "semester": "Spring 2025"},
            {"name": "Signals and Systems", "code": "EE202", "dept": "EE", "credit": 4, "semester": "Fall 2025"},
            {"name": "Microprocessor Systems", "code": "EE301", "dept": "EE", "credit": 4, "semester": "Spring 2026"},
            # BA
            {"name": "Introduction to Business", "code": "BA101", "dept": "BA", "credit": 3, "semester": "Fall 2024"},
            {"name": "Principles of Management", "code": "BA102", "dept": "BA", "credit": 3, "semester": "Spring 2025"},
            {"name": "Financial Accounting", "code": "BA201", "dept": "BA", "credit": 3, "semester": "Fall 2025"},
            {"name": "Marketing Management", "code": "BA301", "dept": "BA", "credit": 3, "semester": "Spring 2026"},
            {"name": "Human Resource Management", "code": "BA302", "dept": "BA", "credit": 3, "semester": "Spring 2026"},
            # MATH
            {"name": "Calculus & Analytical Geometry", "code": "MATH101", "dept": "MATH", "credit": 3, "semester": "Fall 2024"},
            {"name": "Linear Algebra", "code": "MATH201", "dept": "MATH", "credit": 3, "semester": "Spring 2025"},
            {"name": "Differential Equations", "code": "MATH202", "dept": "MATH", "credit": 3, "semester": "Fall 2025"},
            {"name": "Numerical Computing", "code": "MATH301", "dept": "MATH", "credit": 3, "semester": "Spring 2026"},
            {"name": "Probability & Statistics", "code": "MATH302", "dept": "MATH", "credit": 3, "semester": "Spring 2026"}
        ]
        
        for c_info in courses_data:
            course = db.query(Course).filter(Course.code == c_info["code"]).first()
            if not course:
                course = Course(
                    name=c_info["name"],
                    code=c_info["code"],
                    credit_hours=c_info["credit"],
                    department_id=dept_map[c_info["dept"]].id,
                    semester_id=semester_map[c_info["semester"]].id
                )
                db.add(course)
                print(f"Created Course: {c_info['name']} ({c_info['code']})")
            else:
                print(f"Course {c_info['code']} already exists.")
                
        db.commit()

        # 6. Seed Students
        print("\n--- Seeding Students ---")
        first_names = [
            "Ali", "Fatima", "Zain", "Usman", "Aisha", "Hamza", "Bilal", "Maryam", 
            "Osama", "Khadija", "Hassan", "Zahra", "Saad", "Sana", "Waqas", "Amna", 
            "Fahad", "Rabia", "Daniyal", "Laiba", "Junaid", "Aqsa", "Farhan", "Mahnoor", 
            "Nabeel", "Hania", "Shahzaib", "Sadia", "Raza", "Tayyaba", "Shoaib", "Zoya",
            "Muneeb", "Anum", "Kamran", "Sidra", "Ahmad", "Iqra", "Zeeshan", "Kiran",
            "Waseem", "Nida", "Arsalan", "Maria", "Adeel", "Saba", "Taimoor", "Sehrish",
            "Yasir", "Rimsha", "Faisal", "Komel", "Jamil", "Urooj", "Haris", "Sahar",
            "Umair", "Tayyab", "Mehak", "Nouman", "Sonia", "Asad", "Zunaira", "Rizwan"
        ]
        
        last_names = [
            "Ahmed", "Khan", "Ali", "Malik", "Qureshi", "Butt", "Shah", "Siddiqui", 
            "Raza", "Zafar", "Iqbal", "Sheikh", "Abbasi", "Dar", "Awan", "Mughal",
            "Javed", "Saeed", "Hassan", "Bashir", "Hashmi", "Latif"
        ]
        
        # We want to create around 65 students
        shared_student_password = hash_password("Student@123")
        student_count = 0
        
        # Generate clean unique names
        generated_names = set()
        while len(generated_names) < 70:
            fn = random.choice(first_names)
            ln = random.choice(last_names)
            name = f"{fn} {ln}"
            generated_names.add(name)
            
        generated_names_list = list(generated_names)
        
        # We will loop and assign to batches, departments and academic sections
        # To make it distributed:
        for idx, student_name in enumerate(generated_names_list[:65]):
            # Deterministic selection based on index so it behaves nicely
            batch = batches[idx % len(batches)]
            dept_code = list(dept_map.keys())[idx % len(dept_map)]
            sec_name = section_names[(idx // len(dept_map)) % len(section_names)]
            
            # Registration format: SP23-BCS-001 (using department and 1-based format)
            # Make a padded registration number
            serial = (idx // (len(batches) * len(section_names))) + 1
            reg_num = f"{batch}-B{dept_code}-{serial:03d}"
            email = f"student.{reg_num.lower()}@smartstudy.edu"
            
            # Retrieve Academic Section
            academic_sec = academic_sec_map[(batch, dept_code, sec_name)]
            
            # Create user if not exists
            user = db.query(User).filter(User.email == email).first()
            if not user:
                user = User(
                    full_name=student_name,
                    email=email,
                    hashed_password=shared_student_password,
                    role="student",
                    is_active=True,
                    must_change_password=False
                )
                db.add(user)
                db.flush()
                
            student = db.query(Student).filter(Student.reg_number == reg_num).first()
            if not student:
                student = Student(
                    user_id=user.id,
                    reg_number=reg_num,
                    batch=batch,
                    department_id=dept_map[dept_code].id,
                    academic_section_id=academic_sec.id
                )
                db.add(student)
                student_count += 1
                if student_count % 10 == 0 or student_count == 1:
                    print(f"Created Student {student_count}: {student_name} ({reg_num}) in Academic Section {batch}-{dept_code}-{sec_name}")
            else:
                # If student already exists but maybe section got unassigned or anything, let's keep it
                pass
                
        db.commit()
        print(f"\n✅ Total students checked/created: {student_count}")
        
        # 7. Add Audit Log
        audit = AuditLog(
            user_name="admin@smartstudy.edu",
            action="SEED_DUMMY_DATA",
            details=f"Seeded dummy testing data: 5 departments, 4 semesters, 16 teachers, 60 academic sections, 27 courses, and {student_count} students.",
            timestamp=datetime.utcnow()
        )
        db.add(audit)
        db.commit()
        print("✅ Added audit log entry.")
        print("\n🎉 Seeding completed successfully!")
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ Error during seeding: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    seed()
