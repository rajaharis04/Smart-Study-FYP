"""
Learning Model Service — BKT-Enhanced with Assignment Integration
=================================================================
Recalculates StudentLearningProfile using:
  - BKT (Bayesian Knowledge Tracing) for quiz mastery
  - Assignment graded scores blended in (60% quiz + 40% assignment)
  - Engagement, confidence, hint dependency, learning pace
  - Auto weak-topic notification system
"""

import math
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.models import (
    StudentLearningProfile, Lecture, Quiz, QuizQuestion, QuizResponse,
    LectureSession, StudentQA, Topic, Notification
)


def recalculate_student_learning_profile(student_id: int, topic_id: int, db: Session) -> StudentLearningProfile:
    """
    Recalculates StudentLearningProfile for a student-topic pair.
    Uses BKT + assignment performance blend for mastery.
    Formula: mastery = bkt_quiz(60%) + assignment(40%) when graded assignments exist.
    Persists updated values to Postgres and sends weak-topic notification if needed.
    """
    from app.services.bkt_model import (
        compute_bkt_mastery_for_topic,
        compute_confidence_score,
        compute_assignment_mastery
    )

    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        return None

    course_id = topic.course_id

    # ── Step 1: BKT Quiz Mastery ─────────────────────────────────────
    bkt_mastery = compute_bkt_mastery_for_topic(student_id, topic_id, db)

    # ── Step 2: Assignment Mastery ───────────────────────────────────
    assignment_mastery = compute_assignment_mastery(student_id, topic_id, db)

    # ── Step 3: Combined Mastery ─────────────────────────────────────
    if assignment_mastery > 0:
        mastery_score = round((bkt_mastery * 0.60) + (assignment_mastery * 0.40), 2)
    else:
        mastery_score = bkt_mastery

    # ── Step 4: Confidence Score ─────────────────────────────────────
    confidence_score = compute_confidence_score(student_id, topic_id, db)

    # ── Step 5: Is Weak? ─────────────────────────────────────────────
    is_weak = mastery_score < 60.0

    # ── Step 6: Get lectures/quizzes for pace and engagement ─────────
    lectures = db.query(Lecture).filter(
        Lecture.topic_id == topic_id,
        Lecture.is_published == True
    ).all()
    lecture_ids = [l.id for l in lectures]
    quiz_ids = []
    learning_pace = 30.0
    avg_watch_pct = 0.0
    engagement_score = 0.0

    if lecture_ids:
        quizzes = db.query(Quiz).filter(Quiz.lecture_id.in_(lecture_ids)).all()
        quiz_ids = [q.id for q in quizzes]

        # ── Step 7: Learning Pace ─────────────────────────────────────
        if quiz_ids:
            avg_pace = db.query(func.avg(QuizResponse.time_taken_seconds)).filter(
                QuizResponse.quiz_id.in_(quiz_ids),
                QuizResponse.student_id == student_id,
                QuizResponse.answer != None
            ).scalar()
            if avg_pace is not None:
                learning_pace = float(avg_pace)

        # ── Step 8: Engagement Score ──────────────────────────────────
        sessions = db.query(LectureSession).filter(
            LectureSession.student_id == student_id,
            LectureSession.lecture_id.in_(lecture_ids)
        ).all()

        if sessions:
            avg_watch_pct = sum(s.watch_percentage for s in sessions) / len(sessions)
            qna_count = db.query(StudentQA).filter(
                StudentQA.student_id == student_id,
                StudentQA.course_id == course_id
            ).count()
            qna_score = min(qna_count / 5.0, 1.0)

            total_eng = 0.0
            for s in sessions:
                pause_score = 1.0 / (1.0 + s.pause_count)
                engagement = (1.0 * 0.40) + (pause_score * 0.30) + (qna_score * 0.30)
                s.engagement_score = round(engagement, 4)
                total_eng += s.engagement_score
            avg_eng = total_eng / len(sessions)
            engagement_score = avg_eng * 100.0

    # ── Step 9: Hint Dependency ───────────────────────────────────────
    hint_dependency = 0.0
    if quiz_ids:
        total_responses = db.query(QuizResponse).filter(
            QuizResponse.quiz_id.in_(quiz_ids),
            QuizResponse.student_id == student_id
        ).count()
        if total_responses > 0:
            hint_used_count = db.query(QuizResponse).filter(
                QuizResponse.quiz_id.in_(quiz_ids),
                QuizResponse.student_id == student_id,
                QuizResponse.hint_used == True
            ).count()
            hint_dependency = round(hint_used_count / total_responses, 4)

    # ── Step 10: Learning Score ───────────────────────────────────────
    learning_score = round(
        (mastery_score * 0.60) + (avg_watch_pct * 0.20) + (engagement_score * 0.20),
        2
    )

    # ── Step 11: Upsert Profile ───────────────────────────────────────
    profile = db.query(StudentLearningProfile).filter(
        StudentLearningProfile.student_id == student_id,
        StudentLearningProfile.topic_id == topic_id
    ).first()

    if not profile:
        profile = StudentLearningProfile(
            student_id=student_id,
            topic_id=topic_id,
            mastery_score=mastery_score,
            confidence_score=round(confidence_score, 2),
            learning_pace=round(learning_pace, 2),
            engagement_score=round(engagement_score, 2),
            hint_dependency=round(hint_dependency, 2),
            learning_score=learning_score,
            is_weak=is_weak
        )
        db.add(profile)
    else:
        profile.mastery_score    = mastery_score
        profile.confidence_score = round(confidence_score, 2)
        profile.learning_pace    = round(learning_pace, 2)
        profile.engagement_score = round(engagement_score, 2)
        profile.hint_dependency  = round(hint_dependency, 2)
        profile.learning_score   = learning_score
        profile.is_weak          = is_weak

    db.commit()
    db.refresh(profile)

    # ── Step 12: Auto-notify student if weak topic detected ──────────
    if is_weak:
        from app.models.models import Student
        from datetime import datetime, timedelta
        student = db.query(Student).filter(Student.id == student_id).first()
        if student:
            recent_cutoff = datetime.utcnow() - timedelta(days=3)
            existing_notif = db.query(Notification).filter(
                Notification.user_id == student.user_id,
                Notification.title == f"Weak Topic Alert: {topic.title}",
                Notification.created_at >= recent_cutoff
            ).first()
            if not existing_notif:
                rec_lecture = db.query(Lecture).filter(
                    Lecture.topic_id == topic_id,
                    Lecture.is_published == True
                ).order_by(Lecture.created_at.asc()).first()
                rec_msg = (
                    f"Your mastery in '{topic.title}' is {mastery_score:.0f}% — below the 60% passing threshold. "
                )
                if rec_lecture:
                    rec_msg += f"We recommend rewatching: '{rec_lecture.title}' to strengthen your understanding."
                else:
                    rec_msg += "Please review the course materials and attempt the practice quizzes again."
                notif = Notification(
                    user_id=student.user_id,
                    title=f"Weak Topic Alert: {topic.title}",
                    message=rec_msg,
                    is_read=False
                )
                db.add(notif)
                db.commit()

    return profile
