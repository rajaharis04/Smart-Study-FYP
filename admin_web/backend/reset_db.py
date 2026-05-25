"""
Database reset utility. Drops all existing tables and re-initializes them.
"""
from app.db.database import Base, engine
from init_db import init

def reset():
    print("Dropping all existing database tables...")
    Base.metadata.drop_all(bind=engine)
    print("✅ All tables dropped.")
    print("Re-initializing database...")
    init()

if __name__ == "__main__":
    reset()
