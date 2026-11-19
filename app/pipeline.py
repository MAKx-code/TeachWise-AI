"""
Pipeline orchestrator for the connected learning-support workflow:
CSV → Validation → Performance Analysis → Gap Detection → Learning Support

Tracks stage log with timestamps and success/failure status.
"""
import json
import pandas as pd
from datetime import datetime

from app.agents.performance_analysis import validate_csv, compute_performance, ai_interpret_performance
from app.agents.gap_detection import detect_gaps, ai_explain_gaps
from app.agents.learning_support import generate_support_plan


def run_analysis_pipeline(df: pd.DataFrame, course_name: str = '') -> dict:
    """
    Full orchestrated pipeline. Returns a results dict with stage log.
    Each stage records its status.
    """
    stage_log = []
    result = {
        'course_name': course_name,
        'stage_log': stage_log,
        'performance': None,
        'ai_interpretation': None,
        'gaps': None,
        'support_plan': None,
        'error': None,
    }

    # ── Stage 1: Data Validation ──────────────────────────────────────────
    stage_log.append(_stage_start('Data Validation'))
    is_valid, error_msg, warnings = validate_csv(df)
    if not is_valid:
        stage_log[-1].update(_stage_fail(error_msg))
        result['error'] = error_msg
        return result
    stage_log[-1].update(_stage_success(f'Validated {len(df)} student records. Warnings: {len(warnings)}'))
    if warnings:
        stage_log[-1]['warnings'] = warnings

    # ── Stage 2: Python Performance Calculations ──────────────────────────
    stage_log.append(_stage_start('Performance Calculations'))
    try:
        performance = compute_performance(df)
        result['performance'] = performance
        stage_log[-1].update(_stage_success(
            f'{performance["num_students"]} students analysed. '
            f'Avg attendance: {performance["avg_attendance"]}%. '
            f'Overall avg score: {performance["overall_avg_score"]}%.'
        ))
    except Exception as exc:
        stage_log[-1].update(_stage_fail(str(exc)))
        result['error'] = f'Performance calculation failed: {exc}'
        return result

    # ── Stage 3: AI Performance Interpretation ────────────────────────────
    stage_log.append(_stage_start('AI Performance Interpretation (Granite)'))
    try:
        ai_interpretation = ai_interpret_performance(performance)
        result['ai_interpretation'] = ai_interpretation
        stage_log[-1].update(_stage_success('Granite analysed class performance.'))
    except Exception as exc:
        stage_log[-1].update(_stage_fail(f'AI interpretation skipped: {exc}'))
        result['ai_interpretation'] = None

    # ── Stage 4: Gap Detection (Python) ──────────────────────────────────
    stage_log.append(_stage_start('Learning Gap Detection'))
    try:
        gaps = detect_gaps(performance['topic_stats'])
        stage_log[-1].update(_stage_success(f'{len(gaps)} learning gaps detected.'))
    except Exception as exc:
        stage_log[-1].update(_stage_fail(str(exc)))
        gaps = []

    # ── Stage 5: AI Gap Explanations (Granite) ────────────────────────────
    if gaps:
        stage_log.append(_stage_start('AI Gap Explanations (Granite)'))
        try:
            gaps = ai_explain_gaps(gaps, performance['num_students'])
            result['gaps'] = gaps
            stage_log[-1].update(_stage_success(f'Granite provided interventions for {len(gaps)} gaps.'))
        except Exception as exc:
            stage_log[-1].update(_stage_fail(f'AI gap explanation failed: {exc}'))
            result['gaps'] = gaps
    else:
        result['gaps'] = gaps

    # ── Stage 6: Personalized Learning Support (Granite) ─────────────────
    stage_log.append(_stage_start('Personalized Learning Support (Granite)'))
    try:
        support_plan = generate_support_plan(performance, gaps or [], course_name)
        result['support_plan'] = support_plan
        stage_log[-1].update(_stage_success('Personalized support plan generated.'))
    except Exception as exc:
        stage_log[-1].update(_stage_fail(f'Support plan generation failed: {exc}'))
        result['support_plan'] = None

    return result


def _stage_start(name: str) -> dict:
    return {'stage': name, 'status': 'running', 'started_at': datetime.utcnow().isoformat()}


def _stage_success(message: str) -> dict:
    return {'status': 'success', 'message': message, 'completed_at': datetime.utcnow().isoformat()}


def _stage_fail(error: str) -> dict:
    return {'status': 'failed', 'error': error, 'completed_at': datetime.utcnow().isoformat()}
