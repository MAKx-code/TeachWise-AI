"""
app/analytics.py — TeachWise AI Academic Analytics Engine

All calculations are done in Python from the actual database.
Granite is never called here — this is deterministic computation only.

Exported functions:
    compute_co_attainment(course_id)         -> dict
    compute_topic_performance(course_id)     -> list[dict]
    compute_attendance_summary(course_id)    -> dict
    compute_at_risk_students(course_id)      -> list[dict]
    compute_full_analytics(course_id)        -> dict  (all four above)
"""

from __future__ import annotations
from sqlalchemy import func
from app import db
from app.models import (
    Student, Enrollment, CourseOutcome, SyllabusUnit, CoUnitMapping,
    AttendanceClass, AttendanceRecord,
    Quiz, QuizResult,
    Assignment, AssignmentSubmission,
    Exam, ExamMark,
    StudentFeedback,
)


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _enrolled_students(course_id: int) -> list:
    """Return Student objects enrolled in the course."""
    return (Student.query
            .join(Enrollment, Enrollment.student_id == Student.id)
            .filter(Enrollment.course_id == course_id)
            .order_by(Student.student_code)
            .all())


def _total_classes(course_id: int) -> int:
    return AttendanceClass.query.filter_by(course_id=course_id).count()


def _student_present_count(student_id: int, course_id: int) -> int:
    """Count classes where student was present or late for this course."""
    return (AttendanceRecord.query
            .join(AttendanceClass, AttendanceClass.id == AttendanceRecord.class_id)
            .filter(
                AttendanceClass.course_id == course_id,
                AttendanceRecord.student_id == student_id,
                AttendanceRecord.status.in_(['present', 'late'])
            ).count())


# ─────────────────────────────────────────────────────────────────────────────
# 1. Topic (unit) performance
# ─────────────────────────────────────────────────────────────────────────────

def compute_topic_performance(course_id: int) -> list[dict]:
    """
    For each syllabus unit, compute avg score % across all quizzes and
    assignment submissions linked to that unit.

    Returns list of:
      { unit_number, title, quiz_avg_pct, assignment_avg_pct,
        combined_avg_pct, student_count, gap_severity }
    """
    units = SyllabusUnit.query.filter_by(course_id=course_id).order_by(SyllabusUnit.unit_number).all()
    students = _enrolled_students(course_id)
    n_students = len(students)
    if not units or n_students == 0:
        return []

    student_ids = [s.id for s in students]
    results = []

    for unit in units:
        # Quizzes linked to this unit
        quizzes = Quiz.query.filter_by(course_id=course_id, unit_id=unit.id).all()
        quiz_pcts = []
        for quiz in quizzes:
            if quiz.max_marks == 0:
                continue
            rows = (db.session.query(func.avg(QuizResult.marks_obtained))
                    .filter(QuizResult.quiz_id == quiz.id,
                            QuizResult.student_id.in_(student_ids))
                    .scalar())
            if rows is not None:
                quiz_pcts.append(float(rows) / quiz.max_marks * 100)

        # Assignments linked to this unit
        assignments = Assignment.query.filter_by(course_id=course_id, unit_id=unit.id).all()
        assign_pcts = []
        for assign in assignments:
            if assign.max_marks == 0:
                continue
            rows = (db.session.query(func.avg(AssignmentSubmission.marks_obtained))
                    .filter(AssignmentSubmission.assignment_id == assign.id,
                            AssignmentSubmission.student_id.in_(student_ids))
                    .scalar())
            if rows is not None:
                assign_pcts.append(float(rows) / assign.max_marks * 100)

        quiz_avg = round(sum(quiz_pcts) / len(quiz_pcts), 1) if quiz_pcts else None
        assign_avg = round(sum(assign_pcts) / len(assign_pcts), 1) if assign_pcts else None

        all_pcts = quiz_pcts + assign_pcts
        combined_avg = round(sum(all_pcts) / len(all_pcts), 1) if all_pcts else None

        # Gap severity thresholds (configurable)
        if combined_avg is None:
            severity = 'Unknown'
        elif combined_avg < 50:
            severity = 'Critical'
        elif combined_avg < 65:
            severity = 'Significant'
        elif combined_avg < 75:
            severity = 'Moderate'
        else:
            severity = 'None'

        results.append({
            'unit_id': unit.id,
            'unit_number': unit.unit_number,
            'title': unit.title,
            'quiz_avg_pct': quiz_avg,
            'assignment_avg_pct': assign_avg,
            'combined_avg_pct': combined_avg,
            'student_count': n_students,
            'gap_severity': severity,
        })

    return results


