from datetime import datetime
from app import db


# ═══════════════════════════════════════════════════════════════════════════════
# EXISTING MODELS — unchanged
# ═══════════════════════════════════════════════════════════════════════════════

class Course(db.Model):
    __tablename__ = 'courses'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    code = db.Column(db.String(20), nullable=False)
    semester = db.Column(db.String(20))
    student_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # New optional columns (added via migration)
    description = db.Column(db.Text)
    year = db.Column(db.Integer)
    # Relationships
    lessons = db.relationship('LessonPlan', backref='course', lazy=True)
    assessments = db.relationship('Assessment', backref='course', lazy=True)
    units = db.relationship('SyllabusUnit', backref='course', lazy=True, order_by='SyllabusUnit.unit_number')
    outcomes = db.relationship('CourseOutcome', backref='course', lazy=True, order_by='CourseOutcome.co_code')


class LessonPlan(db.Model):
    __tablename__ = 'lesson_plans'
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    topic = db.Column(db.String(200), nullable=False)
    duration = db.Column(db.String(50))
    student_level = db.Column(db.String(50))
    course_outcomes = db.Column(db.Text)
    teaching_approach = db.Column(db.Text)
    generated_plan = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    approved = db.Column(db.Boolean, default=False)
    # New optional column (migration)
    unit_id = db.Column(db.Integer, db.ForeignKey('syllabus_units.id'), nullable=True)


class TeachingMaterial(db.Model):
    __tablename__ = 'teaching_materials'
    id = db.Column(db.Integer, primary_key=True)
    course_name = db.Column(db.String(200))
    topic = db.Column(db.String(200), nullable=False)
    difficulty = db.Column(db.String(20))
    material_type = db.Column(db.String(50))
    content = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    approved = db.Column(db.Boolean, default=False)


class Assessment(db.Model):
    __tablename__ = 'assessments'
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=True)
    topic = db.Column(db.String(200), nullable=False)
    difficulty = db.Column(db.String(20))
    question_types = db.Column(db.String(200))
    num_questions = db.Column(db.Integer, default=5)
    content = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    approved = db.Column(db.Boolean, default=False)
    # New optional columns (migration)
    unit_id = db.Column(db.Integer, db.ForeignKey('syllabus_units.id'), nullable=True)
    co_codes = db.Column(db.String(200))


class AnalysisSession(db.Model):
    __tablename__ = 'analysis_sessions'
    id = db.Column(db.Integer, primary_key=True)
    course_name = db.Column(db.String(200))
    filename = db.Column(db.String(200))
    num_students = db.Column(db.Integer)
    avg_attendance = db.Column(db.Float)
    avg_score = db.Column(db.Float)
    performance_data = db.Column(db.Text)   # JSON
    gap_analysis = db.Column(db.Text)       # JSON
    support_plan = db.Column(db.Text)       # JSON
    stage_log = db.Column(db.Text)          # JSON
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # New optional column (migration)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=True)


# ═══════════════════════════════════════════════════════════════════════════════
# NEW ACADEMIC MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class Student(db.Model):
    __tablename__ = 'students'
    id = db.Column(db.Integer, primary_key=True)
    student_code = db.Column(db.String(10), nullable=False, unique=True)   # S001
    section = db.Column(db.String(10))
    batch_year = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    enrollments = db.relationship('Enrollment', backref='student', lazy=True)


class Enrollment(db.Model):
    __tablename__ = 'enrollments'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    enrolled_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    __table_args__ = (db.UniqueConstraint('student_id', 'course_id', name='uq_enrollment'),)


class SyllabusUnit(db.Model):
    __tablename__ = 'syllabus_units'
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    unit_number = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint('course_id', 'unit_number', name='uq_unit'),)


class CourseOutcome(db.Model):
    __tablename__ = 'course_outcomes'
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    co_code = db.Column(db.String(10), nullable=False)   # CO1
    statement = db.Column(db.Text, nullable=False)
    bloom_level = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint('course_id', 'co_code', name='uq_co'),)


class CoUnitMapping(db.Model):
    __tablename__ = 'co_unit_mappings'
    id = db.Column(db.Integer, primary_key=True)
    co_id = db.Column(db.Integer, db.ForeignKey('course_outcomes.id'), nullable=False)
    unit_id = db.Column(db.Integer, db.ForeignKey('syllabus_units.id'), nullable=False)
    __table_args__ = (db.UniqueConstraint('co_id', 'unit_id', name='uq_co_unit'),)


