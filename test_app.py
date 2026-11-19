"""
TeachWise AI — Integration Tests
Run: python test_app.py
"""
import sys
import os
import json
import time
import io
import pandas as pd

# Ensure the workspace root is on the path
sys.path.insert(0, os.path.dirname(__file__))


def section(title):
    print(f'\n{"="*60}')
    print(f'  {title}')
    print('='*60)


def ok(msg): print(f'  [OK] {msg}')
def fail(msg): print(f'  [FAIL] {msg}')
def info(msg): print(f'  [INFO] {msg}')


# ── 1. App startup ────────────────────────────────────────────────────────────
section('1. Application Startup')
try:
    from app import create_app
    app = create_app()
    ok('Flask app created successfully')
    client = app.test_client()
    with app.app_context():
        from app.models import Course
        count = Course.query.count()
        ok(f'Database initialized — {count} courses seeded')
except Exception as e:
    fail(f'App startup failed: {e}')
    sys.exit(1)


# ── 2. Health check ───────────────────────────────────────────────────────────
section('2. Health Check')
with app.test_request_context():
    with app.test_client() as c:
        r = c.get('/api/health')
        if r.status_code == 200:
            ok(f'Health endpoint: {r.get_json()}')
        else:
            fail(f'Health check failed: {r.status_code}')


# ── 3. Granite connection test ────────────────────────────────────────────────
section('3. IBM Granite Connection')
try:
    from app.granite import test_connection
    result = test_connection()
    if result['status'] == 'ok':
        ok(f'Granite connected: {result["response"][:60]}')
    else:
        fail(f'Granite connection failed: {result.get("error")}')
        info('Other tests will continue but AI generation tests may fail.')
except Exception as e:
    fail(f'Granite test exception: {e}')


# ── 4. Lesson plan generation ─────────────────────────────────────────────────
section('4. Lesson Plan Generation')
try:
    from app.agents.lesson_planning import generate_lesson_plan
    plan = generate_lesson_plan(
        subject='Data Structures',
        topic='Binary Search Trees',
        course_outcomes='CO1: Implement BST, CO2: Analyze complexity',
        duration='60 minutes',
        student_level='Undergraduate (Year 2)',
        teaching_approach='Interactive lecture with live coding',
    )
    if plan and len(plan) > 100:
        ok(f'Lesson plan generated ({len(plan)} chars)')
        info(f'Preview: {plan[:120].strip()}...')
    else:
        fail(f'Short or empty plan: {repr(plan[:50])}')
except Exception as e:
    fail(f'Lesson plan generation failed: {e}')


# ── 5. Assessment generation ──────────────────────────────────────────────────
section('5. Assessment Generation')
try:
    from app.agents.assessment import generate_assessment
    result = generate_assessment(
        topic='Sorting Algorithms',
        difficulty='Medium',
        question_types=['MCQ', 'Short Answer'],
        num_questions=4,
    )
    if result.get('questions'):
        ok(f'Assessment generated: {len(result["questions"])} questions')
        for q in result['questions'][:2]:
            info(f'  Q{q["number"]} [{q["type"]}]: {q["question"][:60]}...')
    elif result.get('error'):
        fail(f'Assessment parse error: {result["error"]}')
        info(f'Raw output preview: {result.get("raw_output","")[:150]}')
    else:
        fail('No questions and no error — unexpected response structure')
except Exception as e:
    fail(f'Assessment generation failed: {e}')


# ── 6. CSV validation ─────────────────────────────────────────────────────────
section('6. CSV Validation')
demo_csv = os.path.join(os.path.dirname(__file__), 'data', 'demo_students.csv')
try:
    df = pd.read_csv(demo_csv)
    from app.agents.performance_analysis import validate_csv
    is_valid, error_msg, warnings = validate_csv(df.copy())
    if is_valid:
        ok(f'Demo CSV valid — {len(df)} students')
        if warnings:
            info(f'Warnings: {warnings}')
    else:
        fail(f'Demo CSV invalid: {error_msg}')
except Exception as e:
    fail(f'CSV validation failed: {e}')

# Test invalid CSV
try:
    bad_df = pd.DataFrame({'name': ['Alice'], 'grade': [90]})
    from app.agents.performance_analysis import validate_csv
    is_valid, error_msg, _ = validate_csv(bad_df)
    if not is_valid:
        ok(f'Invalid CSV correctly rejected: {error_msg}')
    else:
        fail('Invalid CSV was not rejected')
