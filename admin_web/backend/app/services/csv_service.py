"""
CSV Service — Parse CSV files for bulk student/enrollment uploads.
Uses Python's built-in csv module (zero dependencies).
"""
import csv
import io
from typing import List, Dict, Any

STUDENT_CSV_REQUIRED = {"Name", "Email", "RegNumber"}
STUDENT_CSV_OPTIONAL = {"Batch", "Department"}   # Optional — section se inherit ho sakti hai


def parse_student_csv(file_bytes: bytes) -> List[Dict[str, Any]]:
    """
    Parse a student CSV file and return a list of student dicts.
    Required columns: Name, Email, RegNumber
    Optional columns: Batch, Department (section se inherit hogi agar missing ho)
    """
    try:
        text = file_bytes.decode('utf-8')
        f = io.StringIO(text)
        reader = csv.DictReader(f)

        # Strip whitespace from column headers
        if reader.fieldnames:
            reader.fieldnames = [name.strip() for name in reader.fieldnames]
        else:
            raise ValueError("CSV is empty or missing headers.")

        columns = set(reader.fieldnames)
        missing = STUDENT_CSV_REQUIRED - columns
        if missing:
            raise ValueError(f"Missing required columns in CSV: {', '.join(missing)}")

        records = []
        for row in reader:
            clean_row = {k: (v.strip() if v else "") for k, v in row.items()}

            # Skip if Email or RegNumber is empty
            if not clean_row.get("Email") or not clean_row.get("RegNumber"):
                continue

            records.append({
                "full_name":       clean_row.get("Name", ""),
                "email":           clean_row["Email"],
                "reg_number":      clean_row["RegNumber"],
                "batch":           clean_row.get("Batch", ""),          # empty = use section batch
                "department_code": clean_row.get("Department", ""),     # empty = use section dept
            })
        return records
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"CSV parsing error: {str(e)}")



def parse_enrollment_csv(file_bytes: bytes) -> List[str]:
    """
    Parse an enrollment CSV and return a list of registration numbers.
    Expected column: RegNumber
    """
    try:
        text = file_bytes.decode('utf-8')
        f = io.StringIO(text)
        reader = csv.DictReader(f)

        # Strip whitespace from column headers
        if reader.fieldnames:
            reader.fieldnames = [name.strip() for name in reader.fieldnames]
        else:
            raise ValueError("CSV is empty or missing headers.")

        if "RegNumber" not in reader.fieldnames:
            raise ValueError("CSV must have a 'RegNumber' column.")

        reg_numbers = []
        for row in reader:
            reg = row.get("RegNumber")
            if reg:
                reg_numbers.append(reg.strip())
        return reg_numbers
    except Exception as e:
        raise ValueError(f"CSV parsing error: {str(e)}")
