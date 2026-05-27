"""
AcademicSections API — Manages the Batch → Department → Section hierarchy.
Each section has a label like "SP23-BCS-A".
Students are then assigned to these sections.
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from app.db.database import get_db
from app.models.models import AcademicSection, Student, Department, User
from app.core.deps import get_current_admin, log_action
from app.services.auth_service import hash_password
from app.services.csv_service import parse_student_csv

router = APIRouter(prefix="/academic-sections", tags=["Academic Sections"])



# ─── Pydantic Schemas ──────────────────────────────────────────────────────────

class AcademicSectionCreate(BaseModel):
    batch: str           # e.g. SP23
    department_id: int
    section_name: str    # e.g. A, B, C


class AcademicSectionUpdate(BaseModel):
    batch: Optional[str] = None
    department_id: Optional[int] = None
    section_name: Optional[str] = None


class AssignStudentPayload(BaseModel):
    student_id: int


# ─── Helpers ───────────────────────────────────────────────────────────────────

def _section_out(sec: AcademicSection) -> dict:
    return {
        "id":           sec.id,
        "batch":        sec.batch,
        "section_name": sec.section_name,
        "department_id": sec.department_id,
        "department_name": sec.department.name if sec.department else None,
        "department_code": sec.department.code if sec.department else None,
        "full_label":   f"{sec.batch}-{sec.department.code if sec.department else '?'}-{sec.section_name}",
        "student_count": len(sec.students),
        "created_at":   sec.created_at,
    }


def _student_out(s: Student) -> dict:
    return {
        "id":           s.id,
        "reg_number":   s.reg_number,
        "full_name":    s.user.full_name,
        "email":        s.user.email,
        "batch":        s.batch,
        "is_active":    s.user.is_active,
        "profile_picture": s.profile_picture,
    }


# ─── Routes ────────────────────────────────────────────────────────────────────

@router.get("/")
def list_all_sections(db: Session = Depends(get_db), _=Depends(get_current_admin)):
    """
    Returns all academic sections grouped by Batch → Department → Section.
    Response structure:
    [
      {
        "batch": "SP23",
        "departments": [
          {
            "department_id": 1,
            "department_name": "...",
            "department_code": "BCS",
            "sections": [ { id, full_label, student_count, ... } ]
          }
        ]
      }
    ]
    """
    sections = db.query(AcademicSection).order_by(
        AcademicSection.batch, AcademicSection.department_id, AcademicSection.section_name
    ).all()

    # Group by batch
    batch_map: dict = {}
    for sec in sections:
        b = sec.batch
        if b not in batch_map:
            batch_map[b] = {}
        dept_id = sec.department_id
        if dept_id not in batch_map[b]:
            batch_map[b][dept_id] = {
                "department_id": dept_id,
                "department_name": sec.department.name if sec.department else None,
                "department_code": sec.department.code if sec.department else None,
                "sections": [],
            }
        batch_map[b][dept_id]["sections"].append(_section_out(sec))

    result = []
    for batch_name in sorted(batch_map.keys()):
        depts = list(batch_map[batch_name].values())
        result.append({"batch": batch_name, "departments": depts})

    return result


@router.get("/flat")
def list_sections_flat(db: Session = Depends(get_db), _=Depends(get_current_admin)):
    """Returns a flat list of all academic sections — useful for dropdowns."""
    sections = db.query(AcademicSection).order_by(
        AcademicSection.batch, AcademicSection.section_name
    ).all()
    return [_section_out(s) for s in sections]


@router.post("/", status_code=201)
def create_section(
    payload: AcademicSectionCreate,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    """Create a new academic section."""
    dept = db.query(Department).filter(Department.id == payload.department_id).first()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found.")

    # Prevent duplicates
    existing = db.query(AcademicSection).filter(
        AcademicSection.batch == payload.batch.strip().upper(),
        AcademicSection.department_id == payload.department_id,
        AcademicSection.section_name == payload.section_name.strip().upper(),
    ).first()
    if existing:
        label = f"{payload.batch.upper()}-{dept.code}-{payload.section_name.upper()}"
        raise HTTPException(status_code=400, detail=f"Section '{label}' already exists.")

    sec = AcademicSection(
        batch=payload.batch.strip().upper(),
        department_id=payload.department_id,
        section_name=payload.section_name.strip().upper(),
    )
    db.add(sec)
    db.commit()
    db.refresh(sec)

    log_action(
        db, admin.email, "CREATE_ACADEMIC_SECTION",
        f"Created academic section '{sec.batch}-{dept.code}-{sec.section_name}' (ID: {sec.id})."
    )
    return _section_out(sec)


@router.put("/{section_id}")
def update_section(
    section_id: int,
    payload: AcademicSectionUpdate,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    sec = db.query(AcademicSection).filter(AcademicSection.id == section_id).first()
    if not sec:
        raise HTTPException(status_code=404, detail="Academic section not found.")

    if payload.batch is not None:
        sec.batch = payload.batch.strip().upper()
    if payload.department_id is not None:
        dept = db.query(Department).filter(Department.id == payload.department_id).first()
        if not dept:
            raise HTTPException(status_code=404, detail="Department not found.")
        sec.department_id = payload.department_id
    if payload.section_name is not None:
        sec.section_name = payload.section_name.strip().upper()

    db.commit()
    db.refresh(sec)
    log_action(db, admin.email, "UPDATE_ACADEMIC_SECTION", f"Updated academic section ID {section_id}.")
    return _section_out(sec)


@router.delete("/{section_id}")
def delete_section(
    section_id: int,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    sec = db.query(AcademicSection).filter(AcademicSection.id == section_id).first()
    if not sec:
        raise HTTPException(status_code=404, detail="Academic section not found.")

    label = f"{sec.batch}-{sec.department.code if sec.department else '?'}-{sec.section_name}"

    # Unassign all students from this section before deleting
    db.query(Student).filter(Student.academic_section_id == section_id).update(
        {"academic_section_id": None}, synchronize_session=False
    )

    db.delete(sec)
    db.commit()

    log_action(db, admin.email, "DELETE_ACADEMIC_SECTION", f"Deleted academic section '{label}' (ID: {section_id}).")
    return {"message": f"Section '{label}' deleted."}


# ─── Students inside a section ──────────────────────────────────────────────

@router.get("/{section_id}/students")
def get_section_students(
    section_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    sec = db.query(AcademicSection).filter(AcademicSection.id == section_id).first()
    if not sec:
        raise HTTPException(status_code=404, detail="Academic section not found.")

    return {
        "section": _section_out(sec),
        "students": [_student_out(s) for s in sec.students],
    }


@router.post("/{section_id}/students")
def assign_student_to_section(
    section_id: int,
    payload: AssignStudentPayload,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    sec = db.query(AcademicSection).filter(AcademicSection.id == section_id).first()
    if not sec:
        raise HTTPException(status_code=404, detail="Academic section not found.")

    student = db.query(Student).filter(Student.id == payload.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found.")

    student.academic_section_id = section_id
    db.commit()

    label = f"{sec.batch}-{sec.department.code if sec.department else '?'}-{sec.section_name}"
    log_action(db, admin.email, "ASSIGN_STUDENT_SECTION",
               f"Assigned student {student.reg_number} to academic section '{label}'.")
    return {"message": f"Student assigned to '{label}' successfully."}


@router.delete("/{section_id}/students/{student_id}")
def remove_student_from_section(
    section_id: int,
    student_id: int,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    sec = db.query(AcademicSection).filter(AcademicSection.id == section_id).first()
    if not sec:
        raise HTTPException(status_code=404, detail="Academic section not found.")

    student = db.query(Student).filter(
        Student.id == student_id,
        Student.academic_section_id == section_id,
    ).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not in this section.")

    student.academic_section_id = None
    db.commit()

    label = f"{sec.batch}-{sec.department.code if sec.department else '?'}-{sec.section_name}"
    log_action(db, admin.email, "REMOVE_STUDENT_SECTION",
               f"Removed student {student.reg_number} from academic section '{label}'.")
    return {"message": "Student removed from section."}


@router.get("/unassigned-students")
def get_unassigned_students(db: Session = Depends(get_db), _=Depends(get_current_admin)):
    """Returns students not yet assigned to any academic section."""
    students = db.query(Student).filter(Student.academic_section_id == None).all()
    return [_student_out(s) for s in students]


# ─── Bulk CSV Upload directly into a section ─────────────────────────────────

@router.post("/{section_id}/bulk-upload")
async def bulk_upload_into_section(
    section_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    """
    CSV se students upload karo — automatically is section mein assign ho jayenge.
    Batch aur department section se inherit hoti hai (CSV mein optional hai).
    CSV Columns: full_name, email, reg_number  (batch aur department_code optional)
    """
    sec = db.query(AcademicSection).filter(AcademicSection.id == section_id).first()
    if not sec:
        raise HTTPException(status_code=404, detail="Academic section not found.")

    label = f"{sec.batch}-{sec.department.code if sec.department else '?'}-{sec.section_name}"

    contents = await file.read()
    try:
        records = parse_student_csv(contents)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    created  = 0
    skipped  = 0
    assigned = 0
    errors   = []

    for record in records:
        try:
            # Skip duplicates
            if db.query(User).filter(User.email == record["email"]).first():
                skipped += 1
                errors.append(f"Email {record['email']} already exists — skipped.")
                continue
            if db.query(Student).filter(Student.reg_number == record["reg_number"]).first():
                skipped += 1
                errors.append(f"RegNo {record['reg_number']} already exists — skipped.")
                continue

            # Create User
            user = User(
                full_name=record["full_name"],
                email=record["email"],
                hashed_password=None,
                role="student",
                must_change_password=False,
            )
            db.add(user)
            db.flush()

            # Create Student — inherit batch + dept from section
            student = Student(
                user_id=user.id,
                reg_number=record["reg_number"],
                batch=record.get("batch") or sec.batch,          # fallback to section batch
                department_id=sec.department_id,                  # always inherit from section
                academic_section_id=section_id,                   # ← directly assign to section
            )
            db.add(student)
            db.flush()
            created  += 1
            assigned += 1

        except Exception as e:
            errors.append(f"Error for {record.get('email', '?')}: {str(e)}")
            db.rollback()
            continue

    db.commit()
    log_action(
        db, admin.email, "BULK_UPLOAD_INTO_SECTION",
        f"Bulk uploaded {created} students into section '{label}' (ID: {section_id})."
    )

    return {
        "created":  created,
        "assigned": assigned,
        "skipped":  skipped,
        "errors":   errors,
        "section":  label,
        "message":  f"{created} students create ho gaye aur '{label}' section mein assign ho gaye!",
    }
