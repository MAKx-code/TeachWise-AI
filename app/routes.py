"""
Flask routes — main pages + API endpoints.
"""
import os
import json
import csv
import io
import pandas as pd
from datetime import datetime
from flask import (
    Blueprint, render_template, request, jsonify,
    redirect, url_for, flash, send_file, current_app
)
from werkzeug.utils import secure_filename

from app import db
from app.models import Course, LessonPlan, TeachingMaterial, Assessment, AnalysisSession
from app.agents.lesson_planning import generate_lesson_plan
from app.agents.teaching_material import generate_material
from app.agents.assessment import generate_assessment
from app.pipeline import run_analysis_pipeline
from app.granite import test_connection

main_bp = Blueprint('main', __name__)
api_bp = Blueprint('api', __name__)

ALLOWED_EXTENSIONS = {'csv'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN PAGES
# ═══════════════════════════════════════════════════════════════════════════════

@main_bp.route('/')
def index():
    return redirect(url_for('main.dashboard'))


@main_bp.route('/dashboard')
def dashboard():
    from app.models import Student, Enrollment
    courses = Course.query.order_by(Course.created_at.desc()).all()
    recent_lessons = LessonPlan.query.order_by(LessonPlan.created_at.desc()).limit(5).all()
    recent_assessments = Assessment.query.order_by(Assessment.created_at.desc()).limit(5).all()
    recent_analysis = AnalysisSession.query.order_by(AnalysisSession.created_at.desc()).limit(3).all()

    # Live DB student count
    db_student_count = Student.query.count()
    total_students = db_student_count if db_student_count > 0 else sum(c.student_count for c in courses)
    total_lessons = LessonPlan.query.count()
    total_assessments = Assessment.query.count()

    # Aggregate at-risk from CSV analysis sessions
    total_at_risk = 0
    gap_alerts = []
    for session in AnalysisSession.query.all():
        if session.performance_data:
            try:
                perf = json.loads(session.performance_data)
                at_risk = perf.get('at_risk_students', [])
                total_at_risk += len(at_risk)
            except Exception:
                pass
        if session.gap_analysis:
            try:
                gaps = json.loads(session.gap_analysis)
                for g in gaps:
                    if g.get('severity') in ('Critical', 'Significant'):
                        gap_alerts.append({
                            'course': session.course_name,
                            'topic': g['topic'],
                            'severity': g['severity'],
                            'mean_score': g['mean_score'],
                        })
            except Exception:
                pass

    # Also add DB-computed gap alerts from CS201 (if seeded)
    try:
        from app.analytics import compute_topic_performance
        cs201 = Course.query.filter_by(code='CS201').first()
        if cs201:
            tp = compute_topic_performance(cs201.id)
            for t in tp:
                if t.get('gap_severity') in ('Critical', 'Significant') and t.get('combined_avg_pct'):
                    gap_alerts.append({
                        'course': cs201.name,
                        'topic': t['title'],
                        'severity': t['gap_severity'],
                        'mean_score': t['combined_avg_pct'],
                    })
    except Exception:
        pass

    # CO attainment summary for dashboard
    co_summary = None
    try:
        from app.analytics import compute_co_attainment
        cs201 = Course.query.filter_by(code='CS201').first()
        if cs201:
            co_summary = compute_co_attainment(cs201.id)
    except Exception:
        pass

    return render_template('dashboard.html',
        courses=courses,
        recent_lessons=recent_lessons,
        recent_assessments=recent_assessments,
        recent_analysis=recent_analysis,
        total_students=total_students,
        total_lessons=total_lessons,
        total_assessments=total_assessments,
        total_at_risk=total_at_risk,
        gap_alerts=gap_alerts[:5],
        co_summary=co_summary,
    )


@main_bp.route('/lesson-studio')
def lesson_studio():
    courses = Course.query.all()
    recent = LessonPlan.query.order_by(LessonPlan.created_at.desc()).limit(10).all()
    return render_template('lesson_studio.html', courses=courses, recent=recent)


@main_bp.route('/teaching-materials')
def teaching_materials():
    courses = Course.query.all()
    recent = TeachingMaterial.query.order_by(TeachingMaterial.created_at.desc()).limit(10).all()
    return render_template('teaching_materials.html', courses=courses, recent=recent)


@main_bp.route('/assessment-studio')
def assessment_studio():
    courses = Course.query.all()
    recent = Assessment.query.order_by(Assessment.created_at.desc()).limit(10).all()
    return render_template('assessment_studio.html', courses=courses, recent=recent)


@main_bp.route('/student-analytics')
def student_analytics():
    sessions = AnalysisSession.query.order_by(AnalysisSession.created_at.desc()).all()
    return render_template('student_analytics.html', sessions=sessions)


@main_bp.route('/learning-support')
def learning_support():
    sessions = AnalysisSession.query.order_by(AnalysisSession.created_at.desc()).all()
    latest_session = sessions[0] if sessions else None
    support_plan = None
    gaps = None
    performance = None
    stage_log = None
    if latest_session:
        if latest_session.support_plan:
            try:
                support_plan = json.loads(latest_session.support_plan)
            except Exception:
                pass
        if latest_session.gap_analysis:
            try:
                gaps = json.loads(latest_session.gap_analysis)
            except Exception:
                pass
        if latest_session.performance_data:
            try:
                performance = json.loads(latest_session.performance_data)
            except Exception:
                pass
        if latest_session.stage_log:
            try:
                stage_log = json.loads(latest_session.stage_log)
            except Exception:
                pass
    return render_template('learning_support.html',
        sessions=sessions,
        latest_session=latest_session,
        support_plan=support_plan,
        gaps=gaps,
        performance=performance,
        stage_log=stage_log,
    )


@main_bp.route('/faculty-analytics')
def faculty_analytics():
    sessions = AnalysisSession.query.order_by(AnalysisSession.created_at.desc()).all()
    latest_session = sessions[0] if sessions else None
    performance = None
    gaps = None
    db_analytics = None

    if latest_session:
        if latest_session.performance_data:
            try:
                performance = json.loads(latest_session.performance_data)
            except Exception:
                pass
        if latest_session.gap_analysis:
            try:
                gaps = json.loads(latest_session.gap_analysis)
            except Exception:
                pass

    # When no CSV session exists, build performance/gaps from DB analytics (CS201)
    if performance is None:
        try:
            from app.analytics import compute_full_analytics, compute_topic_performance
            from app.agents.gap_detection import detect_gaps
            cs201 = Course.query.filter_by(code='CS201').first()
            if cs201:
                db_analytics = compute_full_analytics(cs201.id)
                att = db_analytics['attendance']
                tp = db_analytics['topic_performance']
                at_risk = db_analytics['at_risk_students']

                # Build topic_stats compatible with gap_detection.detect_gaps()
                topic_stats = {}
                for t in tp:
                    if t.get('combined_avg_pct') is not None:
                        topic_stats[t['title']] = {
                            'mean': t['combined_avg_pct'],
                            'below_50_pct': 0,
                            'below_40_pct': 0,
                            'median': t['combined_avg_pct'],
                            'std': 0,
                        }

                # Build performance dict matching template expectations
                performance = {
                    'num_students': att.get('total_students', 0),
                    'avg_attendance': att.get('class_avg_pct'),
                    'overall_avg_score': round(
                        sum(t['combined_avg_pct'] for t in tp if t.get('combined_avg_pct') is not None)
                        / max(1, sum(1 for t in tp if t.get('combined_avg_pct') is not None)), 1
                    ) if tp else None,
                    'attendance_distribution': {
                        'below_60': att['distribution'].get('<60', 0),
                        '60_to_75': att['distribution'].get('60-74', 0),
                        '75_to_90': att['distribution'].get('75-89', 0),
                        'above_90': att['distribution'].get('>=90', 0),
                    },
                    'topic_stats': topic_stats,
                    'available_topic_columns': [t['title'] for t in tp],
                    'at_risk_students': [
                        {'student_id': s['student_code'], 'reasons': s['reasons'],
                         'attendance': s['attendance_pct'], 'scores': {}}
                        for s in at_risk
                    ],
                    'score_distribution': {},
                    'per_student': [],
                    '_source': 'db_cs201',
                }

                # Detect gaps from DB topic performance
                try:
                    gaps = detect_gaps(topic_stats)
                except Exception:
                    pass
        except Exception:
            pass

    return render_template('faculty_analytics.html',
        sessions=sessions,
        latest_session=latest_session,
        performance=performance,
        gaps=gaps,
        db_analytics=db_analytics,
    )


@main_bp.route('/analysis/<int:session_id>')
def analysis_detail(session_id):
    session = AnalysisSession.query.get_or_404(session_id)
    performance = None
    gaps = None
    support_plan = None
    stage_log = None
    try:
        performance = json.loads(session.performance_data) if session.performance_data else None
        gaps = json.loads(session.gap_analysis) if session.gap_analysis else None
        support_plan = json.loads(session.support_plan) if session.support_plan else None
        stage_log = json.loads(session.stage_log) if session.stage_log else None
    except Exception:
        pass
    return render_template('analysis_detail.html',
        session=session,
        performance=performance,
        gaps=gaps,
        support_plan=support_plan,
        stage_log=stage_log,
    )


@main_bp.route('/demo-csv')
def download_demo_csv():
    """Serve the synthetic demo CSV."""
    demo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'demo_students.csv')
    if os.path.exists(demo_path):
        return send_file(demo_path, as_attachment=True, download_name='demo_students.csv')
    # Generate on the fly if missing
    output = _generate_demo_csv_content()
    return send_file(
        io.BytesIO(output.encode()),
        as_attachment=True,
        download_name='demo_students.csv',
        mimetype='text/csv',
    )


