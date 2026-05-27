from app.db.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
timezone_setting = db.execute(text("SHOW TIMEZONE")).scalar()
print("PostgreSQL timezone setting:", timezone_setting)
db.close()
