"""
Personalized Learning Support Agent
Stage 3 of the connected pipeline.
Receives actual gaps and performance data — generates student-specific support plans.
"""
import json
import re
from app.granite import chat

SYSTEM_PROMPT = """You are TeachWise AI's Personalized Learning Support Agent.
Your role: generate specific, actionable academic support plans based on actual detected learning gaps.
Rules:
- Base ALL recommendations on the gap and performance data provided — do not invent new statistics.
- Generate practical, achievable recommendations for engineering students.
- Include a realistic revision timetable (days of the week).
- Distinguish between high-priority and supplementary activities.
- Faculty must review and approve all recommendations before sharing with students.
- Output must be structured JSON as requested.
"""


def generate_support_plan(
    performance: dict,
    gaps: list,
    course_name: str = '',
) -> dict:
    """
    Generate a comprehensive learning support plan.
    Receives actual computed performance and detected gaps.
    Returns structured support plan.
    """
    # Build a focused summary for the prompt
    gap_summary = []
    for g in gaps:
        gap_summary.append({
            'topic': g['topic'],
            'severity': g['severity'],
            'mean_score': g['mean_score'],
            'students_below_50_pct': g['below_50_pct'],
            'recommended_intervention': g.get('intervention', ''),
        })

    performance_summary = {
        'num_students': performance['num_students'],
        'avg_attendance': performance['avg_attendance'],
        'overall_avg_score': performance['overall_avg_score'],
        'at_risk_count': len(performance.get('at_risk_students', [])),
        'detected_gaps': gap_summary,
    }

    # Compact gap list to keep prompt small
    gap_names = [g['topic'] for g in gaps[:3]]  # top 3 gaps only

    user_message = f"""Generate a concise Personalized Learning Support Plan for "{course_name or 'Engineering Course'}".

Python-computed data:
- Students: {performance_summary['num_students']}
- Avg attendance: {performance_summary['avg_attendance']}%
- Avg score: {performance_summary['overall_avg_score']}%
- At-risk students: {performance_summary['at_risk_count']}
- Top gaps (by severity): {', '.join(gap_names) if gap_names else 'None'}

Return ONLY this JSON (no extra text, no markdown):
{{
  "executive_summary": "<2 sentences summarising the learning situation>",
  "topic_support_plans": [
    {{"topic": "<gap topic>", "severity": "<Critical|Significant|Moderate>", "revision_strategy": "<1 sentence>", "practice_activities": ["<activity 1>", "<activity 2>"]}}
  ],
  "faculty_actions": [
    {{"action": "<specific action>", "timeline": "<this week|next week>", "priority": "<High|Medium|Low>"}}
  ],
  "disclaimer": "These recommendations are advisory. Faculty should review before sharing with students."
}}"""

    raw = chat(SYSTEM_PROMPT, user_message, max_tokens=1000)

    # Parse JSON response
    cleaned = re.sub(r'^```(?:json)?\s*', '', raw.strip(), flags=re.MULTILINE)
    cleaned = re.sub(r'```\s*$', '', cleaned.strip(), flags=re.MULTILINE)
    cleaned = cleaned.strip()

    try:
        plan = json.loads(cleaned)
        plan['_source_data'] = {
            'num_gaps': len(gaps),
            'num_students': performance['num_students'],
            'at_risk_count': len(performance.get('at_risk_students', [])),
        }
        plan['_generation_status'] = 'success'
        return plan
    except (json.JSONDecodeError, ValueError):
        # Try to salvage partial JSON — extract fields we can
        salvaged = _salvage_partial_json(cleaned, raw)
        salvaged['_source_data'] = {
            'num_gaps': len(gaps),
            'num_students': performance['num_students'],
            'at_risk_count': len(performance.get('at_risk_students', [])),
        }
        return salvaged


def _salvage_partial_json(cleaned: str, raw: str) -> dict:
    """Extract what we can from a truncated JSON response."""
    import re as _re
    result = {
        '_generation_status': 'partial',
        'executive_summary': '',
        'topic_support_plans': [],
        'faculty_actions': [],
        'disclaimer': 'These recommendations are advisory. Faculty should review before sharing with students.',
        'raw_output': raw[:500],
    }
    # Try to extract executive_summary
    m = _re.search(r'"executive_summary"\s*:\s*"([^"]{10,})"', cleaned)
    if m:
        result['executive_summary'] = m.group(1)
        result['_generation_status'] = 'partial'
    # If nothing extracted, store raw as summary
    if not result['executive_summary'] and len(raw) > 50:
        result['executive_summary'] = raw[:300].strip()
        result['_generation_status'] = 'partial'
    return result
