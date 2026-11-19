"""
Learning Gap Detection Agent
Uses computed Python statistics to identify and explain learning gaps.
Stage 2 of the connected learning support pipeline.
"""
import json
from app.granite import chat

# Configurable thresholds — faculty can understand and adjust these
GAP_THRESHOLDS = {
    'critical': {'mean_below': 50, 'below_50_pct_above': 50},  # >50% students below 50
    'significant': {'mean_below': 60, 'below_50_pct_above': 30},
    'moderate': {'mean_below': 70, 'below_50_pct_above': 20},
}

SYSTEM_PROMPT = """You are TeachWise AI's Learning Gap Detection Agent.
Your role: explain detected learning gaps and suggest evidence-based teaching interventions.
Rules:
- The gaps have already been detected by Python calculations — you are EXPLAINING them, not detecting them.
- Each gap explanation must reference the specific performance metric that triggered it.
- Suggest concrete, practical teaching interventions that an engineering faculty member can implement.
- Prioritize interventions by urgency based on the severity data provided.
- Output must be structured JSON as requested.
"""

COLUMN_DISPLAY_NAMES = {
    'quiz_basics': 'Programming Basics',
    'quiz_loops': 'Loops & Iteration',
    'quiz_arrays': 'Arrays & Data Structures',
    'assignment_score': 'Assignment Performance',
}


def detect_gaps(topic_stats: dict) -> list:
    """
    Detect learning gaps using Python-computed topic statistics.
    Returns a list of gap dicts with severity classification.
    This is pure Python — no AI involved.
    """
    gaps = []
    for col, stats in topic_stats.items():
        mean = stats['mean']
        below_50_pct = stats['below_50_pct']
        display_name = COLUMN_DISPLAY_NAMES.get(col, col.replace('_', ' ').title())

        severity = None
        reason = None

        if mean < GAP_THRESHOLDS['critical']['mean_below'] or below_50_pct >= GAP_THRESHOLDS['critical']['below_50_pct_above']:
            severity = 'Critical'
            reason = f'Class average {mean}% is below 50%; {below_50_pct}% of students scored below 50%'
        elif mean < GAP_THRESHOLDS['significant']['mean_below'] or below_50_pct >= GAP_THRESHOLDS['significant']['below_50_pct_above']:
            severity = 'Significant'
            reason = f'Class average {mean}% is below 60%; {below_50_pct}% of students scored below 50%'
        elif mean < GAP_THRESHOLDS['moderate']['mean_below'] or below_50_pct >= GAP_THRESHOLDS['moderate']['below_50_pct_above']:
            severity = 'Moderate'
            reason = f'Class average {mean}%; {below_50_pct}% of students scored below 50%'

        if severity:
            gaps.append({
                'column': col,
                'topic': display_name,
                'mean_score': mean,
                'below_50_pct': below_50_pct,
                'below_40_pct': stats.get('below_40_pct', 0),
                'severity': severity,
                'reason': reason,
                'intervention': None,  # Filled by AI
            })

    # Sort by severity: Critical > Significant > Moderate
    severity_order = {'Critical': 0, 'Significant': 1, 'Moderate': 2}
    gaps.sort(key=lambda g: severity_order.get(g['severity'], 3))
    return gaps


def ai_explain_gaps(gaps: list, num_students: int) -> list:
    """
    Use AI to add teaching interventions to detected gaps.
    The gap data itself comes from Python — AI only adds the explanation.
    """
    if not gaps:
        return gaps

    gaps_for_ai = json.dumps([{
        'topic': g['topic'],
        'mean_score': g['mean_score'],
        'below_50_pct': g['below_50_pct'],
        'severity': g['severity'],
        'reason': g['reason'],
    } for g in gaps], indent=2)

    user_message = f"""The following learning gaps were detected by statistical analysis of {num_students} students.
For each gap, provide a targeted teaching intervention.

Detected gaps:
{gaps_for_ai}

Return a JSON array with this exact structure for each gap:
[
  {{
    "topic": "<same topic name from input>",
    "intervention": "<specific, practical teaching strategy — 2-3 sentences>",
    "remediation_activities": ["<activity 1>", "<activity 2>", "<activity 3>"],
    "priority_action": "<single most important action for the faculty to take this week>"
  }}
]

Return ONLY the JSON array, no extra text."""

    raw = chat(SYSTEM_PROMPT, user_message, max_tokens=1200)

    # Parse and merge AI interventions back into gap data
    import re
    cleaned = re.sub(r'^```(?:json)?\s*', '', raw.strip(), flags=re.MULTILINE)
    cleaned = re.sub(r'```\s*$', '', cleaned.strip(), flags=re.MULTILINE)
    try:
        interventions = json.loads(cleaned.strip())
        # Merge by topic name
        intervention_map = {item['topic']: item for item in interventions}
        for gap in gaps:
            info = intervention_map.get(gap['topic'], {})
            gap['intervention'] = info.get('intervention', 'Review and reteach core concepts.')
            gap['remediation_activities'] = info.get('remediation_activities', [])
            gap['priority_action'] = info.get('priority_action', 'Schedule a revision session.')
    except Exception:
        # Fallback if JSON parsing fails
        for gap in gaps:
            gap['intervention'] = f'Review {gap["topic"]} fundamentals with additional practice exercises.'
            gap['remediation_activities'] = ['Targeted practice quiz', 'Peer learning session', 'Office hours review']
            gap['priority_action'] = f'Schedule a dedicated revision session for {gap["topic"]}.'

    return gaps