def _generate_demo_csv_content():
    import random
    random.seed(42)
    rows = ['student_id,attendance_pct,quiz_basics,quiz_loops,quiz_arrays,assignment_score']
    for i in range(1, 41):
        sid = f'S{i:03d}'
        # Intentionally create varied performance for demo interest
        profile = random.choice(['strong', 'average', 'weak', 'average', 'strong'])
        if profile == 'strong':
            att = random.uniform(85, 98)
            basics = random.uniform(72, 95)
            loops = random.uniform(68, 92)
            arrays = random.uniform(65, 90)
            assign = random.uniform(75, 95)
        elif profile == 'average':
            att = random.uniform(65, 85)
            basics = random.uniform(50, 75)
            loops = random.uniform(45, 72)
            arrays = random.uniform(40, 70)
            assign = random.uniform(55, 80)
        else:  # weak
            att = random.uniform(40, 65)
            basics = random.uniform(25, 52)
            loops = random.uniform(20, 48)
            arrays = random.uniform(15, 45)
            assign = random.uniform(30, 55)
        rows.append(f'{sid},{att:.1f},{basics:.1f},{loops:.1f},{arrays:.1f},{assign:.1f}')
    return '\n'.join(rows)


# ═══════════════════════════════════════════════════════════════════════════════
# API ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@api_bp.route('/health')
def health():
    return jsonify({'status': 'ok', 'timestamp': datetime.utcnow().isoformat()})


