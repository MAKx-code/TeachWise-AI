"""
Teaching Material Agent
Generates lecture notes, examples, case studies, exercises.
"""
from app.granite import chat

SYSTEM_PROMPT = """You are TeachWise AI's Teaching Material Agent — an expert content creator for engineering education.
Your role: generate high-quality, accurate teaching materials for engineering faculty.
Rules:
- Content must be technically accurate for the specified topic.
- Adapt depth and complexity to the specified difficulty level.
- Use clear structure with headers, bullet points, and code blocks where relevant.
- Include real-world engineering examples and applications.
- Never invent technical facts or incorrect formulas.
"""

MATERIAL_TYPE_INSTRUCTIONS = {
    'lecture_notes': 'Generate comprehensive lecture notes with key concepts, definitions, formulas, and explanations.',
    'examples': 'Generate 4-5 worked examples progressing from simple to complex, showing complete solutions.',
    'case_study': 'Generate a realistic engineering case study with problem context, analysis, and solution discussion.',
    'exercises': 'Generate 6-8 practice exercises with varying difficulty, including complete solutions.',
    'discussion': 'Generate 5-6 thought-provoking discussion questions that test conceptual understanding.',
}


def generate_material(
    course_name: str,
    topic: str,
    difficulty: str,
    material_type: str,
) -> str:
    """Generate teaching material of specified type."""
    type_instruction = MATERIAL_TYPE_INSTRUCTIONS.get(
        material_type,
        'Generate comprehensive teaching materials with clear explanations and examples.'
    )

    user_message = f"""Generate teaching material with the following specifications:

**Course:** {course_name}
**Topic:** {topic}
**Difficulty Level:** {difficulty}
**Material Type:** {material_type.replace('_', ' ').title()}

{type_instruction}

Additional requirements:
- For {difficulty} level: {'Focus on fundamentals, clear definitions, step-by-step explanations' if difficulty == 'Easy' else ('Include intermediate concepts, comparative analysis, and application problems' if difficulty == 'Medium' else 'Include advanced theory, edge cases, optimization, and research-level challenges')}
- Include relevant code snippets or pseudocode where appropriate for the topic.
- Structure clearly with numbered sections and subheadings.
- End with a brief "Key Takeaways" summary (3-5 bullet points).

Generate the complete {material_type.replace('_', ' ')} now:"""

    return chat(SYSTEM_PROMPT, user_message, max_tokens=2200)
