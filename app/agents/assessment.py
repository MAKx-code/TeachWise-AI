"""
Assessment Generation Agent
Generates MCQs, short/long answer questions, coding exercises with answer keys.
"""
import json
import re
from app.granite import chat

SYSTEM_PROMPT = """You are TeachWise AI's Assessment Agent — an expert assessment designer for engineering education.
Your role: generate valid, well-structured assessments with accurate answer keys.
Rules:
- All answers and explanations must be technically correct.
- Questions must clearly target the specified difficulty level.
- MCQ options must be plausible but have exactly one correct answer.
- Short and long answer questions must have clear marking guidance.
- Coding exercises must include working solution code.
- Output must be structured JSON that follows the exact format requested.
- Never invent incorrect technical facts in answer keys.
"""


def generate_assessment(
    topic: str,
    difficulty: str,
    question_types: list,
    num_questions: int,
    course_outcome: str = '',
) -> dict:
    """
    Generate assessment questions with answer keys.
    Returns a dict with questions list and metadata.
    """
    types_str = ', '.join(question_types)
    co_section = f'\n**Course Outcome:** {course_outcome}' if course_outcome else ''

    user_message = f"""Generate an assessment with the following specifications:

**Topic:** {topic}
**Difficulty Level:** {difficulty}
**Question Types:** {types_str}
**Number of Questions:** {num_questions}{co_section}

Return a JSON object with this exact structure:
{{
  "topic": "{topic}",
  "difficulty": "{difficulty}",
  "total_marks": <calculated total>,
  "questions": [
    {{
      "number": 1,
      "type": "MCQ" | "Short Answer" | "Long Answer" | "Coding",
      "marks": <1 for MCQ, 3 for Short, 8 for Long, 5 for Coding>,
      "question": "<question text>",
      "options": ["A) ...", "B) ...", "C) ...", "D) ..."],  // only for MCQ
      "correct_answer": "<answer or option letter>",
      "explanation": "<why this is correct>",
      "co_alignment": "<which course outcome this tests>"
    }}
  ],
  "instructions": "<assessment instructions for students>"
}}

Distribute questions across requested types. Generate exactly {num_questions} questions.
Return ONLY the JSON object, no extra text."""

    raw = chat(SYSTEM_PROMPT, user_message, max_tokens=2500)
    return _parse_assessment_json(raw, topic, difficulty)


def _parse_assessment_json(raw: str, topic: str, difficulty: str) -> dict:
    """Parse and validate the assessment JSON from Granite."""
    # Strip markdown code fences if present
    cleaned = re.sub(r'^```(?:json)?\s*', '', raw.strip(), flags=re.MULTILINE)
    cleaned = re.sub(r'```\s*$', '', cleaned.strip(), flags=re.MULTILINE)
    cleaned = cleaned.strip()

    try:
        data = json.loads(cleaned)
        # Validate structure
        if 'questions' not in data:
            raise ValueError('Missing questions array')
        for q in data['questions']:
            # Normalize common alternate field names
            if 'correct_answer' not in q:
                for alt in ('answer', 'correct', 'answer_key', 'correctAnswer'):
                    if alt in q:
                        q['correct_answer'] = q.pop(alt)
                        break
            if 'correct_answer' not in q:
                q['correct_answer'] = 'See explanation.'
            if 'explanation' not in q:
                q['explanation'] = ''
            required = ['number', 'type', 'question']
            for field in required:
                if field not in q:
                    raise ValueError(f'Question missing field: {field}')
        return data
    except (json.JSONDecodeError, ValueError) as exc:
        # Return structured error that the route can handle
        return {
            'error': f'Could not parse assessment output: {exc}',
            'raw_output': raw,
            'topic': topic,
            'difficulty': difficulty,
            'questions': [],
        }