@api_bp.route('/granite/test')
def granite_test():
    result = test_connection()
    return jsonify(result)


@api_bp.route('/lesson-plan', methods=['POST'])
def api_lesson_plan():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    # Input validation
    subject = _safe_str(data.get('subject', ''), 'Subject', 200)
    topic = _safe_str(data.get('topic', ''), 'Topic', 200)
    outcomes = _safe_str(data.get('course_outcomes', ''), 'Course outcomes', 1000)
    duration = _safe_str(data.get('duration', '60 minutes'), 'Duration', 50)
    level = _safe_str(data.get('student_level', 'Undergraduate'), 'Student level', 50)
    approach = _safe_str(data.get('teaching_approach', ''), 'Teaching approach', 500)

    if isinstance(subject, dict): return jsonify(subject), 400
    if isinstance(topic, dict): return jsonify(topic), 400
    if isinstance(outcomes, dict): return jsonify(outcomes), 400

    try:
        plan_text = generate_lesson_plan(subject, topic, outcomes, duration, level, approach)
    except Exception as exc:
        return jsonify({'error': f'Granite unavailable: {str(exc)}'}), 503

    # Save to DB
    course = Course.query.filter(Course.name.ilike(f'%{subject}%')).first()
    lesson = LessonPlan(
        course_id=course.id if course else Course.query.first().id,
        topic=topic,
        duration=duration,
        student_level=level,
        course_outcomes=outcomes,
        teaching_approach=approach,
        generated_plan=plan_text,
    )
    db.session.add(lesson)
    db.session.commit()

    return jsonify({'id': lesson.id, 'plan': plan_text, 'status': 'success'})


