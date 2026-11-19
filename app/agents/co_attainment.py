"""
app/agents/co_attainment.py -- CO Attainment Interpretation Agent

Receives COMPUTED attainment data from app/analytics.py.
Granite interprets the findings -- it does NOT invent them.
"""
import json
from app.granite import chat

SYSTEM_PROMPT = """You are TeachWise AI's CO Attainment Analysis Agent.
Your role: interpret Python-computed Course Outcome attainment data and provide faculty insights.
Rules:
- Base ALL analysis on the provided computed attainment percentages. Do NOT invent numbers.
- Identify which COs are at risk and hypothesize root causes.
- Provide specific, actionable interventions per unattained CO.
- Keep language professional, objective and advisory (not definitive judgments).
- Output structured plain text with clear sections."""


def interpret_co_attainment(co_attainment: dict, course_name: str = '') -> str:
    """
    Given the computed CO attainment dict (from compute_co_attainment),
    ask Granite to provide:
    - Interpretation of attainment levels
    - Root-cause hypotheses for unattained COs
    - Specific recommended faculty interventions

    Returns plain text interpretation.
    Raises exception on Granite failure (caller handles gracefully).
    """
    # Build a compact, injection-safe summary from the computed data
    outcomes_summary = []
    for o in co_attainment.get('outcomes', []):
        pct_str = f"{o['attainment_pct']}%" if o['attainment_pct'] is not None else 'No data'
        outcomes_summary.append(
            f"  {o['co_code']} ({o['bloom_level']}): {pct_str} -- {o['level_label']}"
        )

    summary_text = '\n'.join(outcomes_summary)
    overall = co_attainment.get('overall_attainment_pct')
    overall_str = f"{overall}%" if overall is not None else 'No data'

    attained = co_attainment.get('attained_count', 0)
    partially = co_attainment.get('partially_count', 0)
    not_attained = co_attainment.get('not_attained_count', 0)

    user_message = f"""The following Course Outcome attainment data has been computed from student assessment records for "{course_name}".

COMPUTED ATTAINMENT SUMMARY:
Overall attainment: {overall_str}
COs Attained (>=70%): {attained}
COs Partially Attained (55-69%): {partially}
COs Not Attained (<55%): {not_attained}

INDIVIDUAL CO ATTAINMENT:
{summary_text}

Based ONLY on these computed figures, provide a structured analysis in three sections:
1. ATTAINMENT OVERVIEW: Summarize the overall attainment picture and highlight the best and worst performing COs.
2. ROOT CAUSE HYPOTHESES: For each CO that is Partially Attained or Not Attained, suggest 2-3 likely pedagogical root causes.
3. RECOMMENDED INTERVENTIONS: Provide 3-5 specific, actionable faculty interventions to improve attainment for the weakest COs.

Do not invent or assume any statistics beyond what is provided above."""

    return chat(SYSTEM_PROMPT, user_message, max_tokens=900)