# ─────────────────────────────────────────────────────────────────────────────
# 2. CO Attainment
# ─────────────────────────────────────────────────────────────────────────────

def compute_co_attainment(course_id: int) -> dict:
    """
    Compute attainment % for each Course Outcome.

    Attainment = average of topic performance for units mapped to this CO.
    Attainment level:
      >= 70%: Attained (level 3)
      >= 55%: Partially Attained (level 2)
      < 55%:  Not Attained (level 1)

    Returns:
      { outcomes: [{ co_code, statement, bloom_level, attainment_pct,
                     level, level_label, mapped_units }],
        overall_attainment_pct, attained_count, partially_count, not_attained_count }
    """
    cos = CourseOutcome.query.filter_by(course_id=course_id).order_by(CourseOutcome.co_code).all()
    topic_perf = compute_topic_performance(course_id)
    unit_perf_map = {tp['unit_id']: tp['combined_avg_pct'] for tp in topic_perf}

    outcomes = []
    for co in cos:
        # Find units mapped to this CO
        mappings = CoUnitMapping.query.filter_by(co_id=co.id).all()
        mapped_units = []
        pcts = []
        for m in mappings:
            unit = SyllabusUnit.query.get(m.unit_id)
            if unit:
                pct = unit_perf_map.get(unit.id)
                mapped_units.append({'title': unit.title, 'pct': pct})
                if pct is not None:
                    pcts.append(pct)

        att_pct = round(sum(pcts) / len(pcts), 1) if pcts else None

        if att_pct is None:
            level, label = 0, 'No Data'
        elif att_pct >= 70:
            level, label = 3, 'Attained'
        elif att_pct >= 55:
            level, label = 2, 'Partially Attained'
        else:
            level, label = 1, 'Not Attained'

        outcomes.append({
            'co_id': co.id,
            'co_code': co.co_code,
            'statement': co.statement,
            'bloom_level': co.bloom_level,
            'attainment_pct': att_pct,
            'level': level,
            'level_label': label,
            'mapped_units': mapped_units,
        })

    total_pcts = [o['attainment_pct'] for o in outcomes if o['attainment_pct'] is not None]
    overall_pct = round(sum(total_pcts) / len(total_pcts), 1) if total_pcts else None

    return {
        'outcomes': outcomes,
        'overall_attainment_pct': overall_pct,
        'attained_count': sum(1 for o in outcomes if o['level'] == 3),
        'partially_count': sum(1 for o in outcomes if o['level'] == 2),
        'not_attained_count': sum(1 for o in outcomes if o['level'] == 1),
        'no_data_count': sum(1 for o in outcomes if o['level'] == 0),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 3. Attendance Summary
# ─────────────────────────────────────────────────────────────────────────────

def compute_attendance_summary(course_id: int) -> dict:
    """
    Returns attendance statistics for the course.

    {
      total_classes, total_students, class_avg_pct,
      below_75_count, below_75_pct,
      distribution: { '>=90': n, '75-89': n, '60-74': n, '<60': n },
      student_attendance: [{ student_code, pct, section }]  -- sorted asc
    }
    """
    students = _enrolled_students(course_id)
    total_classes = _total_classes(course_id)
    n = len(students)

    if n == 0 or total_classes == 0:
        return {
            'total_classes': total_classes,
            'total_students': n,
            'class_avg_pct': None,
            'below_75_count': 0,
            'below_75_pct': 0,
            'distribution': {},
            'student_attendance': [],
        }

    student_atts = []
    total_pct_sum = 0.0
    for s in students:
        present = _student_present_count(s.id, course_id)
        pct = round(present / total_classes * 100, 1)
        total_pct_sum += pct
        student_atts.append({'student_code': s.student_code, 'pct': pct, 'section': s.section})

    student_atts.sort(key=lambda x: x['pct'])

    class_avg = round(total_pct_sum / n, 1)
    below_75 = [sa for sa in student_atts if sa['pct'] < 75]

    dist = {'>=90': 0, '75-89': 0, '60-74': 0, '<60': 0}
    for sa in student_atts:
        p = sa['pct']
        if p >= 90:
            dist['>=90'] += 1
        elif p >= 75:
            dist['75-89'] += 1
        elif p >= 60:
            dist['60-74'] += 1
        else:
            dist['<60'] += 1

    return {
        'total_classes': total_classes,
        'total_students': n,
        'class_avg_pct': class_avg,
        'below_75_count': len(below_75),
        'below_75_pct': round(len(below_75) / n * 100, 1),
        'distribution': dist,
        'student_attendance': student_atts,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 4. At-Risk Students
# ─────────────────────────────────────────────────────────────────────────────

# Configurable thresholds
AT_RISK_ATT_THRESHOLD = 60.0    # attendance < 60% → at risk
AT_RISK_SCORE_THRESHOLD = 50.0  # combined avg score < 50% → at risk


def compute_at_risk_students(course_id: int) -> list[dict]:
    """
    Identify students at risk based on:
    - Attendance < AT_RISK_ATT_THRESHOLD, OR
    - Average quiz/assignment score < AT_RISK_SCORE_THRESHOLD across topics.

    Returns list of:
      { student_code, section, attendance_pct, avg_score_pct, reasons, priority }
    """
    students = _enrolled_students(course_id)
    total_classes = _total_classes(course_id)
    quizzes = Quiz.query.filter_by(course_id=course_id).all()
    assignments = Assignment.query.filter_by(course_id=course_id).all()
    at_risk = []

    for s in students:
        reasons = []

        # Attendance
        att_pct = 0.0
        if total_classes > 0:
            present = _student_present_count(s.id, course_id)
            att_pct = round(present / total_classes * 100, 1)
        if att_pct < AT_RISK_ATT_THRESHOLD:
            reasons.append(f'Attendance {att_pct}% is below {AT_RISK_ATT_THRESHOLD}% threshold')

        # Average quiz score
        quiz_scores = []
        for quiz in quizzes:
            if quiz.max_marks == 0:
                continue
            qr = QuizResult.query.filter_by(quiz_id=quiz.id, student_id=s.id).first()
            if qr:
                quiz_scores.append(qr.marks_obtained / quiz.max_marks * 100)

        # Average assignment score
        assign_scores = []
        for assign in assignments:
            if assign.max_marks == 0:
                continue
            sub = AssignmentSubmission.query.filter_by(assignment_id=assign.id, student_id=s.id).first()
            if sub:
                assign_scores.append(sub.marks_obtained / assign.max_marks * 100)

        all_scores = quiz_scores + assign_scores
        avg_score_pct = round(sum(all_scores) / len(all_scores), 1) if all_scores else None

        if avg_score_pct is not None and avg_score_pct < AT_RISK_SCORE_THRESHOLD:
            reasons.append(f'Average score {avg_score_pct}% is below {AT_RISK_SCORE_THRESHOLD}% threshold')

        if reasons:
            # Priority: both risks = High; one risk = Medium
            priority = 'High' if len(reasons) >= 2 else 'Medium'
            at_risk.append({
                'student_code': s.student_code,
                'section': s.section,
                'attendance_pct': att_pct,
                'avg_score_pct': avg_score_pct,
                'reasons': reasons,
                'priority': priority,
            })

    # Sort: High priority first, then by score asc
    at_risk.sort(key=lambda x: (0 if x['priority'] == 'High' else 1, x['avg_score_pct'] or 999))
    return at_risk


# ─────────────────────────────────────────────────────────────────────────────
# 5. Full analytics bundle
# ─────────────────────────────────────────────────────────────────────────────

def compute_full_analytics(course_id: int) -> dict:
    """
    Compute all analytics for a course in one call.
    Returns:
      { topic_performance, co_attainment, attendance, at_risk_students,
        course_id, computed_at }
    """
    from datetime import datetime
    return {
        'course_id': course_id,
        'computed_at': datetime.utcnow().isoformat(),
        'topic_performance': compute_topic_performance(course_id),
        'co_attainment': compute_co_attainment(course_id),
        'attendance': compute_attendance_summary(course_id),
        'at_risk_students': compute_at_risk_students(course_id),
    }
