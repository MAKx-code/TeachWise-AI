"""P1 targeted tests: tables, counts, idempotency, existing routes."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app, db
from sqlalchemy import inspect as sa_inspect

app = create_app()

PASS = '[PASS]'
FAIL = '[FAIL]'

def check(label, passed, detail=''):
    tag = PASS if passed else FAIL
    print(f'  {tag} {label}' + (f' — {detail}' if detail else ''))
    return passed

results = []

with app.app_context():
    tables = sa_inspect(db.engine).get_table_names()
    # 22 app tables + 1 alembic_version = 23
    results.append(check('23 tables in DB (22 app + alembic_version)', len(tables) == 23, f'{len(tables)} found'))

    from app.models import (Student, Enrollment, AttendanceRecord, AssignmentSubmission,
                             QuizResult, ExamMark, Question, LearningResource,
                             StudentFeedback, SyllabusUnit, CourseOutcome)

    results.append(check('45 students seeded', Student.query.count() == 45))
    results.append(check('45 enrollments seeded', Enrollment.query.count() == 45))
    results.append(check('1800 attendance records', AttendanceRecord.query.count() == 1800))
    results.append(check('225 assignment submissions', AssignmentSubmission.query.count() == 225))
    late = AssignmentSubmission.query.filter_by(is_late=True).count()
    results.append(check('Late submissions exist as warnings (is_late=True)', late >= 1, f'{late} late'))
    results.append(check('225 quiz results', QuizResult.query.count() == 225))
    results.append(check('90 exam marks', ExamMark.query.count() == 90))
    results.append(check('50 questions in bank', Question.query.count() == 50))
    results.append(check('15 learning resources', LearningResource.query.count() == 15))
    results.append(check('45 student feedback records', StudentFeedback.query.count() == 45))
    results.append(check('5 syllabus units', SyllabusUnit.query.count() == 5))
    results.append(check('5 course outcomes', CourseOutcome.query.count() == 5))

    # Idempotency: run seeder again, counts must not change
    import seed_academic
    seed_academic.seed_academic()
    results.append(check('Idempotency: student count unchanged after re-seed',
                          Student.query.count() == 45))
    results.append(check('Idempotency: attendance unchanged after re-seed',
                          AttendanceRecord.query.count() == 1800))

# Existing route regression
with app.test_client() as c:
    for route, name in [('/dashboard', 'Dashboard'), ('/lesson-studio', 'Lesson Studio'),
                        ('/teaching-materials', 'Teaching Materials'),
                        ('/assessment-studio', 'Assessment Studio'),
                        ('/student-analytics', 'Student Analytics'),
                        ('/learning-support', 'Learning Support'),
                        ('/faculty-analytics', 'Faculty Analytics'),
                        ('/api/health', 'Health API')]:
        r = c.get(route)
        results.append(check(f'Route {route} OK', r.status_code in (200, 302), f'HTTP {r.status_code}'))

passes = sum(1 for r in results if r)
fails = sum(1 for r in results if not r)
print(f'\nTotal: {len(results)}  |  PASS: {passes}  |  FAIL: {fails}')
