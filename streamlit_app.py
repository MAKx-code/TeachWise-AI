"""
streamlit_app.py — TeachWise AI Streamlit Frontend
Reuses existing Flask agents, analytics and IBM Granite integration.
Run: streamlit run streamlit_app.py
"""
import os
import sys
import io
import json
import pandas as pd

# Ensure app package is importable from project root
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
from dotenv import load_dotenv
load_dotenv()

# ── Page config (must be first Streamlit call) ────────────────────────────────
st.set_page_config(
    page_title="TeachWise AI",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  [data-testid="stSidebar"] { background: #0d1117; }
  [data-testid="stSidebar"] .stMarkdown h1 { color: #22d3ee; font-size: 1.3rem; }
  .metric-card { background: #161b22; border: 1px solid #30363d;
                 border-radius: 8px; padding: 16px; text-align: center; }
  .metric-val  { font-size: 2rem; font-weight: 700; color: #22d3ee; }
  .metric-lbl  { font-size: 0.8rem; color: #8b9ab0; margin-top: 4px; }
  .gap-critical { border-left: 4px solid #f85149; padding: 10px 14px;
                  background: #1a0a0a; border-radius: 0 6px 6px 0; margin:6px 0; }
  .gap-significant { border-left: 4px solid #d29922; padding: 10px 14px;
                     background: #1a1500; border-radius: 0 6px 6px 0; margin:6px 0; }
  .gap-moderate { border-left: 4px solid #3b82f6; padding: 10px 14px;
                  background: #0a1020; border-radius: 0 6px 6px 0; margin:6px 0; }
  .advisory-box { background: #161b22; border: 1px solid #30363d;
                  border-radius: 8px; padding: 14px; font-size: 0.85rem;
                  color: #8b9ab0; margin-top: 12px; }
</style>
""", unsafe_allow_html=True)

# ── Helpers ───────────────────────────────────────────────────────────────────

@st.cache_resource
def get_flask_app():
    """Create Flask app once and cache it for the session."""
    from app import create_app
    return create_app()


def db_analytics(course_id: int) -> dict:
    """Run DB analytics inside Flask app context."""
    flask_app = get_flask_app()
    with flask_app.app_context():
        from app.analytics import compute_full_analytics
        return compute_full_analytics(course_id)


def get_courses() -> list[dict]:
    flask_app = get_flask_app()
    with flask_app.app_context():
        from app.models import Course
        return [{'id': c.id, 'name': c.name, 'code': c.code,
                 'semester': c.semester} for c in Course.query.all()]


def granite_available() -> bool:
    return bool(os.getenv('WATSONX_API_KEY') and os.getenv('WATSONX_PROJECT_ID'))


# ── Sidebar navigation ────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🎓 TeachWise AI")
    st.caption("Faculty Intelligence Platform")
    st.divider()

    page = st.radio(
        "Navigate",
        ["Overview", "Lesson Studio", "Teaching Materials",
         "Assessment Studio", "Student Analytics", "CO & Analytics",
         "Learning Support"],
        label_visibility="collapsed",
    )
    st.divider()

    # Granite status
    if granite_available():
        st.success("IBM Granite · Connected", icon="🟢")
    else:
        st.error("IBM Granite · No credentials", icon="🔴")
        st.caption("Set WATSONX_API_KEY and WATSONX_PROJECT_ID in .env")

    st.caption("Plan Better. Teach Smarter. Support Every Learner.")


# ════════════════════════════════════════════════════════════════════════════════
# PAGE: OVERVIEW (Dashboard)
# ════════════════════════════════════════════════════════════════════════════════
if page == "Overview":
    st.title("Faculty Overview")
    st.caption("Live stats from the CS201 synthetic academic dataset")

    courses = get_courses()
    cs201 = next((c for c in courses if c['code'] == 'CS201'), None)

    # Stat cards row
    if cs201:
        try:
            analytics = db_analytics(cs201['id'])
            att = analytics['attendance']
            co = analytics['co_attainment']
            at_risk = analytics['at_risk_students']
            tp = analytics['topic_performance']

            c1, c2, c3, c4, c5 = st.columns(5)
            with c1:
                st.metric("Students", att['total_students'])
            with c2:
                avg_att = att['class_avg_pct']
                st.metric("Avg Attendance",
                          f"{avg_att}%" if avg_att is not None else "N/A",
                          delta=f"{avg_att - 75:.1f}% vs 75% threshold" if avg_att is not None else None)
            with c3:
                overall_att = co['overall_attainment_pct']
                st.metric("CO Attainment",
                          f"{overall_att}%" if overall_att is not None else "N/A",
                          delta=f"{co['attained_count']}/{len(co['outcomes'])} COs attained")
            with c4:
                st.metric("At-Risk Students", len(at_risk),
                          delta=f"{att['below_75_count']} below 75% attendance",
                          delta_color="inverse")
            with c5:
                critical = sum(1 for t in tp if t['gap_severity'] == 'Critical')
                st.metric("Critical Gaps", critical)

            st.divider()

            # Topic performance bar chart
            st.subheader("Topic Performance (CS201)")
            chart_df = pd.DataFrame([
                {'Topic': t['title'],
                 'Combined Avg %': t['combined_avg_pct'],
                 'Severity': t['gap_severity']}
                for t in tp if t['combined_avg_pct'] is not None
            ])
            st.bar_chart(chart_df.set_index('Topic')['Combined Avg %'])

            col_left, col_right = st.columns(2)
            with col_left:
                st.subheader("CO Attainment")
                co_df = pd.DataFrame([
                    {'CO': o['co_code'], 'Attainment %': o['attainment_pct'],
                     'Level': o['level_label']}
                    for o in co['outcomes']
                ])
                st.dataframe(co_df, use_container_width=True, hide_index=True)

            with col_right:
                st.subheader("At-Risk Students (top 10)")
                if at_risk:
                    risk_df = pd.DataFrame([
                        {'Student': s['student_code'],
                         'Attendance %': s['attendance_pct'],
                         'Avg Score %': s['avg_score_pct'],
                         'Priority': s['priority']}
                        for s in at_risk[:10]
                    ])
                    st.dataframe(risk_df, use_container_width=True, hide_index=True)
                else:
                    st.success("No at-risk students detected.")

        except Exception as exc:
            st.error(f"Analytics error: {exc}")
    else:
        st.warning("CS201 course not found. Run `python seed_academic.py` first.")

    st.divider()
    st.subheader("All Courses")
    if courses:
        st.dataframe(pd.DataFrame(courses)[['code','name','semester']],
                     use_container_width=True, hide_index=True)


# ════════════════════════════════════════════════════════════════════════════════
# PAGE: LESSON STUDIO
# ════════════════════════════════════════════════════════════════════════════════
elif page == "Lesson Studio":
    st.title("Lesson Studio")
    st.caption("Generate structured lesson plans aligned with course outcomes · IBM Granite")

    if not granite_available():
        st.error("IBM Granite credentials not set. Add WATSONX_API_KEY and WATSONX_PROJECT_ID to .env")
        st.stop()

    with st.form("lesson_form"):
        col1, col2 = st.columns(2)
        with col1:
            subject = st.text_input("Subject / Course", value="Data Structures & Algorithms")
            topic = st.text_input("Topic", value="Binary Search Trees")
            duration = st.selectbox("Duration", ["45 minutes", "60 minutes", "90 minutes", "120 minutes"])
        with col2:
            level = st.selectbox("Student Level", ["Undergraduate", "Postgraduate", "Diploma"])
            outcomes = st.text_area("Course Outcomes",
                value="CO4: Construct and traverse tree data structures for hierarchical data.",
                height=80)
            approach = st.text_input("Teaching Approach", value="Interactive lecture with coding examples")

        submitted = st.form_submit_button("Generate Lesson Plan", use_container_width=True, type="primary")

    if submitted:
        if not subject.strip() or not topic.strip():
            st.error("Subject and Topic are required.")
        elif len(topic) > 200:
            st.error("Topic exceeds 200 characters.")
        else:
            with st.spinner("Generating lesson plan with IBM Granite..."):
                try:
                    from app.agents.lesson_planning import generate_lesson_plan
                    plan = generate_lesson_plan(subject, topic, outcomes, duration, level, approach)
                    st.session_state['lesson_plan'] = plan
                    st.session_state['lesson_approved'] = False
                except Exception as exc:
                    st.error(f"Granite unavailable: {exc}")

    if 'lesson_plan' in st.session_state:
        st.divider()
        st.subheader("Generated Lesson Plan")
        st.markdown(st.session_state['lesson_plan'])

        if not st.session_state.get('lesson_approved'):
            st.markdown('<div class="advisory-box">These recommendations are AI-generated. Review before use in class.</div>', unsafe_allow_html=True)
            if st.button("Approve Lesson Plan", type="primary"):
                st.session_state['lesson_approved'] = True
                st.success("Lesson plan approved by faculty.")
                st.rerun()
        else:
            st.success("Approved by faculty.")


# ════════════════════════════════════════════════════════════════════════════════
# PAGE: TEACHING MATERIALS
# ════════════════════════════════════════════════════════════════════════════════
elif page == "Teaching Materials":
    st.title("Teaching Materials")
    st.caption("Generate lecture notes, worked examples, case studies and exercises · IBM Granite")

    if not granite_available():
        st.error("IBM Granite credentials not set.")
        st.stop()

    with st.form("material_form"):
        col1, col2 = st.columns(2)
        with col1:
            course_name = st.text_input("Course", value="Data Structures & Algorithms")
            topic = st.text_input("Topic", value="Graph Traversal: BFS and DFS")
            difficulty = st.selectbox("Difficulty", ["Easy", "Medium", "Hard"])
        with col2:
            mat_type = st.selectbox("Material Type", [
                ("Lecture Notes", "lecture_notes"),
                ("Worked Examples", "examples"),
                ("Case Study", "case_study"),
                ("Practice Exercises", "exercises"),
                ("Discussion Questions", "discussion"),
            ], format_func=lambda x: x[0])

        submitted = st.form_submit_button("Generate Material", use_container_width=True, type="primary")

    if submitted:
        if not topic.strip():
            st.error("Topic is required.")
        else:
            with st.spinner(f"Generating {mat_type[0]} with IBM Granite..."):
                try:
                    from app.agents.teaching_material import generate_material
                    content = generate_material(course_name, topic, difficulty, mat_type[1])
                    st.session_state['material'] = content
                    st.session_state['material_approved'] = False
                except Exception as exc:
                    st.error(f"Granite unavailable: {exc}")

    if 'material' in st.session_state:
        st.divider()
        st.subheader("Generated Material")
        st.markdown(st.session_state['material'])
        if not st.session_state.get('material_approved'):
            st.markdown('<div class="advisory-box">AI-generated content. Review for accuracy before use.</div>', unsafe_allow_html=True)
            if st.button("Approve Material", type="primary"):
                st.session_state['material_approved'] = True
                st.success("Material approved.")
                st.rerun()
        else:
            st.success("Approved by faculty.")


# ════════════════════════════════════════════════════════════════════════════════
# PAGE: ASSESSMENT STUDIO
# ════════════════════════════════════════════════════════════════════════════════
elif page == "Assessment Studio":
    st.title("Assessment Studio")
    st.caption("Generate MCQs, short-answer and coding questions with answer keys · IBM Granite")

    if not granite_available():
        st.error("IBM Granite credentials not set.")
        st.stop()

    with st.form("assess_form"):
        col1, col2 = st.columns(2)
        with col1:
            topic = st.text_input("Topic", value="Linked Lists")
            difficulty = st.selectbox("Difficulty", ["Easy", "Medium", "Hard"])
            num_q = st.slider("Number of Questions", 2, 10, 4)
        with col2:
            q_types = st.multiselect("Question Types",
                ["MCQ", "Short", "Long", "Coding"],
                default=["MCQ", "Short"])
            co = st.text_input("Course Outcome (optional)",
                value="CO2: Implement and analyse linked list operations")

        show_answers = st.checkbox("Show answer key", value=True)
        submitted = st.form_submit_button("Generate Assessment", use_container_width=True, type="primary")

    if submitted:
        if not topic.strip():
            st.error("Topic is required.")
        elif not q_types:
            st.error("Select at least one question type.")
        else:
            with st.spinner("Generating assessment with IBM Granite..."):
                try:
                    from app.agents.assessment import generate_assessment
                    result = generate_assessment(topic, difficulty, q_types, num_q, co)
                    st.session_state['assessment'] = result
                    st.session_state['assess_approved'] = False
                except Exception as exc:
                    st.error(f"Granite unavailable: {exc}")

    if 'assessment' in st.session_state:
        result = st.session_state['assessment']
        st.divider()

        if result.get('error') and not result.get('questions'):
            st.error(f"Assessment parse error: {result['error']}")
        else:
            questions = result.get('questions', [])
            st.subheader(f"Assessment: {result.get('topic', topic)} — {result.get('difficulty', difficulty)}")
            st.caption(f"{len(questions)} questions · Total marks: {result.get('total_marks', 'N/A')}")

            for i, q in enumerate(questions, 1):
                with st.expander(f"Q{i}. [{q.get('type','')}/{q.get('marks','')} marks] {q.get('question','')[:100]}..."):
                    st.markdown(f"**{q.get('question', '')}**")
                    if q.get('options'):
                        for opt in q['options']:
                            st.markdown(f"&nbsp;&nbsp;&nbsp;{opt}")
                    if show_answers:
                        ans = q.get('answer') or q.get('correct_answer', '')
                        exp = q.get('explanation', '')
                        if ans:
                            st.success(f"Answer: {ans}")
                        if exp:
                            st.info(f"Explanation: {exp}")

            if not st.session_state.get('assess_approved'):
                st.markdown('<div class="advisory-box">AI-generated. Verify technical accuracy before use.</div>', unsafe_allow_html=True)
                if st.button("Approve Assessment", type="primary"):
                    st.session_state['assess_approved'] = True
                    st.success("Assessment approved by faculty.")
                    st.rerun()
            else:
                st.success("Approved by faculty.")


# ════════════════════════════════════════════════════════════════════════════════
# PAGE: STUDENT ANALYTICS (CSV Pipeline)
# ════════════════════════════════════════════════════════════════════════════════
elif page == "Student Analytics":
    st.title("Student Analytics")
    st.caption("Upload student CSV → 6-stage pipeline → Granite interpretation + gap detection")

    # Demo CSV download
    demo_path = os.path.join(os.path.dirname(__file__), 'data', 'demo_students.csv')
    if os.path.exists(demo_path):
        with open(demo_path, 'rb') as f:
            st.download_button("Download Demo CSV", f.read(), "demo_students.csv",
                               mime="text/csv", help="40-student synthetic dataset")

    uploaded = st.file_uploader("Upload student CSV", type=["csv"])
    course_name = st.text_input("Course Name", value="Data Structures & Algorithms",
                                max_chars=200)

    if uploaded and st.button("Run Analysis Pipeline", type="primary"):
        try:
            df = pd.read_csv(uploaded)
        except Exception as exc:
            st.error(f"Could not read CSV: {exc}")
            st.stop()

        from app.pipeline import run_analysis_pipeline
        from app.agents.performance_analysis import validate_csv

        # Validate first
        is_valid, err, warnings = validate_csv(df)
        if not is_valid:
            st.error(f"Validation failed: {err}")
            st.stop()
        if warnings:
            for w in warnings:
                st.warning(w)

        # Run pipeline with progress
        progress = st.progress(0, text="Stage 1/6: Validating data...")
        result = {}

        with st.spinner("Running 6-stage analysis pipeline..."):
            try:
                result = run_analysis_pipeline(df, course_name)
            except Exception as exc:
                st.error(f"Pipeline error: {exc}")
                st.stop()

        progress.progress(100, text="Pipeline complete")

        if result.get('error'):
            st.error(result['error'])
            st.stop()

        st.session_state['pipeline_result'] = result

    if 'pipeline_result' in st.session_state:
        result = st.session_state['pipeline_result']
        perf = result.get('performance') or {}
        gaps = result.get('gaps') or []
        stage_log = result.get('stage_log') or []
        support = result.get('support_plan') or {}

        # Stage log
        with st.expander("Pipeline Stage Log", expanded=True):
            for s in stage_log:
                icon = "✅" if s['status'] == 'success' else ("❌" if s['status'] == 'failed' else "⏳")
                msg = s.get('message') or s.get('error') or ''
                st.markdown(f"{icon} **{s['stage']}** — {msg}")

        st.divider()

        # Performance stats
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Students", perf.get('num_students', 0))
        c2.metric("Avg Attendance", f"{perf.get('avg_attendance', 0)}%")
        c3.metric("Avg Score", f"{perf.get('overall_avg_score', 0)}%")
        c4.metric("At-Risk", len(perf.get('at_risk_students', [])))

        # Topic performance chart
        topic_stats = perf.get('topic_stats', {})
        if topic_stats:
            st.subheader("Topic Performance")
            ts_df = pd.DataFrame([
                {'Topic': k.replace('quiz_','').replace('_',' ').title(),
                 'Mean %': v['mean'], 'Below 50%': v['below_50_pct']}
                for k, v in topic_stats.items()
            ])
            st.bar_chart(ts_df.set_index('Topic')['Mean %'])

        # Gaps
        if gaps:
            st.subheader(f"Learning Gaps Detected ({len(gaps)})")
            for g in gaps:
                sev = g.get('severity', '')
                css_class = 'gap-critical' if sev == 'Critical' else ('gap-significant' if sev == 'Significant' else 'gap-moderate')
                intervention = g.get('intervention') or g.get('priority_action') or ''
                st.markdown(f"""<div class="{css_class}">
                  <strong>{g['topic']}</strong> <span style="color:#8b9ab0;font-size:0.85rem;">{sev} · {g['mean_score']}% avg · {g['below_50_pct']}% failing</span>
                  <div style="font-size:0.85rem;margin-top:4px;">{intervention}</div>
                </div>""", unsafe_allow_html=True)

        # AI interpretation
        ai_interp = result.get('ai_interpretation')
        if ai_interp:
            with st.expander("Granite Performance Interpretation"):
                st.markdown(ai_interp)

        # Support plan summary
        if support and support.get('executive_summary'):
            st.subheader("Learning Support Plan")
            st.info(support['executive_summary'])
            plans = support.get('topic_support_plans', [])
            if plans:
                for p in plans:
                    with st.expander(f"{p.get('topic','')} — {p.get('severity','')}"):
                        st.markdown(f"**Strategy:** {p.get('revision_strategy','')}")
                        for act in p.get('practice_activities', []):
                            st.markdown(f"- {act}")
            st.markdown('<div class="advisory-box">These recommendations are advisory. Faculty should review before sharing with students.</div>', unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════════
# PAGE: CO & ANALYTICS
# ════════════════════════════════════════════════════════════════════════════════
elif page == "CO & Analytics":
    st.title("CO & Analytics")
    st.caption("DB-computed CO attainment, topic performance and attendance — CS201 (45 students)")

    if not granite_available():
        st.warning("Granite credentials not set — AI pipeline will not run. Analytics still available.")

    courses = get_courses()
    course_options = {f"{c['code']} — {c['name']}": c['id'] for c in courses}
    selected = st.selectbox("Course", list(course_options.keys()))
    course_id = course_options[selected]

    try:
        analytics = db_analytics(course_id)
    except Exception as exc:
        st.error(f"Analytics error: {exc}")
        st.stop()

    tp = analytics['topic_performance']
    co = analytics['co_attainment']
    att = analytics['attendance']
    at_risk = analytics['at_risk_students']

    # Summary stats
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Students", att['total_students'])
    _avg_att = att['class_avg_pct']
    c2.metric("Avg Attendance", f"{_avg_att}%" if _avg_att is not None else "N/A")
    _co_att = co['overall_attainment_pct']
    c3.metric("CO Attainment", f"{_co_att}%" if _co_att is not None else "N/A")
    c4.metric("At-Risk", len(at_risk))

    st.divider()
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Topic Performance")
        if tp:
            tp_df = pd.DataFrame([{
                'Topic': t['title'],
                'Quiz Avg %': t['quiz_avg_pct'],
                'Assign Avg %': t['assignment_avg_pct'],
                'Combined %': t['combined_avg_pct'],
                'Severity': t['gap_severity'],
            } for t in tp])
            st.dataframe(tp_df, use_container_width=True, hide_index=True)
            tp_chart = tp_df[tp_df['Combined %'].notna()].set_index('Topic')['Combined %']
            if not tp_chart.empty:
                st.bar_chart(tp_chart)

    with col_right:
        st.subheader("CO Attainment")
        co_rows = [{
            'CO': o['co_code'],
            'Bloom': o['bloom_level'],
            'Attainment %': o['attainment_pct'],
            'Level': o['level_label'],
        } for o in co['outcomes']]
        if co_rows:
            co_df = pd.DataFrame(co_rows)
            st.dataframe(co_df, use_container_width=True, hide_index=True)
            co_chart = co_df[co_df['Attainment %'].notna()].set_index('CO')['Attainment %']
            if not co_chart.empty:
                st.bar_chart(co_chart)
        else:
            st.caption("No CO attainment data available.")

    # Attendance distribution
    st.subheader("Attendance Distribution")
    dist = att.get('distribution', {})
    if dist:
        dist_df = pd.DataFrame([{'Band': k, 'Students': v} for k, v in dist.items()])
        st.bar_chart(dist_df.set_index('Band'))

    # At-risk
    if at_risk:
        st.subheader(f"At-Risk Students ({len(at_risk)})")
        st.caption("Criteria: attendance < 60% OR avg score < 50%. Review individually before action.")
        risk_df = pd.DataFrame([{
            'Student': s['student_code'],
            'Section': s['section'] or '',
            'Attendance %': s['attendance_pct'],
            'Avg Score %': s['avg_score_pct'],
            'Priority': s['priority'],
        } for s in at_risk])
        st.dataframe(risk_df, use_container_width=True, hide_index=True)

    # Run AI Pipeline
    st.divider()
    if granite_available():
        st.subheader("AI Pipeline")
        st.caption("Runs gap detection, Granite interventions, support plan and CO interpretation")
        if st.button("Run Full AI Pipeline", type="primary"):
            with st.spinner("Running 6-stage AI pipeline... (may take 30-60s)"):
                try:
                    flask_app = get_flask_app()
                    with flask_app.app_context():
                        from app.analytics import (compute_topic_performance,
                            compute_at_risk_students, compute_attendance_summary,
                            compute_co_attainment)
                        from app.agents.gap_detection import detect_gaps, ai_explain_gaps
                        from app.agents.learning_support import generate_support_plan
                        from app.agents.co_attainment import interpret_co_attainment

                        # Build gap data
                        t_perf = compute_topic_performance(course_id)
                        att_sum = compute_attendance_summary(course_id)
                        at_risk_list = compute_at_risk_students(course_id)
                        topic_stats = {
                            t['title']: {'mean': t['combined_avg_pct'], 'below_50_pct': 0,
                                         'below_40_pct': 0, 'median': t['combined_avg_pct'], 'std': 0}
                            for t in t_perf if t.get('combined_avg_pct') is not None
                        }
                        gaps = detect_gaps(topic_stats)
                        gaps = ai_explain_gaps(gaps, att_sum.get('total_students', 0))

                        overall_avg = (sum(t['combined_avg_pct'] for t in t_perf if t.get('combined_avg_pct') is not None)
                                       / max(1, sum(1 for t in t_perf if t.get('combined_avg_pct') is not None)))
                        perf_for_support = {
                            'num_students': att_sum.get('total_students', 0),
                            'avg_attendance': att_sum.get('class_avg_pct'),
                            'overall_avg_score': round(overall_avg, 1),
                            'at_risk_students': at_risk_list,
                        }
                        support_plan = generate_support_plan(perf_for_support, gaps, selected.split('—')[-1].strip())

                        co_att = compute_co_attainment(course_id)
                        co_interp = interpret_co_attainment(co_att, selected.split('—')[-1].strip())

                        st.session_state['ai_pipeline'] = {
                            'gaps': gaps, 'support_plan': support_plan,
                            'co_interp': co_interp,
                        }
                except Exception as exc:
                    st.error(f"Pipeline error: {exc}")

        if 'ai_pipeline' in st.session_state:
            pipeline = st.session_state['ai_pipeline']
            gaps = pipeline.get('gaps', [])
            sp = pipeline.get('support_plan', {})
            co_interp = pipeline.get('co_interp', '')

            if gaps:
                st.subheader("Detected Gaps")
                for g in gaps:
                    sev = g.get('severity', '')
                    css = 'gap-critical' if sev == 'Critical' else ('gap-significant' if sev == 'Significant' else 'gap-moderate')
                    st.markdown(f'<div class="{css}"><strong>{g["topic"]}</strong> ({sev} · {g["mean_score"]}%)'
                                f'<div style="font-size:0.85rem">{g.get("intervention","")}</div></div>',
                                unsafe_allow_html=True)

            if sp and sp.get('executive_summary'):
                st.subheader("Learning Support Plan")
                st.info(sp['executive_summary'])
                for p in sp.get('topic_support_plans', []):
                    with st.expander(f"{p.get('topic','')} — {p.get('severity','')}"):
                        st.write(p.get('revision_strategy', ''))
                        for act in p.get('practice_activities', []):
                            st.markdown(f"- {act}")

            if co_interp:
                with st.expander("Granite CO Attainment Interpretation"):
                    st.markdown(co_interp)

            st.markdown('<div class="advisory-box">All recommendations are advisory. Faculty approval required before action.</div>', unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════════
# PAGE: LEARNING SUPPORT
# ════════════════════════════════════════════════════════════════════════════════
elif page == "Learning Support":
    st.title("Learning Support")
    st.caption("Gap-matched resources and at-risk student support — CS201")

    courses = get_courses()
    cs201 = next((c for c in courses if c['code'] == 'CS201'), None)
    if not cs201:
        st.warning("CS201 not found. Run seed_academic.py first.")
        st.stop()

    flask_app = get_flask_app()
    with flask_app.app_context():
        from app.analytics import compute_topic_performance, compute_at_risk_students
        from app.models import LearningResource, SyllabusUnit

        tp = compute_topic_performance(cs201['id'])
        at_risk = compute_at_risk_students(cs201['id'])
        weak = [t for t in tp if t['gap_severity'] in ('Critical', 'Significant', 'Moderate')]

        # Fetch resources for weak units
        weak_resources = {}
        for t in weak:
            res = LearningResource.query.filter_by(
                course_id=cs201['id'], unit_id=t['unit_id']).all()
            weak_resources[t['unit_id']] = {
                'title': t['title'], 'severity': t['gap_severity'],
                'score': t['combined_avg_pct'],
                'resources': [{'title': r.title, 'type': r.resource_type, 'url': r.url_or_path}
                              for r in res],
            }

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Topics", len(tp))
    c2.metric("Weak Topics", len(weak))
    c3.metric("At-Risk Students", len(at_risk))

    if weak:
        st.subheader("Topics Requiring Attention")
        for t in weak:
            sev = t['gap_severity']
            color = "#f85149" if sev == "Critical" else ("#d29922" if sev == "Significant" else "#3b82f6")
            info = weak_resources.get(t['unit_id'], {})
            with st.expander(f"Unit {t['unit_number']}: {t['title']} — {sev} ({t.get('combined_avg_pct')}%)"):
                st.markdown(f"<span style='color:{color};font-weight:700;'>{sev}</span> · "
                            f"Combined avg: {t.get('combined_avg_pct')}%", unsafe_allow_html=True)
                resources = info.get('resources', [])
                if resources:
                    st.markdown("**Recommended Resources:**")
                    for r in resources:
                        icon = {"video": "▶️", "link": "🔗", "textbook": "📖"}.get(r['type'], "📄")
                        if r['url']:
                            st.markdown(f"{icon} [{r['title']}]({r['url']})")
                        else:
                            st.markdown(f"{icon} {r['title']}")
                else:
                    st.caption("No resources linked for this topic.")

    if at_risk:
        st.divider()
        st.subheader(f"At-Risk Students ({len(at_risk)})")
        st.caption("Criteria: attendance < 60% OR avg score < 50%")
        risk_df = pd.DataFrame([{
            'Student': s['student_code'],
            'Attendance %': s['attendance_pct'],
            'Avg Score %': s['avg_score_pct'],
            'Priority': s['priority'],
        } for s in at_risk])
        st.dataframe(risk_df, use_container_width=True, hide_index=True)

    st.markdown('<div class="advisory-box">Faculty should review each at-risk student individually before intervention.</div>', unsafe_allow_html=True)
