"""Students API router — manual creation + CSV bulk upload."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.models import User, Student, Department, Enrollment
from app.schemas.schemas import StudentCreate, StudentUpdate, StudentOut, BulkStudentResult, PasswordResetResponse
from app.services.auth_service import hash_password, generate_random_password
from app.services.csv_service import parse_student_csv
from app.core.deps import get_current_admin, log_action

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

router = APIRouter(prefix="/students", tags=["Students"])



def _student_to_out(s: Student) -> dict:
    return {
        "id": s.id,
        "reg_number": s.reg_number,
        "full_name": s.user.full_name,
        "email": s.user.email,
        "batch": s.batch,
        "department_name": s.department.name if s.department else None,
        "is_active": s.user.is_active,
        "created_at": s.created_at,
    }


@router.get("/", response_model=List[StudentOut])
def list_students(db: Session = Depends(get_db), _=Depends(get_current_admin)):
    students = db.query(Student).all()
    return [_student_to_out(s) for s in students]


@router.post("/", status_code=201)
def create_student(
    payload: StudentCreate,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered.")
    if db.query(Student).filter(Student.reg_number == payload.reg_number).first():
        raise HTTPException(status_code=400, detail="Registration number already exists.")

    user = User(
        full_name=payload.full_name,
        email=payload.email,
        hashed_password=None,
        role="student",
        must_change_password=False,
    )
    db.add(user)
    db.flush()

    student = Student(
        user_id=user.id,
        reg_number=payload.reg_number,
        batch=payload.batch,
        department_id=payload.department_id,
    )
    db.add(student)
    db.commit()
    db.refresh(student)

    log_action(db, admin.email, "CREATE_STUDENT", f"Created student profile: '{student.user.full_name}' (Reg: {student.reg_number}, ID: {student.id}).")

    return {
        **_student_to_out(student),
        "message": "Student account created successfully. The student must verify their email and set their password in the app.",
    }


@router.post("/bulk-upload", response_model=BulkStudentResult)
async def bulk_upload_students(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    """Upload a CSV file to create multiple student accounts at once."""
    contents = await file.read()
    try:
        records = parse_student_csv(contents)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    created = 0
    skipped = 0
    errors = []

    for record in records:
        try:
            # Skip if email or reg number already exists
            if db.query(User).filter(User.email == record["email"]).first():
                skipped += 1
                errors.append(f"Email {record['email']} already exists — skipped.")
                continue
            if db.query(Student).filter(Student.reg_number == record["reg_number"]).first():
                skipped += 1
                errors.append(f"RegNumber {record['reg_number']} already exists — skipped.")
                continue

            # Resolve department by code
            dept = None
            if record.get("department_code"):
                dept = db.query(Department).filter(
                    Department.code == record["department_code"]
                ).first()

            user = User(
                full_name=record["full_name"],
                email=record["email"],
                hashed_password=None,
                role="student",
                must_change_password=False,
            )
            db.add(user)
            db.flush()

            student = Student(
                user_id=user.id,
                reg_number=record["reg_number"],
                batch=record["batch"],
                department_id=dept.id if dept else None,
            )
            db.add(student)
            db.flush()
            created += 1

        except Exception as e:
            errors.append(f"Error for {record.get('email', '?')}: {str(e)}")
            db.rollback()
            continue

    db.commit()
    log_action(db, admin.email, "BULK_UPLOAD_STUDENTS", f"Bulk uploaded {created} student profiles from CSV file.")
    return BulkStudentResult(created=created, skipped=skipped, errors=errors)


@router.put("/{student_id}", response_model=StudentOut)
def update_student(
    student_id: int,
    payload: StudentUpdate,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found.")

    if payload.full_name is not None:
        student.user.full_name = payload.full_name
    if payload.email is not None and payload.email != student.user.email:
        existing = db.query(User).filter(User.email == payload.email).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered.")
        student.user.email = payload.email
    if payload.batch is not None:
        student.batch = payload.batch
    if payload.department_id is not None:
        student.department_id = payload.department_id
    if payload.is_active is not None:
        student.user.is_active = payload.is_active

    db.commit()
    db.refresh(student)
    log_action(db, admin.email, "UPDATE_STUDENT", f"Updated student profile: '{student.user.full_name}' (Reg: {student.reg_number}, ID: {student_id}).")
    return _student_to_out(student)


@router.post("/{student_id}/reset-password", response_model=PasswordResetResponse)
def reset_student_password(
    student_id: int,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found.")

    new_password = generate_random_password()
    student.user.hashed_password = hash_password(new_password)
    student.user.must_change_password = True
    db.commit()
    log_action(db, admin.email, "RESET_STUDENT_PASSWORD", f"Reset password for student: '{student.user.full_name}' (Reg: {student.reg_number}, ID: {student.id}).")
    return PasswordResetResponse(
        new_password=new_password,
        message=f"Password reset for {student.user.full_name}.",
    )


@router.delete("/{student_id}")
def delete_student(
    student_id: int,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found.")

    student_name = student.user.full_name
    reg_number = student.reg_number

    # Delete all student enrollments
    db.query(Enrollment).filter(Enrollment.student_id == student.id).delete()

    user_id = student.user_id
    db.delete(student)

    user = db.query(User).filter(User.id == user_id).first()
    if user:
        db.delete(user)

    db.commit()
    log_action(db, admin.email, "DELETE_STUDENT", f"Deleted student profile: '{student_name}' (Reg: {reg_number}, ID: {student_id}).")
    return {"message": "Student account deleted."}


@router.get("/me")
def get_student_me(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    from app.services.auth_service import decode_token
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    student = db.query(Student).filter(Student.user_id == user.id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student profile not found")
        
    return {
        "id": student.id,
        "full_name": user.full_name,
        "email": user.email,
        "role": user.role,
        "reg_number": student.reg_number,
        "batch": student.batch,
        "department": student.department.name if student.department else "Computer Science"
    }

