"""Departments API router."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.models import Department
from app.schemas.schemas import DepartmentCreate, DepartmentUpdate, DepartmentOut
from app.core.deps import get_current_admin

router = APIRouter(prefix="/departments", tags=["Departments"])


@router.get("/", response_model=List[DepartmentOut])
def list_departments(db: Session = Depends(get_db), _=Depends(get_current_admin)):
    return db.query(Department).order_by(Department.name).all()


@router.post("/", response_model=DepartmentOut, status_code=201)
def create_department(
    payload: DepartmentCreate,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    existing = db.query(Department).filter(Department.code == payload.code).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Department code '{payload.code}' already exists.")
    dept = Department(**payload.model_dump())
    db.add(dept)
    db.commit()
    db.refresh(dept)
    return dept


@router.get("/{dept_id}", response_model=DepartmentOut)
def get_department(dept_id: int, db: Session = Depends(get_db), _=Depends(get_current_admin)):
    dept = db.query(Department).filter(Department.id == dept_id).first()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found.")
    return dept


@router.put("/{dept_id}", response_model=DepartmentOut)
def update_department(
    dept_id: int,
    payload: DepartmentUpdate,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    dept = db.query(Department).filter(Department.id == dept_id).first()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found.")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(dept, field, value)
    db.commit()
    db.refresh(dept)
    return dept


@router.get("/{dept_id}/detail")
def get_department_detail(
    dept_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin)
):
    dept = db.query(Department).filter(Department.id == dept_id).first()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found.")
    
    teachers_list = []
    for t in dept.teachers:
        teachers_list.append({
            "id": t.id,
            "employee_id": t.employee_id,
            "full_name": t.user.full_name,
            "email": t.user.email,
            "is_active": t.user.is_active,
        })
        
    courses_list = []
    for c in dept.courses:
        courses_list.append({
            "id": c.id,
            "code": c.code,
            "name": c.name,
            "credit_hours": c.credit_hours,
        })
        
    sections_list = []
    for sec in dept.academic_sections:
        sections_list.append({
            "id": sec.id,
            "batch": sec.batch,
            "section_name": sec.section_name,
            "full_label": sec.full_label,
        })
        
    return {
        "id": dept.id,
        "name": dept.name,
        "code": dept.code,
        "hod_name": dept.hod_name,
        "created_at": dept.created_at,
        "teachers": teachers_list,
        "courses": courses_list,
        "academic_sections": sections_list,
        "student_count": len(dept.students)
    }


@router.delete("/{dept_id}")
def delete_department(dept_id: int, db: Session = Depends(get_db), _=Depends(get_current_admin)):
    dept = db.query(Department).filter(Department.id == dept_id).first()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found.")
    db.delete(dept)
    db.commit()
    return {"message": "Department deleted."}