class AttendanceClass(db.Model):
    __tablename__ = 'attendance_classes'
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    unit_id = db.Column(db.Integer, db.ForeignKey('syllabus_units.id'), nullable=True)
    class_date = db.Column(db.Date, nullable=False)
    topic = db.Column(db.String(200))
    __table_args__ = (db.UniqueConstraint('course_id', 'class_date', name='uq_class'),)


class AttendanceRecord(db.Model):
    __tablename__ = 'attendance_records'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('attendance_classes.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False)   # present/absent/late/excused
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    __table_args__ = (db.UniqueConstraint('student_id', 'class_id', name='uq_attendance'),)


class Assignment(db.Model):
    __tablename__ = 'assignments'
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    unit_id = db.Column(db.Integer, db.ForeignKey('syllabus_units.id'), nullable=True)
    title = db.Column(db.String(200), nullable=False)
    max_marks = db.Column(db.Float, nullable=False)
    due_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class AssignmentSubmission(db.Model):
    __tablename__ = 'assignment_submissions'
    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignments.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    marks_obtained = db.Column(db.Float, nullable=False)
    submitted_at = db.Column(db.DateTime)
    is_late = db.Column(db.Boolean, nullable=False, default=False)   # warning, not rejection
    __table_args__ = (db.UniqueConstraint('assignment_id', 'student_id', name='uq_submission'),)


class Quiz(db.Model):
    __tablename__ = 'quizzes'
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    unit_id = db.Column(db.Integer, db.ForeignKey('syllabus_units.id'), nullable=True)
    title = db.Column(db.String(200), nullable=False)
    max_marks = db.Column(db.Float, nullable=False)
    quiz_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class QuizResult(db.Model):
    __tablename__ = 'quiz_results'
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    marks_obtained = db.Column(db.Float, nullable=False)
    attempted_at = db.Column(db.DateTime)
    __table_args__ = (db.UniqueConstraint('quiz_id', 'student_id', name='uq_quiz_result'),)


class Exam(db.Model):
    __tablename__ = 'exams'
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    exam_type = db.Column(db.String(20), nullable=False)   # internal/mid/end
    title = db.Column(db.String(200), nullable=False)
    max_marks = db.Column(db.Float, nullable=False)
    exam_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ExamMark(db.Model):
    __tablename__ = 'exam_marks'
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exams.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    marks_obtained = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    __table_args__ = (db.UniqueConstraint('exam_id', 'student_id', name='uq_exam_mark'),)


class Question(db.Model):
    __tablename__ = 'questions'
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    unit_id = db.Column(db.Integer, db.ForeignKey('syllabus_units.id'), nullable=True)
    co_id = db.Column(db.Integer, db.ForeignKey('course_outcomes.id'), nullable=True)
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(20), nullable=False)   # MCQ/Short/Long/Coding
    difficulty = db.Column(db.String(20), nullable=False)
    bloom_level = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class LearningResource(db.Model):
    __tablename__ = 'learning_resources'
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    unit_id = db.Column(db.Integer, db.ForeignKey('syllabus_units.id'), nullable=True)
    title = db.Column(db.String(200), nullable=False)
    resource_type = db.Column(db.String(50), nullable=False)   # video/pdf/link/textbook
    url_or_path = db.Column(db.String(500))
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class StudentFeedback(db.Model):
    __tablename__ = 'student_feedback'
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=True)  # optional anonymity
    week_number = db.Column(db.Integer)
    rating = db.Column(db.Integer, nullable=False)   # 1–5
    comments = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class DataImport(db.Model):
    __tablename__ = 'data_imports'
    id = db.Column(db.Integer, primary_key=True)
    import_type = db.Column(db.String(50), nullable=False)
    filename = db.Column(db.String(200))
    total_records = db.Column(db.Integer, nullable=False)
    valid_records = db.Column(db.Integer, nullable=False)
    rejected_records = db.Column(db.Integer, nullable=False)
    warning_count = db.Column(db.Integer, nullable=False, default=0)
    validation_report = db.Column(db.Text, nullable=False)   # JSON
    status = db.Column(db.String(20), nullable=False, default='pending')
    imported_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


# ═══════════════════════════════════════════════════════════════════════════════
# SEED FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def seed_demo_data():
    """Seed initial demo courses if DB is empty. Idempotent."""
    if Course.query.count() == 0:
        demo_courses = [
            Course(name='Data Structures & Algorithms', code='CS201', semester='Sem 3', student_count=45),
            Course(name='Database Management Systems', code='CS301', semester='Sem 5', student_count=38),
            Course(name='Object-Oriented Programming', code='CS101', semester='Sem 1', student_count=52),
            Course(name='Computer Networks', code='CS401', semester='Sem 7', student_count=30),
        ]
        db.session.add_all(demo_courses)
        db.session.commit()
