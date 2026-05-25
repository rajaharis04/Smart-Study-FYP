import math
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.models import (
    StudentLearningProfile, Lecture, Quiz, QuizQuestion, QuizResponse, LectureSession, StudentQA, Topic
)

def recalculate_student_learning_profile(student_id: int, topic_id: int, db: Session) -> StudentLearningProfile:
    """
    Recalculates the StudentLearningProfile metrics for a given student and topic.
    Persists the updated values to the Postgres database.
    """
    # 1. Fetch the topic and course
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        return None

    course_id = topic.course_id

    # 2. Get all published lectures and quizzes for this topic
    lectures = db.query(Lecture).filter(
        Lecture.topic_id == topic_id,
        Lecture.is_published == True
    ).all()
    lecture_ids = [l.id for l in lectures]

    scores = []
    quiz_ids = []
    
    if lecture_ids:
        quizzes = db.query(Quiz).filter(Quiz.lecture_id.in_(lecture_ids)).all()
        quiz_ids = [q.id for q in quizzes]
        
        # Calculate score per quiz
        for quiz in quizzes:
            total_questions = db.query(QuizQuestion).filter(QuizQuestion.quiz_id == quiz.id).count()
            if total_questions == 0:
                continue
                
            correct_responses = db.query(QuizResponse).filter(
                QuizResponse.quiz_id == quiz.id,
                QuizResponse.student_id == student_id,
                QuizResponse.is_correct == True
            ).count()
            
            has_attempt = db.query(QuizResponse).filter(
                QuizResponse.quiz_id == quiz.id,
                QuizResponse.student_id == student_id
            ).count() > 0
            
            if has_attempt:
                score = (correct_responses / total_questions) * 100.0
                scores.append(score)

    # Calculate Mastery Score (Average quiz score)
    mastery_score = 0.0
    if scores:
        mastery_score = sum(scores) / len(scores)

    # Calculate Confidence Score (Stability of last 3 quiz attempts)
    confidence_score = 0.0
    if scores:
        last_scores = scores[-3:]
        n = len(last_scores)
        if n >= 2:
            mean_val = sum(last_scores) / n
            variance = sum((x - mean_val) ** 2 for x in last_scores) / n
            std_dev = math.sqrt(variance)
            # Higher std dev (variance) penalizes the confidence score
            confidence_score = max(0.0, min(100.0, mean_val - (std_dev * 1.5)))
        elif n == 1:
            confidence_score = last_scores[0]
    
    # Identify Weak Topic (flagged if mastery falls below 60%)
    is_weak = mastery_score < 60.0

    # Calculate Learning Pace (Average seconds spent per MCQ question)
    learning_pace = 30.0
    if quiz_ids:
        avg_pace = db.query(func.avg(QuizResponse.time_taken_seconds)).filter(
            QuizResponse.quiz_id.in_(quiz_ids),
            QuizResponse.student_id == student_id,
            QuizResponse.answer != None
        ).scalar()
        if avg_pace is not None:
            learning_pace = float(avg_pace)

    # Calculate Engagement Score
    avg_watch_pct = 0.0
    engagement_score = 0.0
    
    if lecture_ids:
        sessions = db.query(LectureSession).filter(
            LectureSession.student_id == student_id,
            LectureSession.lecture_id.in_(lecture_ids)
        ).all()
        
        if sessions:
            avg_watch_pct = sum(s.watch_percentage for s in sessions) / len(sessions)
            
            # Dynamic engagement calculation per session
            qna_count = db.query(StudentQA).filter(
                StudentQA.student_id == student_id,
                StudentQA.course_id == course_id
            ).count()
            qna_score = min(qna_count / 5.0, 1.0)
            
            total_session_engagement = 0.0
            for s in sessions:
                pause_score = 1.0 / (1.0 + s.pause_count)
                # Engagement=(ForegroundRatio*0.40) + (PauseScore*0.30) + (QnAScore*0.30)
                engagement = (1.0 * 0.40) + (pause_score * 0.30) + (qna_score * 0.30)
                s.engagement_score = round(engagement, 4)
                total_session_engagement += s.engagement_score
            
            avg_engagement = total_session_engagement / len(sessions)
            engagement_score = avg_engagement * 100.0  # Scale to 0.0 - 100.0

    # Calculate Hint Dependency
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
            hint_dependency = hint_used_count / total_responses

    # Calculate overall Learning Score
    # Formula: LearningScore = (QuizPerformance * 0.60) + (WatchCompletionRate * 0.20) + (EngagementScore * 0.20)
    learning_score = (mastery_score * 0.60) + (avg_watch_pct * 0.20) + (engagement_score * 0.20)

    # 3. Create or update profile record in database
    profile = db.query(StudentLearningProfile).filter(
        StudentLearningProfile.student_id == student_id,
        StudentLearningProfile.topic_id == topic_id
    ).first()

    if not profile:
        profile = StudentLearningProfile(
            student_id=student_id,
            topic_id=topic_id,
            mastery_score=round(mastery_score, 2),
            confidence_score=round(confidence_score, 2),
            learning_pace=round(learning_pace, 2),
            engagement_score=round(engagement_score, 2),
            hint_dependency=round(hint_dependency, 2),
            learning_score=round(learning_score, 2),
            is_weak=is_weak
        )
        db.add(profile)
    else:
        profile.mastery_score = round(mastery_score, 2)
        profile.confidence_score = round(confidence_score, 2)
        profile.learning_pace = round(learning_pace, 2)
        profile.engagement_score = round(engagement_score, 2)
        profile.hint_dependency = round(hint_dependency, 2)
        profile.learning_score = round(learning_score, 2)
        profile.is_weak = is_weak

    db.commit()
    db.refresh(profile)
    return profile
