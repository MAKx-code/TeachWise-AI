"""
Lesson Planning Agent
Generates structured lesson plans aligned with course outcomes.
"""
from app.granite import chat

SYSTEM_PROMPT = """You are TeachWise AI's Lesson Planning Agent — an expert educational designer for engineering faculty.
Your role: generate structured, pedagogically sound lesson plans.
Rules:
- Output must be practical and immediately usable by an engineering faculty member.
- Align content precisely with the stated course outcomes.
- Include clear time allocations that sum to the stated duration.
- Use clear section headers.
- Keep language professional and concise.
- Do NOT invent course content that contradicts standard engineering curricula.
"""


def generate_lesson_plan(
    subject: str,
    topic: str,
    course_outcomes: str,
    duration: str,
    student_level: str,
    teaching_approach: str,
) -> str:
    """
    Generate a complete lesson plan for the given inputs.
    Returns formatted lesson plan text.
    """
    user_message = f"""Create a detailed lesson plan with the following specifications:

**Subject/Course:** {subject}
**Topic:** {topic}
**Course Outcomes to Address:** {course_outcomes}
**Class Duration:** {duration}
**Student Level:** {student_level}
**Teaching Approach/Preferred Format:** {teaching_approach}

Generate a lesson plan that includes:
1. LEARNING OBJECTIVES (3-5 specific, measurable objectives)
2. LESSON OVERVIEW (brief summary)
3. TEACHING SEQUENCE WITH TIME ALLOCATION (breakdown adding to {duration})
   - Introduction / Hook
   - Core Content Delivery
   - Practical Activity / Examples
   - Assessment / Check for Understanding
   - Summary & Wrap-up
4. KEY CONCEPTS & EXAMPLES (2-3 concrete engineering examples)
5. PRACTICAL ACTIVITIES (hands-on tasks or exercises)
6. COURSE OUTCOME ALIGNMENT (map each objective to stated outcomes)
7. ASSESSMENT IDEAS (formative check-for-understanding questions)
8. FACULTY NOTES (tips, common misconceptions to address)

Format clearly with headers. Be specific and actionable."""

    return chat(SYSTEM_PROMPT, user_message, max_tokens=2000)