@api_bp.route('/lesson-plan/<int:lesson_id>/approve', methods=['POST'])
def api_approve_lesson(lesson_id):
    lesson = LessonPlan.query.get_or_404(lesson_id)
    lesson.approved = True
    db.session.commit()
    return jsonify({'status': 'approved', 'id': lesson_id})


@api_bp.route('/teaching-material', methods=['POST'])
def api_teaching_material():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    course_name = _safe_str(data.get('course_name', ''), 'Course', 200)
    topic = _safe_str(data.get('topic', ''), 'Topic', 200)
    difficulty = data.get('difficulty', 'Medium')
    material_type = data.get('material_type', 'lecture_notes')

    if isinstance(topic, dict): return jsonify(topic), 400
    if difficulty not in ('Easy', 'Medium', 'Hard'):
        return jsonify({'error': 'Difficulty must be Easy, Medium, or Hard'}), 400

    try:
        content = generate_material(course_name, topic, difficulty, material_type)
    except Exception as exc:
        return jsonify({'error': f'Granite unavailable: {str(exc)}'}), 503

    mat = TeachingMaterial(
        course_name=course_name,
        topic=topic,
        difficulty=difficulty,
        material_type=material_type,
        content=content,
    )
    db.session.add(mat)
    db.session.commit()

    return jsonify({'id': mat.id, 'content': content, 'status': 'success'})


@api_bp.route('/teaching-material/<int:mat_id>/approve', methods=['POST'])
def api_approve_material(mat_id):
    mat = TeachingMaterial.query.get_or_404(mat_id)
    mat.approved = True
    db.session.commit()
    return jsonify({'status': 'approved', 'id': mat_id})


@api_bp.route('/assessment', methods=['POST'])
def api_assessment():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    topic = _safe_str(data.get('topic', ''), 'Topic', 200)
    difficulty = data.get('difficulty', 'Medium')
    question_types = data.get('question_types', ['MCQ'])
    num_questions = int(data.get('num_questions', 5))
    course_outcome = _safe_str(data.get('course_outcome', ''), 'Course outcome', 500)

    if isinstance(topic, dict): return jsonify(topic), 400
    if difficulty not in ('Easy', 'Medium', 'Hard'):
        return jsonify({'error': 'Difficulty must be Easy, Medium, or Hard'}), 400
    if not isinstance(question_types, list) or not question_types:
        return jsonify({'error': 'question_types must be a non-empty list'}), 400
    num_questions = max(1, min(20, num_questions))

    try:
        result = generate_assessment(topic, difficulty, question_types, num_questions, course_outcome)
    except Exception as exc:
        return jsonify({'error': f'Granite unavailable: {str(exc)}'}), 503

    if 'error' in result and not result.get('questions'):
        return jsonify({'error': result['error'], 'raw': result.get('raw_output', '')}), 500

    # Save
    assessment = Assessment(
        topic=topic,
        difficulty=difficulty,
        question_types=', '.join(question_types),
        num_questions=num_questions,
        content=json.dumps(result),
    )
    db.session.add(assessment)
    db.session.commit()
    result['id'] = assessment.id

    return jsonify({'status': 'success', 'assessment': result})


