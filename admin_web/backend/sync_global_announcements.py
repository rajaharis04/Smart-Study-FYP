import sys
from app.db.database import SessionLocal
from app.models.models import GlobalAnnouncement, User, Teacher, Student, Notification

def run_sync():
    db = SessionLocal()
    try:
        print("Starting retroactive global announcements sync...")
        announcements = db.query(GlobalAnnouncement).all()
        print(f"Found {len(announcements)} global announcements to sync.")
        
        synced_count = 0
        for ann in announcements:
            target_role = ann.target_role
            dept_id = ann.department_id
            users_to_notify = []
            
            if target_role == "teachers":
                t_query = db.query(User).join(Teacher, Teacher.user_id == User.id).filter(User.is_active == True)
                if dept_id:
                    t_query = t_query.filter(Teacher.department_id == dept_id)
                users_to_notify = t_query.all()
            elif target_role == "students":
                s_query = db.query(User).join(Student, Student.user_id == User.id).filter(User.is_active == True)
                if dept_id:
                    s_query = s_query.filter(Student.department_id == dept_id)
                users_to_notify = s_query.all()
            elif target_role == "all":
                t_query = db.query(User).join(Teacher, Teacher.user_id == User.id).filter(User.is_active == True)
                if dept_id:
                    t_query = t_query.filter(Teacher.department_id == dept_id)
                
                s_query = db.query(User).join(Student, Student.user_id == User.id).filter(User.is_active == True)
                if dept_id:
                    s_query = s_query.filter(Student.department_id == dept_id)
                
                users_to_notify = t_query.all() + s_query.all()
            
            # Check for existing notification to prevent duplicates
            for u in users_to_notify:
                existing = db.query(Notification).filter(
                    Notification.user_id == u.id,
                    Notification.title == f"📢 {ann.title}",
                    Notification.message == ann.content
                ).first()
                
                if not existing:
                    notif = Notification(
                        user_id=u.id,
                        title=f"📢 {ann.title}",
                        message=ann.content,
                        created_at=ann.created_at
                    )
                    db.add(notif)
                    synced_count += 1
                    
        db.commit()
        print(f"✅ Sync complete! Created {synced_count} new notification entries.")
    except Exception as e:
        print(f"❌ Error during sync: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    run_sync()
