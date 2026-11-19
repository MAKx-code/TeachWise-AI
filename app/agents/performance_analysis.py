"""
Performance Analysis Agent
Validates and analyses student CSV data; computes statistics.
Stage 1 of the connected learning support pipeline.
"""
import json
import pandas as pd
import numpy as np
from app.granite import chat

REQUIRED_COLUMNS = {'student_id', 'attendance_pct'}
OPTIONAL_TOPIC_COLUMNS = ['quiz_basics', 'quiz_loops', 'quiz_arrays', 'assignment_score']

SYSTEM_PROMPT = """You are TeachWise AI's Performance Analysis Agent.
Your role: interpret Python-computed student performance statistics and provide educational insights.
Rules:
- Base ALL analysis on the provided computed statistics. Do NOT invent numbers.
- Identify patterns in the data: strengths, weaknesses, trends.
- Keep language professional and objective.
- Present findings as advisory, not definitive judgments.
- Output structured JSON as requested.
"""


def validate_csv(df: pd.DataFrame) -> tuple[bool, str, list]:
    """Validate CSV columns and values. Returns (is_valid, error_msg, warnings)."""
    warnings = []
    cols_lower = {c.lower().strip() for c in df.columns}

    # Check required columns
    missing = REQUIRED_COLUMNS - cols_lower
    if missing:
        return False, f"Missing required columns: {', '.join(missing)}", []

    # Rename columns to standard lowercase
    df.columns = [c.lower().strip() for c in df.columns]

    # Check attendance range
    if 'attendance_pct' in df.columns:
        invalid_att = df['attendance_pct'].apply(
            lambda x: not _is_valid_number(x, 0, 100)
        ).sum()
        if invalid_att > 0:
            warnings.append(f'{invalid_att} rows have invalid attendance_pct values (expected 0-100). They will be treated as missing.')

    # Check topic scores
    for col in OPTIONAL_TOPIC_COLUMNS:
        if col in df.columns:
            invalid = df[col].apply(lambda x: not _is_valid_number(x, 0, 100)).sum()
            if invalid > 0:
                warnings.append(f'{invalid} rows have invalid {col} values. They will be treated as missing.')

    if len(df) < 2:
        return False, 'CSV must contain at least 2 student records.', warnings

    return True, '', warnings


def _is_valid_number(val, min_val=0, max_val=100) -> bool:
    try:
        f = float(val)
        return min_val <= f <= max_val
    except (ValueError, TypeError):
        return False


def compute_performance(df: pd.DataFrame) -> dict:
    """
    Compute all performance statistics using Python/pandas.
    Returns structured performance dict. No AI involved here.
    """
    df.columns = [c.lower().strip() for c in df.columns]

    # Coerce numeric columns
    numeric_cols = [c for c in df.columns if c != 'student_id']
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    n = len(df)
    topic_cols = [c for c in OPTIONAL_TOPIC_COLUMNS if c in df.columns]

    # Class-level stats
    avg_attendance = float(df['attendance_pct'].mean()) if 'attendance_pct' in df.columns else None
    attendance_distribution = _attendance_distribution(df)

    # Topic-wise stats
    topic_stats = {}
    for col in topic_cols:
        vals = df[col].dropna()
        if len(vals) == 0:
            continue
        topic_stats[col] = {
            'mean': round(float(vals.mean()), 1),
            'median': round(float(vals.median()), 1),
            'std': round(float(vals.std()), 1),
            'min': round(float(vals.min()), 1),
            'max': round(float(vals.max()), 1),
            'below_50_pct': round(float((vals < 50).sum() / len(vals) * 100), 1),
            'below_40_pct': round(float((vals < 40).sum() / len(vals) * 100), 1),
        }

    # Overall score (average of available topic/assignment columns)
    if topic_cols:
        df['_overall'] = df[topic_cols].mean(axis=1)
        overall_avg = round(float(df['_overall'].mean()), 1)
        score_distribution = _score_distribution(df['_overall'].dropna())
    else:
        overall_avg = None
        score_distribution = {}

    # Students needing attention
    at_risk = _identify_at_risk(df, topic_cols)

    return {
        'num_students': n,
        'avg_attendance': round(avg_attendance, 1) if avg_attendance is not None else None,
        'attendance_distribution': attendance_distribution,
        'overall_avg_score': overall_avg,
        'score_distribution': score_distribution,
        'topic_stats': topic_stats,
        'available_topic_columns': topic_cols,
        'at_risk_students': at_risk,
        'per_student': _per_student_summary(df, topic_cols),
    }


