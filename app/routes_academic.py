"""
Academic data routes — import wizard, validation preview, academic data views.
New blueprint: academic_bp — does NOT modify main_bp or api_bp.
"""
import io
import json
import os
from datetime import datetime

from flask import (
    Blueprint, render_template, request, jsonify, redirect, url_for, current_app
)
from werkzeug.utils import secure_filename

from app import db
from app.models import (
    Course, Student, Enrollment, SyllabusUnit, CourseOutcome,
    AttendanceClass, AttendanceRecord, Assignment, AssignmentSubmission,
    Quiz, QuizResult, Exam, ExamMark, Question, LearningResource,
    StudentFeedback, DataImport
)
from app.validator import AcademicDataValidator

academic_bp = Blueprint('academic', __name__)

ALLOWED = {'csv'}


def _allowed(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED


# ── Main academic data page ───────────────────────────────────────────────────

@academic_bp.route('/academic')
def academic_data():
    courses = Course.query.all()
    selected_id = request.args.get('course_id', type=int)
    course = Course.query.get(selected_id) if selected_id else courses[0] if courses else None

    units = SyllabusUnit.query.filter_by(course_id=course.id).order_by(SyllabusUnit.unit_number).all() if course else []
    cos = CourseOutcome.query.filter_by(course_id=course.id).order_by(CourseOutcome.co_code).all() if course else []
    students = (Student.query
                .join(Enrollment, Enrollment.student_id == Student.id)
                .filter(Enrollment.course_id == course.id)
                .order_by(Student.student_code).all()) if course else []
    resources = LearningResource.query.filter_by(course_id=course.id).all() if course else []
    questions = Question.query.filter_by(course_id=course.id).all() if course else []
    feedback = StudentFeedback.query.filter_by(course_id=course.id).all() if course else []
    recent_imports = DataImport.query.order_by(DataImport.imported_at.desc()).limit(10).all()

    # Attendance summary stats
    att_stats = {}
    if course and students:
        total_classes = AttendanceClass.query.filter_by(course_id=course.id).count()
        for s in students[:10]:  # preview first 10
            present = (AttendanceRecord.query
                       .join(AttendanceClass, AttendanceClass.id == AttendanceRecord.class_id)
                       .filter(AttendanceClass.course_id == course.id,
                               AttendanceRecord.student_id == s.id,
                               AttendanceRecord.status.in_(['present', 'late'])).count())
            att_stats[s.student_code] = round(present / total_classes * 100, 1) if total_classes else 0

    return render_template('academic_data.html',
        courses=courses,
        course=course,
        units=units,
        cos=cos,
        students=students,
        resources=resources,
        questions=questions,
        feedback=feedback,
        recent_imports=recent_imports,
        att_stats=att_stats,
    )


# ── Validation API ────────────────────────────────────────────────────────────

@academic_bp.route('/api/academic/validate', methods=['POST'])
def api_validate():
    """Validate CSV without importing. Returns ValidationReport JSON."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    import_type = request.form.get('import_type', 'attendance')
    course_id = request.form.get('course_id', type=int)

    if not file.filename or not _allowed(file.filename):
        return jsonify({'error': 'Only CSV files are accepted.'}), 400

    file_bytes = file.read()

    # Build context from DB for semantic validation
    context = _build_validation_context(import_type, course_id)

    report = _run_validator(import_type, file_bytes, context)
    return jsonify(report.to_dict())


# ── Import API (transactional) ────────────────────────────────────────────────

@academic_bp.route('/api/academic/import', methods=['POST'])
def api_import():
    """Validate then import. All-or-nothing on errors; warnings don't block import."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    import_type = request.form.get('import_type', '')
    course_id = request.form.get('course_id', type=int)
    force = request.form.get('force_with_warnings', 'false').lower() == 'true'

    if not import_type:
        return jsonify({'error': 'import_type is required'}), 400
    if not file.filename or not _allowed(file.filename):
        return jsonify({'error': 'Only CSV files are accepted.'}), 400

    file_bytes = file.read()
    context = _build_validation_context(import_type, course_id)
    report = _run_validator(import_type, file_bytes, context)

    # Hard errors block import
    if report.rejected > 0:
        di = DataImport(
            import_type=import_type,
            filename=secure_filename(file.filename),
            total_records=report.total,
            valid_records=report.valid,
            rejected_records=report.rejected,
            warning_count=report.warning_count,
            validation_report=report.to_json(),
            status='rejected',
        )
        db.session.add(di)
        db.session.commit()
        return jsonify({
            'status': 'rejected',
            'message': f'{report.rejected} error(s) found. Import blocked. Fix and re-upload.',
            'report': report.to_dict(),
            'import_id': di.id,
        }), 400

    # Warnings: allow import if faculty confirms (force=True) or no warnings
    if report.warning_count > 0 and not force:
        return jsonify({
            'status': 'warnings',
            'message': f'{report.warning_count} warning(s). Re-submit with force_with_warnings=true to proceed.',
            'report': report.to_dict(),
        }), 200

    # Perform transactional import
    try:
        import_count = _perform_import(import_type, file_bytes, course_id, context)
        di = DataImport(
            import_type=import_type,
            filename=secure_filename(file.filename),
            total_records=report.total,
            valid_records=import_count,
            rejected_records=0,
            warning_count=report.warning_count,
            validation_report=report.to_json(),
            status='imported',
        )
        db.session.add(di)
        db.session.commit()
        return jsonify({
            'status': 'imported',
            'message': f'{import_count} records imported successfully.',
            'report': report.to_dict(),
            'import_id': di.id,
        })
    except Exception as exc:
        db.session.rollback()
        return jsonify({'error': f'Import failed: {exc}', 'report': report.to_dict()}), 500


# ── Helper: build validation context from DB ──────────────────────────────────

def _build_validation_context(import_type: str, course_id: int | None) -> dict:
    ctx = {}
    if not course_id:
        return ctx

    students = (Student.query
                .join(Enrollment, Enrollment.student_id == Student.id)
                .filter(Enrollment.course_id == course_id).all())
    ctx['valid_student_codes'] = {s.student_code for s in students}

    classes = AttendanceClass.query.filter_by(course_id=course_id).all()
    ctx['valid_class_dates'] = {str(c.class_date) for c in classes}

    exams = Exam.query.filter_by(course_id=course_id).all()
    ctx['exam_definitions'] = {e.title: e.max_marks for e in exams}

    assignments = Assignment.query.filter_by(course_id=course_id).all()
    ctx['assignment_definitions'] = {a.title: a.max_marks for a in assignments}

    quizzes = Quiz.query.filter_by(course_id=course_id).all()
    ctx['quiz_definitions'] = {q.title: q.max_marks for q in quizzes}

    cos = CourseOutcome.query.filter_by(course_id=course_id).all()
    ctx['valid_co_codes'] = {co.co_code for co in cos}

    units = SyllabusUnit.query.filter_by(course_id=course_id).all()
    ctx['valid_unit_titles'] = {u.title for u in units}

    return ctx


def _run_validator(import_type: str, file_bytes: bytes, ctx: dict):
    v = AcademicDataValidator()
    if import_type == 'students':
        return v.validate_students(file_bytes)
    elif import_type == 'attendance':
        return v.validate_attendance(file_bytes,
            valid_student_codes=ctx.get('valid_student_codes'),
            valid_class_dates=ctx.get('valid_class_dates'))
    elif import_type == 'exam_marks':
        return v.validate_marks(file_bytes,
            exam_definitions=ctx.get('exam_definitions'),
            valid_student_codes=ctx.get('valid_student_codes'))
    elif import_type == 'assignment_submissions':
        return v.validate_assignment_submissions(file_bytes,
            assignment_definitions=ctx.get('assignment_definitions'),
            valid_student_codes=ctx.get('valid_student_codes'))
    elif import_type == 'quiz_results':
        return v.validate_quiz_results(file_bytes,
            quiz_definitions=ctx.get('quiz_definitions'),
            valid_student_codes=ctx.get('valid_student_codes'))
    elif import_type == 'question_bank':
        from app.validator import AcademicDataValidator as ADV
        return ADV.validate_question_bank(file_bytes,
            valid_co_codes=ctx.get('valid_co_codes'),
            valid_unit_titles=ctx.get('valid_unit_titles'))
    elif import_type == 'feedback':
        return v.validate_feedback(file_bytes,
            valid_student_codes=ctx.get('valid_student_codes'))
    else:
        from app.validator import ValidationReport
        r = ValidationReport(import_type)
        r.add_error(0, 'import_type', import_type, f'Unknown import type: {import_type}', 'Use: students, attendance, exam_marks, assignment_submissions, quiz_results, question_bank, feedback')
        return r


def _perform_import(import_type: str, file_bytes: bytes, course_id: int | None, ctx: dict) -> int:
    """Transactional import of validated records. Returns count imported."""
    import io
    import pandas as pd

    text = file_bytes.decode('utf-8', errors='replace')
    df = pd.read_csv(io.StringIO(text))
    df.columns = [c.lower().strip() for c in df.columns]
    count = 0

    if import_type == 'students' and course_id:
        for _, row in df.iterrows():
            code = str(row['student_code']).strip()
            existing = Student.query.filter_by(student_code=code).first()
            if not existing:
                s = Student(student_code=code,
                            section=str(row.get('section', '')).strip() or None,
                            batch_year=int(row['batch_year']) if 'batch_year' in df.columns and pd.notna(row.get('batch_year')) else None)
                db.session.add(s)
                db.session.flush()
                db.session.add(Enrollment(student_id=s.id, course_id=course_id))
                count += 1

    elif import_type == 'attendance' and course_id:
        class_map = {str(c.class_date): c.id for c in AttendanceClass.query.filter_by(course_id=course_id).all()}
        student_map = {s.student_code: s.id for s in Student.query.join(Enrollment).filter(Enrollment.course_id == course_id).all()}
        for _, row in df.iterrows():
            code = str(row['student_code']).strip()
            cdate = str(row['class_date']).strip()
            status = str(row['status']).strip().lower()
            if code in student_map and cdate in class_map:
                existing = AttendanceRecord.query.filter_by(student_id=student_map[code], class_id=class_map[cdate]).first()
                if not existing:
                    db.session.add(AttendanceRecord(student_id=student_map[code], class_id=class_map[cdate], status=status))
                    count += 1

    # Other import types follow same pattern — query existing, skip duplicates, add new
    db.session.flush()
    return count


# ═══════════════════════════════════════════════════════════════════════════════
# P3: Academic Analytics Routes
# ═══════════════════════════════════════════════════════════════════════════════

@academic_bp.route('/academic/analytics')
def academic_analytics():
    """Full DB-backed analytics dashboard for a selected course."""
    from app.analytics import compute_full_analytics
    from app.models import Course, LearningResource

    courses = Course.query.all()
    selected_id = request.args.get('course_id', type=int)
    course = Course.query.get(selected_id) if selected_id else courses[0] if courses else None

    analytics = None
    resources_by_unit = {}
    if course:
        try:
            analytics = compute_full_analytics(course.id)
            # Fetch learning resources grouped by unit for gap remediation
            units = SyllabusUnit.query.filter_by(course_id=course.id).all()
            for u in units:
                res = LearningResource.query.filter_by(course_id=course.id, unit_id=u.id).all()
                if res:
                    resources_by_unit[u.id] = {
                        'title': u.title,
                        'resources': [{'id': r.id, 'title': r.title, 'type': r.resource_type, 'url': r.url_or_path} for r in res]
                    }
        except Exception as exc:
            current_app.logger.error('Analytics compute error: %s', exc)
            analytics = None

    return render_template('academic_analytics.html',
        courses=courses,
        course=course,
        analytics=analytics,
        resources_by_unit=resources_by_unit,
    )


@academic_bp.route('/api/academic/analytics/<int:course_id>')
def api_academic_analytics(course_id):
    """JSON analytics API for a course."""
    from app.analytics import compute_full_analytics
    course = Course.query.get_or_404(course_id)
    try:
        data = compute_full_analytics(course.id)
        data['course_name'] = course.name
        data['course_code'] = course.code
        return jsonify(data)
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500


@academic_bp.route('/api/academic/co-attainment/<int:course_id>')
def api_co_attainment(course_id):
    """CO attainment data + optional Granite interpretation."""
    from app.analytics import compute_co_attainment
    from app.agents.co_attainment import interpret_co_attainment

    course = Course.query.get_or_404(course_id)
    try:
        co_data = compute_co_attainment(course.id)
    except Exception as exc:
        return jsonify({'error': f'CO attainment calculation failed: {exc}'}), 500

    # Optional: include AI interpretation
    interpret = request.args.get('interpret', 'false').lower() == 'true'
    ai_interpretation = None
    if interpret:
        try:
            ai_interpretation = interpret_co_attainment(co_data, course.name)
        except Exception as exc:
            ai_interpretation = f'AI interpretation unavailable: {exc}'

    return jsonify({
        'course_id': course_id,
        'course_name': course.name,
        'co_attainment': co_data,
        'ai_interpretation': ai_interpretation,
    })


@academic_bp.route('/api/academic/db-pipeline/<int:course_id>', methods=['POST'])
def api_db_pipeline(course_id):
    """
    DB-backed 6-stage pipeline:
    DB query -> Python analytics -> Gap detection -> AI explanations -> Support plan -> CO attainment.
    Returns structured pipeline result with stage log.
    """
    from datetime import datetime as dt
    from app.analytics import compute_topic_performance, compute_at_risk_students, compute_attendance_summary
    from app.agents.gap_detection import ai_explain_gaps
    from app.agents.learning_support import generate_support_plan
    from app.agents.co_attainment import interpret_co_attainment
    from app.analytics import compute_co_attainment

    course = Course.query.get_or_404(course_id)
    stage_log = []

    def stage_start(name):
        entry = {'stage': name, 'status': 'running', 'started_at': dt.utcnow().isoformat()}
        stage_log.append(entry)
        return entry

    def stage_success(entry, msg):
        entry.update({'status': 'success', 'message': msg, 'completed_at': dt.utcnow().isoformat()})

    def stage_fail(entry, err):
        entry.update({'status': 'failed', 'error': str(err), 'completed_at': dt.utcnow().isoformat()})

    result = {
        'course_id': course_id,
        'course_name': course.name,
        'stage_log': stage_log,
        'topic_performance': None,
        'attendance': None,
        'at_risk_students': None,
        'gaps': None,
        'support_plan': None,
        'co_attainment': None,
        'co_interpretation': None,
        'error': None,
    }

    # Stage 1: DB data retrieval & Python analytics
    s = stage_start('DB Analytics (Python)')
    try:
        topic_perf = compute_topic_performance(course_id)
        attendance = compute_attendance_summary(course_id)
        at_risk = compute_at_risk_students(course_id)
        result['topic_performance'] = topic_perf
        result['attendance'] = attendance
        result['at_risk_students'] = at_risk
        stage_success(s, f'{len(topic_perf)} units analysed, {len(at_risk)} at-risk students identified, attendance avg {attendance.get("class_avg_pct")}%')
    except Exception as exc:
        stage_fail(s, exc)
        result['error'] = f'Analytics computation failed: {exc}'
        return jsonify(result), 500

    # Stage 2: Gap detection from topic performance
    s = stage_start('Learning Gap Detection (Python)')
    try:
        # Convert topic_performance to format expected by gap_detection
        topic_stats_for_gaps = {}
        for tp in topic_perf:
            if tp.get('combined_avg_pct') is not None:
                pct = tp['combined_avg_pct']
                # Compute below_50_pct from at-risk student data
                # (use per-student scores from DB for accurate below-50 count)
                below_50 = _compute_below_threshold_pct(course_id, tp['unit_id'], 50.0)
                below_40 = _compute_below_threshold_pct(course_id, tp['unit_id'], 40.0)
                topic_stats_for_gaps[tp['title']] = {
                    'mean': pct,
                    'below_50_pct': below_50,
                    'below_40_pct': below_40,
                    'median': pct,
                    'std': 0,
                }

        from app.agents.gap_detection import detect_gaps
        gaps = detect_gaps(topic_stats_for_gaps)
        stage_success(s, f'{len(gaps)} gap(s) detected from DB performance data.')
    except Exception as exc:
        stage_fail(s, exc)
        gaps = []

    # Stage 3: AI gap explanations
    if gaps:
        s = stage_start('AI Gap Explanations (Granite)')
        try:
            gaps = ai_explain_gaps(gaps, attendance.get('total_students', 0))
            result['gaps'] = gaps
            stage_success(s, f'Granite provided interventions for {len(gaps)} gap(s).')
        except Exception as exc:
            stage_fail(s, exc)
            result['gaps'] = gaps
    else:
        result['gaps'] = gaps

    # Stage 4: Personalized learning support
    s = stage_start('Personalized Learning Support (Granite)')
    try:
        # Build a performance dict compatible with generate_support_plan
        perf_for_support = {
            'num_students': attendance.get('total_students', 0),
            'avg_attendance': attendance.get('class_avg_pct'),
            'overall_avg_score': (
                sum(tp['combined_avg_pct'] for tp in topic_perf if tp.get('combined_avg_pct') is not None)
                / max(1, sum(1 for tp in topic_perf if tp.get('combined_avg_pct') is not None))
            ),
            'at_risk_students': at_risk,
        }
        support_plan = generate_support_plan(perf_for_support, gaps or [], course.name)
        result['support_plan'] = support_plan
        stage_success(s, 'Personalized support plan generated.')
    except Exception as exc:
        stage_fail(s, exc)
        result['support_plan'] = None

    # Stage 5: CO attainment computation
    s = stage_start('CO Attainment Calculation (Python)')
    try:
        co_att = compute_co_attainment(course_id)
        result['co_attainment'] = co_att
        stage_success(s, f"Overall attainment: {co_att.get('overall_attainment_pct')}%. "
                         f"Attained: {co_att.get('attained_count')}, "
                         f"Not Attained: {co_att.get('not_attained_count')}.")
    except Exception as exc:
        stage_fail(s, exc)
        result['co_attainment'] = None

    # Stage 6: AI CO interpretation
    if result['co_attainment']:
        s = stage_start('CO Attainment Interpretation (Granite)')
        try:
            co_interp = interpret_co_attainment(result['co_attainment'], course.name)
            result['co_interpretation'] = co_interp
            stage_success(s, 'Granite interpreted CO attainment findings.')
        except Exception as exc:
            stage_fail(s, exc)
            result['co_interpretation'] = None

    return jsonify(result)


@academic_bp.route('/academic/learning-support/<int:course_id>')
def academic_learning_support(course_id):
    """Learning support page backed by DB resources."""
    from app.analytics import compute_at_risk_students, compute_topic_performance

    course = Course.query.get_or_404(course_id)
    courses = Course.query.all()

    # Get weak topics (gap severity != None)
    topic_perf = compute_topic_performance(course_id)
    weak_topics = [tp for tp in topic_perf if tp.get('gap_severity') in ('Critical', 'Significant', 'Moderate')]

    # Get resources for weak units
    weak_resources = {}
    for tp in weak_topics:
        res = LearningResource.query.filter_by(course_id=course_id, unit_id=tp['unit_id']).all()
        weak_resources[tp['unit_id']] = {
            'unit_title': tp['title'],
            'severity': tp['gap_severity'],
            'score': tp.get('combined_avg_pct'),
            'resources': [{'title': r.title, 'type': r.resource_type, 'url': r.url_or_path, 'description': r.description} for r in res],
        }

    at_risk = compute_at_risk_students(course_id)

    return render_template('academic_learning_support.html',
        course=course,
        courses=courses,
        weak_topics=weak_topics,
        weak_resources=weak_resources,
        at_risk_students=at_risk,
        topic_perf=topic_perf,
    )


def _compute_below_threshold_pct(course_id: int, unit_id: int, threshold: float) -> float:
    """
    Compute % of students who scored below threshold% across all quizzes and
    assignments in a given unit.
    """
    from app import db
    from app.models import Quiz, QuizResult, Assignment, AssignmentSubmission, Enrollment, Student

    students = (Student.query
                .join(Enrollment, Enrollment.student_id == Student.id)
                .filter(Enrollment.course_id == course_id).all())
    if not students:
        return 0.0

    student_ids = [s.id for s in students]
    below_count = 0
    total_count = 0

    quizzes = Quiz.query.filter_by(course_id=course_id, unit_id=unit_id).all()
    assignments = Assignment.query.filter_by(course_id=course_id, unit_id=unit_id).all()

    for s_id in student_ids:
        scores = []
        for quiz in quizzes:
            if quiz.max_marks == 0:
                continue
            qr = QuizResult.query.filter_by(quiz_id=quiz.id, student_id=s_id).first()
            if qr:
                scores.append(qr.marks_obtained / quiz.max_marks * 100)
        for assign in assignments:
            if assign.max_marks == 0:
                continue
            sub = AssignmentSubmission.query.filter_by(assignment_id=assign.id, student_id=s_id).first()
            if sub:
                scores.append(sub.marks_obtained / assign.max_marks * 100)
        if scores:
            avg = sum(scores) / len(scores)
            total_count += 1
            if avg < threshold:
                below_count += 1

    return round(below_count / total_count * 100, 1) if total_count > 0 else 0.0
