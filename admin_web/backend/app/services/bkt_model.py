"""
BKT Model — Bayesian Knowledge Tracing
=======================================
Per-topic mastery probability ko quiz responses ke basis par update karta hai.
No external ML library required — pure Python math.

BKT Parameters (standard educational values):
  P(L0) = 0.30  — Prior probability of mastery before any evidence
  P(T)  = 0.09  — Probability of learning (transition: not learned → learned)
  P(G)  = 0.25  — Probability of guessing correctly when not mastered
  P(S)  = 0.10  — Probability of slipping (mistake when mastered)
"""

import math
from sqlalchemy.orm import Session
from app.models.models import (
    StudentLearningProfile, Topic, Quiz, QuizQuestion, QuizResponse, Lecture
)

BKT_DEFAULTS = {
    "p_l0":   0.30,
    "p_t":    0.09,
    "p_g":    0.25,
    "p_s":    0.10,
}


def _bkt_update(p_l: float, is_correct: bool,
                p_t: float, p_g: float, p_s: float) -> float:
    """Single Bayesian update after one question response."""
    if is_correct:
        p_correct = (1 - p_s) * p_l + p_g * (1 - p_l)
        if p_correct == 0:
            return p_l
        p_l_given_correct = ((1 - p_s) * p_l) / p_correct
    else:
        p_incorrect = p_s * p_l + (1 - p_g) * (1 - p_l)
        if p_incorrect == 0:
            return p_l
        p_l_given_correct = (p_s * p_l) / p_incorrect

    p_l_new = p_l_given_correct + (1 - p_l_given_correct) * p_t
    return max(0.0, min(1.0, p_l_new))


def compute_bkt_mastery_for_topic(
    student_id: int, topic_id: int, db: Session
) -> float:
    """
    Computes BKT-based mastery probability for a student on a topic.
    Returns probability in 0.0-100.0 range.
    Processes all quiz responses in chronological order with sequential Bayesian updates.
    """
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        return 0.0

    lectures = db.query(Lecture).filter(
        Lecture.topic_id == topic_id,
        Lecture.is_published == True
    ).order_by(Lecture.created_at.asc()).all()

    if not lectures:
        return 0.0

    lecture_ids = [l.id for l in lectures]
    quizzes = db.query(Quiz).filter(
        Quiz.lecture_id.in_(lecture_ids)
    ).order_by(Quiz.created_at.asc()).all()

    if not quizzes:
        return 0.0

    quiz_ids = [q.id for q in quizzes]
    responses = db.query(QuizResponse).filter(
        QuizResponse.student_id == student_id,
        QuizResponse.quiz_id.in_(quiz_ids),
        QuizResponse.is_correct != None
    ).order_by(QuizResponse.answered_at.asc()).all()

    if not responses:
        return 0.0

    p_l = BKT_DEFAULTS["p_l0"]
    p_t = BKT_DEFAULTS["p_t"]
    p_g = BKT_DEFAULTS["p_g"]
    p_s = BKT_DEFAULTS["p_s"]

    for resp in responses:
        p_l = _bkt_update(p_l, bool(resp.is_correct), p_t, p_g, p_s)

    return round(p_l * 100.0, 2)


def compute_confidence_score(
    student_id: int, topic_id: int, db: Session
) -> float:
    """
    Confidence = stability of recent performance.
    Analyzes last 5 quiz attempts; lower variance -> higher confidence.
    Returns 0.0-100.0.
    """
    lectures = db.query(Lecture).filter(
        Lecture.topic_id == topic_id,
        Lecture.is_published == True
    ).all()
    lecture_ids = [l.id for l in lectures]

    if not lecture_ids:
        return 0.0

    quizzes = db.query(Quiz).filter(
        Quiz.lecture_id.in_(lecture_ids)
    ).order_by(Quiz.created_at.desc()).limit(5).all()

    if not quizzes:
        return 0.0

    quiz_scores = []
    for quiz in quizzes:
        total_q = db.query(QuizQuestion).filter(QuizQuestion.quiz_id == quiz.id).count()
        if total_q == 0:
            continue
        correct = db.query(QuizResponse).filter(
            QuizResponse.quiz_id == quiz.id,
            QuizResponse.student_id == student_id,
            QuizResponse.is_correct == True
        ).count()
        attempted = db.query(QuizResponse).filter(
            QuizResponse.quiz_id == quiz.id,
            QuizResponse.student_id == student_id
        ).count()
        if attempted > 0:
            quiz_scores.append((correct / total_q) * 100.0)

    if not quiz_scores:
        return 0.0
    if len(quiz_scores) == 1:
        return quiz_scores[0]

    mean_v = sum(quiz_scores) / len(quiz_scores)
    variance = sum((x - mean_v) ** 2 for x in quiz_scores) / len(quiz_scores)
    std_dev = math.sqrt(variance)
    confidence = max(0.0, min(100.0, mean_v - (std_dev * 1.5)))
    return round(confidence, 2)


def compute_assignment_mastery(student_id: int, topic_id: int, db: Session) -> float:
    """
    Compute assignment-based mastery for a student on a topic's course.
    Returns 0.0-100.0.
    """
    from app.models.models import Assignment, AssignmentSubmission, Section

    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        return 0.0

    sections = db.query(Section).filter(Section.course_id == topic.course_id).all()
    section_ids = [s.id for s in sections]
    if not section_ids:
        return 0.0

    assignments = db.query(Assignment).filter(
        Assignment.section_id.in_(section_ids),
        Assignment.is_published == True
    ).all()
    if not assignments:
        return 0.0

    assign_ids = [a.id for a in assignments]
    subs = db.query(AssignmentSubmission).filter(
        AssignmentSubmission.student_id == student_id,
        AssignmentSubmission.assignment_id.in_(assign_ids),
        AssignmentSubmission.status.in_(["graded", "evaluated", "completed"])
    ).all()

    if not subs:
        return 0.0

    scores = []
    for s in subs:
        a = s.assignment
        if not a:
            continue
        q_sum = sum(q.marks for q in a.questions) if a.questions else 0
        max_m = q_sum if q_sum > 0 else (a.total_marks or 100)
        if s.total_score is not None and max_m > 0:
            scores.append((s.total_score / max_m) * 100.0)

    return round(sum(scores) / len(scores), 2) if scores else 0.0
