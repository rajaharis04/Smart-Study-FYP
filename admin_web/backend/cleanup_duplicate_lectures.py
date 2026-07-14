"""
cleanup_duplicate_lectures.py
Run this once from the admin_web/backend directory to remove duplicate lectures.
Usage:
  cd /Users/rajaharis01/Desktop/SamrtStudyInstructeer/smartstudy/admin_web/backend
  source venv/bin/activate
  python cleanup_duplicate_lectures.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.database import SessionLocal
from app.models.models import Lecture

db = SessionLocal()

try:
    lectures = db.query(Lecture).order_by(Lecture.id).all()

    seen = {}   # (section_id, title) -> first lecture id
    to_delete = []

    for lec in lectures:
        key = (lec.section_id, lec.title.strip())
        if key in seen:
            to_delete.append(lec)
        else:
            seen[key] = lec.id

    print(f"Found {len(to_delete)} duplicate lectures to remove:")
    for lec in to_delete:
        print(f"  - [{lec.id}] '{lec.title}' (section {lec.section_id})")

    if to_delete:
        confirm = input("\nDelete these duplicates? (yes/no): ").strip().lower()
        if confirm == 'yes':
            for lec in to_delete:
                db.delete(lec)
            db.commit()
            print(f"\n✅ Deleted {len(to_delete)} duplicate lectures.")
        else:
            print("Aborted.")
    else:
        print("No duplicates found.")
finally:
    db.close()