def _attendance_distribution(df: pd.DataFrame) -> dict:
    if 'attendance_pct' not in df.columns:
        return {}
    vals = df['attendance_pct'].dropna()
    return {
        'below_60': int((vals < 60).sum()),
        '60_to_75': int(((vals >= 60) & (vals < 75)).sum()),
        '75_to_90': int(((vals >= 75) & (vals < 90)).sum()),
        'above_90': int((vals >= 90).sum()),
    }


def _score_distribution(scores: pd.Series) -> dict:
    return {
        'below_40': int((scores < 40).sum()),
        '40_to_60': int(((scores >= 40) & (scores < 60)).sum()),
        '60_to_75': int(((scores >= 60) & (scores < 75)).sum()),
        '75_to_90': int(((scores >= 75) & (scores < 90)).sum()),
        'above_90': int((scores >= 90).sum()),
    }


def _identify_at_risk(df: pd.DataFrame, topic_cols: list) -> list:
    """Identify at-risk students using transparent configurable criteria."""
    at_risk = []
    for _, row in df.iterrows():
        reasons = []
        att = row.get('attendance_pct')
        if pd.notna(att) and float(att) < 60:
            reasons.append(f'Low attendance: {att:.0f}%')

        if topic_cols:
            topic_scores = [row.get(c) for c in topic_cols if pd.notna(row.get(c))]
            if topic_scores:
                avg = float(np.mean(topic_scores))
                if avg < 50:
                    reasons.append(f'Low average score: {avg:.1f}%')
                # Check if failing 2+ topics
                failing = sum(1 for s in topic_scores if float(s) < 40)
                if failing >= 2:
                    reasons.append(f'Failing {failing} topics (score <40%)')

        if reasons:
            at_risk.append({
                'student_id': str(row['student_id']),
                'reasons': reasons,
                'attendance': float(att) if pd.notna(att) else None,
                'scores': {c: round(float(row[c]), 1) if pd.notna(row.get(c)) else None for c in topic_cols},
            })

    return at_risk


def _per_student_summary(df: pd.DataFrame, topic_cols: list) -> list:
    rows = []
    for _, row in df.iterrows():
        entry = {'student_id': str(row['student_id'])}
        if 'attendance_pct' in df.columns and pd.notna(row.get('attendance_pct')):
            entry['attendance_pct'] = round(float(row['attendance_pct']), 1)
        for col in topic_cols:
            if pd.notna(row.get(col)):
                entry[col] = round(float(row[col]), 1)
        if topic_cols:
            scores = [row.get(c) for c in topic_cols if pd.notna(row.get(c))]
            if scores:
                entry['overall'] = round(float(np.mean(scores)), 1)
        rows.append(entry)
    return rows


def ai_interpret_performance(performance: dict) -> str:
    """AI interprets computed performance stats. Stats come from Python, not AI."""
    stats_summary = json.dumps({
        'num_students': performance['num_students'],
        'avg_attendance': performance['avg_attendance'],
        'overall_avg_score': performance['overall_avg_score'],
        'topic_stats': performance['topic_stats'],
        'at_risk_count': len(performance['at_risk_students']),
        'attendance_distribution': performance['attendance_distribution'],
    }, indent=2)

    user_message = f"""The following are Python-computed performance statistics for a class of {performance['num_students']} students.
Based ONLY on these statistics, provide a brief performance analysis (3-4 paragraphs):

{stats_summary}

Your analysis should:
1. Summarize overall class performance and attendance.
2. Identify which topics show strongest and weakest performance based on the data.
3. Note any concerning patterns.
4. Provide 2-3 specific, actionable recommendations for the faculty.

Base your entire analysis on the provided numbers. Do not invent or estimate statistics not shown above."""

    return chat(SYSTEM_PROMPT, user_message, max_tokens=800)
