from app.db.database import SessionLocal
from app.models.models import Notification, User

db = SessionLocal()
print("--- USERS ---")
for u in db.query(User).all():
    print(f"ID: {u.id}, Name: {u.full_name}, Email: {u.email}, Active: {u.is_active}, Role: {u.role}")

print("\n--- NOTIFICATIONS ---")
for n in db.query(Notification).all():
    print(f"ID: {n.id}, UserID: {n.user_id}, Title: {n.title}, Read: {n.is_read}, Message: {n.message[:30]}")

db.close()