except Exception as e:
    fail(f'Invalid CSV test failed: {e}')


# ── 7. Performance calculations ───────────────────────────────────────────────
section('7. Performance Calculations')
try:
    df = pd.read_csv(demo_csv)
    from app.agents.performance_analysis import compute_performance
    perf = compute_performance(df)
    ok(f'Students: {perf["num_students"]}')
    ok(f'Avg attendance: {perf["avg_attendance"]}%')
    ok(f'Overall avg score: {perf["overall_avg_score"]}%')
    ok(f'At-risk students: {len(perf["at_risk_students"])}')
    ok(f'Topics analysed: {list(perf["topic_stats"].keys())}')
except Exception as e:
    fail(f'Performance calculation failed: {e}')


# ── 8. Learning gap detection ─────────────────────────────────────────────────
section('8. Learning Gap Detection')
try:
    from app.agents.gap_detection import detect_gaps
    gaps = detect_gaps(perf['topic_stats'])
    if gaps:
        ok(f'{len(gaps)} learning gaps detected')
        for g in gaps:
            info(f'  [{g["severity"]}] {g["topic"]}: {g["mean_score"]}% avg')
    else:
        info('No significant gaps in this dataset (all topics above thresholds)')
except Exception as e:
    fail(f'Gap detection failed: {e}')


# ── 9. Full pipeline ──────────────────────────────────────────────────────────
section('9. Full Analysis Pipeline')
try:
    df = pd.read_csv(demo_csv)
    from app.pipeline import run_analysis_pipeline
    start = time.time()
    result = run_analysis_pipeline(df, 'Data Structures & Algorithms')
    elapsed = time.time() - start
    info(f'Pipeline completed in {elapsed:.1f}s')
    
    for stage in result['stage_log']:
        status = stage['status']
        name = stage['stage']
        msg = stage.get('message', stage.get('error', ''))
        symbol = '[OK]' if status == 'success' else '[FAIL]'
        print(f'    {symbol} [{status.upper()}] {name}: {msg[:60]}')
    
    if result.get('error'):
        fail(f'Pipeline error: {result["error"]}')
    else:
        ok('Pipeline completed without fatal errors')
        if result['support_plan']:
            ok('Support plan generated')
        if result['gaps']:
            ok(f'{len(result["gaps"])} gaps with AI interventions')
except Exception as e:
    fail(f'Pipeline failed: {e}')


# ── 10. Empty/invalid input handling ─────────────────────────────────────────
section('10. Empty & Invalid Input Handling')
with app.test_client() as c:
    # Empty lesson plan input
    r = c.post('/api/lesson-plan', json={'subject': '', 'topic': ''}, content_type='application/json')
    data = r.get_json()
    if r.status_code == 400 or 'error' in data:
        ok(f'Empty input rejected: {data.get("error", "400 returned")}')
    else:
        fail(f'Empty input not rejected: {r.status_code} {data}')

    # No file upload
    r = c.post('/api/upload-csv', data={})
    data = r.get_json()
    if 'error' in data:
        ok(f'Missing file rejected: {data["error"]}')
    else:
        fail(f'Missing file not rejected: {r.status_code}')


# ── 11. API endpoints smoke test ──────────────────────────────────────────────
section('11. Page Routes Smoke Test')
with app.test_client() as c:
    for route, name in [
        ('/', 'Dashboard redirect'),
        ('/dashboard', 'Dashboard'),
        ('/lesson-studio', 'Lesson Studio'),
        ('/teaching-materials', 'Teaching Materials'),
        ('/assessment-studio', 'Assessment Studio'),
        ('/student-analytics', 'Student Analytics'),
        ('/learning-support', 'Learning Support'),
        ('/faculty-analytics', 'Faculty Analytics'),
    ]:
        r = c.get(route)
        if r.status_code in (200, 302):
            ok(f'{name}: HTTP {r.status_code}')
        else:
            fail(f'{name}: HTTP {r.status_code}')


# ── Summary ───────────────────────────────────────────────────────────────────
section('Test Run Complete')
info('TeachWise AI test suite finished.')
info('Start the app: python run.py')
info('Open: http://localhost:5000')
