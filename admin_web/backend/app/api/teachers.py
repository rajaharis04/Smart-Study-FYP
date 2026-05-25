"""Teachers API router."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.models import User, Teacher, Department, Section
from app.schemas.schemas import TeacherCreate, TeacherUpdate, TeacherOut, PasswordResetResponse
from app.services.auth_service import hash_password, generate_random_password
from app.core.deps import get_current_admin, log_action

router = APIRouter(prefix="/teachers", tags=["Teachers"])


def _teacher_to_out(t: Teacher) -> dict:
    return {
        "id": t.id,
        "employee_id": t.employee_id,
        "full_name": t.user.full_name,
        "email": t.user.email,
        "department_name": t.department.name if t.department else None,
        "is_active": t.user.is_active,
        "created_at": t.created_at,
    }


@router.get("/", response_model=List[TeacherOut])
def list_teachers(db: Session = Depends(get_db), _=Depends(get_current_admin)):
    teachers = db.query(Teacher).all()
    return [_teacher_to_out(t) for t in teachers]


@router.post("/", status_code=201)
def create_teacher(
    payload: TeacherCreate,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    # Check email uniqueness
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered.")
    # Check employee ID uniqueness
    if db.query(Teacher).filter(Teacher.employee_id == payload.employee_id).first():
        raise HTTPException(status_code=400, detail="Employee ID already exists.")

    user = User(
        full_name=payload.full_name,
        email=payload.email,
        hashed_password=None,
        role="teacher",
        must_change_password=False,
    )
    db.add(user)
    db.flush()  # get user.id

    teacher = Teacher(
        user_id=user.id,
        employee_id=payload.employee_id,
        department_id=payload.department_id,
    )
    db.add(teacher)
    db.commit()
    db.refresh(teacher)

    log_action(db, admin.email, "CREATE_TEACHER", f"Provisioned teacher account: '{teacher.user.full_name}' (ID: {teacher.id}, Employee ID: {teacher.employee_id}).")

    return {
        **_teacher_to_out(teacher),
        "message": "Teacher account created successfully. The teacher must verify their email and set their password in the app.",
    }


@router.put("/{teacher_id}", response_model=TeacherOut)
def update_teacher(
    teacher_id: int,
    payload: TeacherUpdate,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    teacher = db.query(Teacher).filter(Teacher.id == teacher_id).first()
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found.")

    if payload.full_name is not None:
        teacher.user.full_name = payload.full_name
    if payload.email is not None and payload.email != teacher.user.email:
        existing = db.query(User).filter(User.email == payload.email).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered.")
        teacher.user.email = payload.email
    if payload.department_id is not None:
        teacher.department_id = payload.department_id
    if payload.is_active is not None:
        teacher.user.is_active = payload.is_active

    db.commit()
    db.refresh(teacher)
    log_action(db, admin.email, "UPDATE_TEACHER", f"Updated teacher account: '{teacher.user.full_name}' (ID: {teacher.id}).")
    return _teacher_to_out(teacher)


@router.post("/{teacher_id}/reset-password", response_model=PasswordResetResponse)
def reset_teacher_password(
    teacher_id: int,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    teacher = db.query(Teacher).filter(Teacher.id == teacher_id).first()
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found.")

    new_password = generate_random_password()
    teacher.user.hashed_password = hash_password(new_password)
    teacher.user.must_change_password = True
    db.commit()
    log_action(db, admin.email, "RESET_TEACHER_PASSWORD", f"Reset password for teacher: '{teacher.user.full_name}' (ID: {teacher.id}).")
    return PasswordResetResponse(
        new_password=new_password,
        message=f"Password reset for {teacher.user.full_name}.",
    )


@router.delete("/{teacher_id}")
def delete_teacher(
    teacher_id: int,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    teacher = db.query(Teacher).filter(Teacher.id == teacher_id).first()
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found.")

    teacher_name = teacher.user.full_name
    employee_id = teacher.employee_id

    # Unassign teacher from any sections
    db.query(Section).filter(Section.teacher_id == teacher.id).update({Section.teacher_id: None})

    user_id = teacher.user_id
    db.delete(teacher)

    user = db.query(User).filter(User.id == user_id).first()
    if user:
        db.delete(user)

    db.commit()
    log_action(db, admin.email, "DELETE_TEACHER", f"Deleted teacher account: '{teacher_name}' (Employee ID: {employee_id}, ID: {teacher_id}).")
    return {"message": "Teacher account deleted."}