@api_bp.route('/assessment/<int:assess_id>/approve', methods=['POST'])
def api_approve_assessment(assess_id):
    assess = Assessment.query.get_or_404(assess_id)
    assess.approved = True
    db.session.commit()
    return jsonify({'status': 'approved', 'id': assess_id})


@api_bp.route('/upload-csv', methods=['POST'])
def api_upload_csv():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    raw_course_name = request.form.get('course_name', 'Engineering Course')
    course_name = str(raw_course_name).strip()[:200] if raw_course_name else 'Engineering Course'

    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    if not allowed_file(file.filename):
        return jsonify({'error': 'Only CSV files are allowed'}), 400

    # Read CSV into DataFrame
    try:
        content = file.read().decode('utf-8')
        # Treat CSV as untrusted data (not system instructions)
        df = pd.read_csv(io.StringIO(content))
    except Exception as exc:
        return jsonify({'error': f'Could not read CSV: {exc}'}), 400

    # Run pipeline
    try:
        result = run_analysis_pipeline(df, course_name)
    except Exception as exc:
        return jsonify({'error': f'Pipeline error: {exc}'}), 500

    if result.get('error'):
        return jsonify({
            'error': result['error'],
            'stage_log': result.get('stage_log', []),
        }), 400

    # Save session to DB
    session_obj = AnalysisSession(
        course_name=course_name,
        filename=secure_filename(file.filename),
        num_students=result['performance']['num_students'] if result['performance'] else 0,
        avg_attendance=result['performance']['avg_attendance'] if result['performance'] else None,
        avg_score=result['performance']['overall_avg_score'] if result['performance'] else None,
        performance_data=json.dumps(result['performance']) if result['performance'] else None,
        gap_analysis=json.dumps(result['gaps']) if result['gaps'] is not None else None,
        support_plan=json.dumps(result['support_plan']) if result['support_plan'] else None,
        stage_log=json.dumps(result['stage_log']),
    )
    db.session.add(session_obj)
    db.session.commit()

    return jsonify({
        'status': 'success',
        'session_id': session_obj.id,
        'performance': result['performance'],
        'ai_interpretation': result.get('ai_interpretation'),
        'gaps': result['gaps'],
        'support_plan': result['support_plan'],
        'stage_log': result['stage_log'],
    })


@api_bp.route('/session/<int:session_id>')
def api_get_session(session_id):
    session = AnalysisSession.query.get_or_404(session_id)
    return jsonify({
        'id': session.id,
        'course_name': session.course_name,
        'num_students': session.num_students,
        'avg_attendance': session.avg_attendance,
        'avg_score': session.avg_score,
        'performance': json.loads(session.performance_data) if session.performance_data else None,
        'gaps': json.loads(session.gap_analysis) if session.gap_analysis else None,
        'support_plan': json.loads(session.support_plan) if session.support_plan else None,
        'stage_log': json.loads(session.stage_log) if session.stage_log else None,
        'created_at': session.created_at.isoformat(),
    })


# ─── Input sanitization helpers ───────────────────────────────────────────────

def _safe_str(value, field_name: str, max_length: int):
    """Validate and sanitize a string input. Returns error dict if invalid."""
    if not value or not str(value).strip():
        return {'error': f'{field_name} is required and cannot be empty.'}
    s = str(value).strip()
    if len(s) > max_length:
        return {'error': f'{field_name} exceeds maximum length of {max_length} characters.'}
    return s
