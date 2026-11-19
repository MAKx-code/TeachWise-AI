"""
Idempotent CS201 synthetic dataset seeder.
Run once after DB creation: python seed_academic.py

Creates:
  - 45 students (S001–S045)
  - 5 syllabus units, 5 COs, 7 CO-unit mappings
  - 40 attendance classes → 1,800 attendance records
  - 5 assignments → 225 submissions (15 late = warnings, not rejections)
  - 5 quizzes → 225 results
  - 2 exams → 90 exam marks
  - 50 questions (10/unit)
  - 15 learning resources (3/unit)
  - 45 student feedback records

Performance design (seed=42):
  Arrays:         ~74% avg   (no gap)
  Linked Lists:   ~51% avg   (Significant gap)
  Stacks/Queues:  ~68% avg   (no gap)
  Trees:          ~72% avg   (no gap)
  Graphs:         ~44% avg   (Critical gap)
  ~10 students at-risk (low attendance + low marks)
"""

import os
import sys
import random
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))
random.seed(42)

from app import create_app, db
from app.models import (
    Course, Student, Enrollment, SyllabusUnit, CourseOutcome, CoUnitMapping,
    AttendanceClass, AttendanceRecord, Assignment, AssignmentSubmission,
    Quiz, QuizResult, Exam, ExamMark, Question, LearningResource,
    StudentFeedback
)


def seed_academic():
    app = create_app()
    with app.app_context():
        # Guard: idempotent
        if Student.query.count() > 0:
            print("Academic data already seeded. Skipping.")
            return

        course = Course.query.filter_by(code='CS201').first()
        if not course:
            print("ERROR: CS201 course not found. Run the app once first to seed courses.")
            return

        print(f"Seeding CS201 academic data (course id={course.id})...")

        # ── 1. Students ───────────────────────────────────────────────────────
        students = []
        for i in range(1, 46):
            s = Student(
                student_code=f'S{i:03d}',
                section='A' if i <= 23 else 'B',
                batch_year=2024
            )
            db.session.add(s)
            students.append(s)
        db.session.flush()
        print(f"  Students: {len(students)}")

        # ── 2. Enrollments ────────────────────────────────────────────────────
        for s in students:
            db.session.add(Enrollment(student_id=s.id, course_id=course.id))
        db.session.flush()

        # ── 3. Syllabus Units ─────────────────────────────────────────────────
        unit_specs = [
            (1, 'Arrays & Strings', 'Fundamentals of arrays, multi-dimensional arrays, string operations and algorithms.'),
            (2, 'Linked Lists', 'Singly, doubly and circular linked lists; insertion, deletion and traversal.'),
            (3, 'Stacks & Queues', 'Stack and queue ADTs, implementations, applications including expression evaluation.'),
            (4, 'Trees', 'Binary trees, BSTs, AVL trees, tree traversals and applications.'),
            (5, 'Graphs', 'Graph representations, BFS, DFS, shortest path algorithms and spanning trees.'),
        ]
        units = []
        for num, title, desc in unit_specs:
            u = SyllabusUnit(course_id=course.id, unit_number=num, title=title, description=desc)
            db.session.add(u)
            units.append(u)
        db.session.flush()

        # ── 4. Course Outcomes ────────────────────────────────────────────────
        co_specs = [
            ('CO1', 'Apply array and string manipulation techniques to solve computational problems.', 'Apply'),
            ('CO2', 'Implement and analyse linked list operations for dynamic data management.', 'Analyse'),
            ('CO3', 'Design stack and queue-based solutions for real-world problems.', 'Apply'),
            ('CO4', 'Construct and traverse tree data structures for hierarchical data.', 'Analyse'),
            ('CO5', 'Evaluate graph algorithms for connectivity and shortest-path problems.', 'Evaluate'),
        ]
        cos = []
        for code, stmt, bloom in co_specs:
            co = CourseOutcome(course_id=course.id, co_code=code, statement=stmt, bloom_level=bloom)
            db.session.add(co)
            cos.append(co)
        db.session.flush()

        # ── 5. CO-Unit Mappings (7 mappings — some COs span multiple units) ───
        # Primary: each CO maps to its unit; secondary cross-mappings
        mapping_pairs = [
            (0, 0), (1, 1), (2, 2), (3, 3), (4, 4),  # CO1→U1, CO2→U2 ... (primary)
            (3, 2), (4, 3),                             # CO4→U3 (trees span stacks), CO5→U4
        ]
        for co_idx, unit_idx in mapping_pairs:
            db.session.add(CoUnitMapping(co_id=cos[co_idx].id, unit_id=units[unit_idx].id))
        db.session.flush()

        # ── 6. Attendance Classes (40 classes across 14 weeks) ────────────────
        start_date = date(2024, 7, 1)
        classes = []
        class_topics = [
            # Unit 1: 8 classes
            ('Introduction to Arrays', 0), ('Array Operations', 0), ('Multi-dim Arrays', 0),
            ('String Basics', 0), ('String Algorithms', 0), ('Array Searching', 0),
            ('Array Sorting', 0), ('Arrays Problem Solving', 0),
            # Unit 2: 8 classes
            ('Singly Linked List', 1), ('Linked List Operations', 1), ('Doubly Linked List', 1),
            ('Circular Linked List', 1), ('Linked List Applications', 1), ('Linked List vs Array', 1),
            ('Linked List Problems', 1), ('Linked List Review', 1),
            # Unit 3: 8 classes
            ('Stack Introduction', 2), ('Stack Implementation', 2), ('Stack Applications', 2),
            ('Queue Introduction', 2), ('Queue Variants', 2), ('Deque & Priority Queue', 2),
            ('Expression Evaluation', 2), ('Stacks & Queues Review', 2),
            # Unit 4: 8 classes
            ('Binary Trees', 3), ('Tree Traversals', 3), ('BST Introduction', 3),
            ('BST Operations', 3), ('AVL Trees', 3), ('Heap Data Structure', 3),
            ('Tree Applications', 3), ('Trees Review', 3),
            # Unit 5: 8 classes
            ('Graph Introduction', 4), ('Graph Representations', 4), ('BFS Algorithm', 4),
            ('DFS Algorithm', 4), ('Shortest Path - Dijkstra', 4), ('Minimum Spanning Tree', 4),
            ('Graph Applications', 4), ('Graphs Review', 4),
        ]

        d = start_date
        for idx, (topic, unit_idx) in enumerate(class_topics):
            # 3 classes per week (Mon, Wed, Fri)
            day_offset = (idx // 3) * 7 + [0, 2, 4][idx % 3]
            class_date = start_date + timedelta(days=day_offset)
            ac = AttendanceClass(
                course_id=course.id,
                unit_id=units[unit_idx].id,
                class_date=class_date,
                topic=topic
            )
            db.session.add(ac)
            classes.append(ac)
        db.session.flush()
        print(f"  Classes: {len(classes)}")

        # ── 7. Attendance Records (1,800 = 45 × 40) ───────────────────────────
        # Intentional profile variation:
        # ~10 at-risk students (S001–S010): low attendance 40–59%
        # ~25 average (S011–S035): attendance 65–85%
        # ~10 strong (S036–S045): attendance 85–98%
        att_records = 0
        for s in students:
            idx = int(s.student_code[1:]) - 1
            if idx < 10:        base_att = 0.50   # at-risk
            elif idx < 35:      base_att = 0.75   # average
            else:               base_att = 0.92   # strong

            for cls in classes:
                roll = random.random()
                attend_prob = base_att + random.uniform(-0.08, 0.08)
                attend_prob = max(0.3, min(0.99, attend_prob))
                if roll < attend_prob:
                    status = 'late' if random.random() < 0.05 else 'present'
                else:
                    status = 'excused' if random.random() < 0.1 else 'absent'
                db.session.add(AttendanceRecord(
                    student_id=s.id, class_id=cls.id, status=status
                ))
                att_records += 1

        db.session.flush()
        print(f"  Attendance records: {att_records}")

        # ── 8. Assignments (5, one per unit) ──────────────────────────────────
        assignment_specs = [
            ('Arrays & Strings Assignment', 0, 20.0, date(2024, 7, 29)),
            ('Linked Lists Assignment', 1, 20.0, date(2024, 8, 19)),
            ('Stacks & Queues Assignment', 2, 20.0, date(2024, 9, 9)),
            ('Trees Assignment', 3, 20.0, date(2024, 9, 30)),
            ('Graphs Assignment', 4, 20.0, date(2024, 10, 21)),
        ]
        assignments = []
        for title, unit_idx, max_m, due in assignment_specs:
            a = Assignment(
                course_id=course.id, unit_id=units[unit_idx].id,
                title=title, max_marks=max_m, due_date=due
            )
            db.session.add(a)
            assignments.append(a)
        db.session.flush()

        # ── 9. Assignment Submissions (225, with ~15 late = warnings) ─────────
        # Topic performance means (% of max):
        unit_means = [0.74, 0.51, 0.68, 0.72, 0.44]  # Arrays, LL, S&Q, Trees, Graphs
        late_count = 0
        sub_count = 0
        for s in students:
            idx = int(s.student_code[1:]) - 1
            for a_idx, (a, (_, unit_idx, max_m, due)) in enumerate(zip(assignments, assignment_specs)):
                mean_pct = unit_means[unit_idx]
                if idx < 10:    mean_pct *= 0.65   # at-risk students score lower
                elif idx < 35:  mean_pct *= 0.90
                # else strong: use full mean

                score = random.gauss(mean_pct * max_m, max_m * 0.12)
                score = round(max(0.0, min(max_m, score)), 1)

                # ~7% of submissions are late (warning, not rejection)
                is_late = random.random() < 0.07
                sub_at = datetime.combine(due, datetime.min.time()) + timedelta(days=random.randint(0, 2 if not is_late else 5))
                if is_late:
                    late_count += 1

                db.session.add(AssignmentSubmission(
                    assignment_id=a.id, student_id=s.id,
                    marks_obtained=score, submitted_at=sub_at, is_late=is_late
                ))
                sub_count += 1
        db.session.flush()
        print(f"  Submissions: {sub_count} ({late_count} late warnings)")

        # ── 10. Quizzes (5, one per unit) ─────────────────────────────────────
        quiz_specs = [
            ('Quiz 1: Arrays', 0, 10.0, date(2024, 7, 22)),
            ('Quiz 2: Linked Lists', 1, 10.0, date(2024, 8, 12)),
            ('Quiz 3: Stacks & Queues', 2, 10.0, date(2024, 9, 2)),
            ('Quiz 4: Trees', 3, 10.0, date(2024, 9, 23)),
            ('Quiz 5: Graphs', 4, 10.0, date(2024, 10, 14)),
        ]
        quizzes = []
        for title, unit_idx, max_m, qdate in quiz_specs:
            q = Quiz(
                course_id=course.id, unit_id=units[unit_idx].id,
                title=title, max_marks=max_m, quiz_date=qdate
            )
            db.session.add(q)
            quizzes.append(q)
        db.session.flush()

        qr_count = 0
        for s in students:
            idx = int(s.student_code[1:]) - 1
            for q_idx, (quiz, (_, unit_idx, max_m, _d)) in enumerate(zip(quizzes, quiz_specs)):
                mean_pct = unit_means[unit_idx]
                if idx < 10:    mean_pct *= 0.65
                elif idx < 35:  mean_pct *= 0.90
                score = round(max(0.0, min(max_m, random.gauss(mean_pct * max_m, max_m * 0.15))), 1)
                db.session.add(QuizResult(quiz_id=quiz.id, student_id=s.id, marks_obtained=score))
                qr_count += 1
        db.session.flush()
        print(f"  Quiz results: {qr_count}")

        # ── 11. Exams (2: mid-term and end-term) ──────────────────────────────
        mid_exam = Exam(course_id=course.id, exam_type='mid', title='Mid-Term Examination',
                        max_marks=50.0, exam_date=date(2024, 9, 10))
        end_exam = Exam(course_id=course.id, exam_type='end', title='End-Term Examination',
                        max_marks=100.0, exam_date=date(2024, 11, 5))
        db.session.add_all([mid_exam, end_exam])
        db.session.flush()

        em_count = 0
        for s in students:
            idx = int(s.student_code[1:]) - 1
            # Mid-term covers units 1-3; overall mean based on first 3 units
            mid_mean_pct = sum(unit_means[:3]) / 3
            end_mean_pct = sum(unit_means) / 5
            if idx < 10:
                mid_mean_pct *= 0.65; end_mean_pct *= 0.65
            elif idx < 35:
                mid_mean_pct *= 0.90; end_mean_pct *= 0.90

            mid_score = round(max(0.0, min(50.0, random.gauss(mid_mean_pct * 50.0, 50.0 * 0.12))), 1)
            end_score = round(max(0.0, min(100.0, random.gauss(end_mean_pct * 100.0, 100.0 * 0.12))), 1)
            db.session.add_all([
                ExamMark(exam_id=mid_exam.id, student_id=s.id, marks_obtained=mid_score),
                ExamMark(exam_id=end_exam.id, student_id=s.id, marks_obtained=end_score),
            ])
            em_count += 2
        db.session.flush()
        print(f"  Exam marks: {em_count}")

        # ── 12. Question Bank (50 questions, 10 per unit) ─────────────────────
        qtypes = ['MCQ', 'Short', 'Long', 'Coding']
        difficulties = ['Easy', 'Medium', 'Hard']
        blooms = ['Remember', 'Understand', 'Apply', 'Analyse']
        q_count = 0
        for u_idx, unit in enumerate(units):
            co = cos[u_idx]
            for qnum in range(1, 11):
                db.session.add(Question(
                    course_id=course.id,
                    unit_id=unit.id,
                    co_id=co.id,
                    question_text=f'{unit.title} — Question {qnum}: Demonstrate understanding of {unit.title.lower()} concepts.',
                    question_type=qtypes[qnum % len(qtypes)],
                    difficulty=difficulties[qnum % len(difficulties)],
                    bloom_level=blooms[qnum % len(blooms)]
                ))
                q_count += 1
        db.session.flush()
        print(f"  Questions: {q_count}")

        # ── 13. Learning Resources (15, 3 per unit) ───────────────────────────
        resource_specs = [
            ('Arrays in Python - GeeksForGeeks', 'link', 'https://geeksforgeeks.org/arrays', 0),
            ('Introduction to Arrays (Video)', 'video', 'https://youtube.com/example/arrays', 0),
            ('Data Structures by Cormen (Ch.2)', 'textbook', None, 0),
            ('Linked Lists Visualized', 'video', 'https://youtube.com/example/linkedlists', 1),
            ('Linked Lists - CS Dojo', 'link', 'https://csdojo.io/linked-lists', 1),
            ('Linked Lists Practice Problems', 'pdf', None, 1),
            ('Stacks & Queues - MIT OpenCourseWare', 'link', 'https://ocw.mit.edu', 2),
            ('Stack Animation Tool', 'link', 'https://visualgo.net/stacks', 2),
            ('Expression Evaluation Tutorial', 'pdf', None, 2),
            ('Binary Trees - Visualgo', 'link', 'https://visualgo.net/binarytree', 3),
            ('Tree Traversals - MIT Lecture', 'video', 'https://ocw.mit.edu/trees', 3),
            ('AVL Trees Explained', 'pdf', None, 3),
            ('Graph Algorithms - Stanford', 'link', 'https://stanford.edu/graphs', 4),
            ('Dijkstra Visualizer', 'link', 'https://pathfinding.io', 4),
            ('Graph Theory - Introduction (Video)', 'video', 'https://youtube.com/example/graphs', 4),
        ]
        for title, rtype, url, unit_idx in resource_specs:
            db.session.add(LearningResource(
                course_id=course.id, unit_id=units[unit_idx].id,
                title=title, resource_type=rtype, url_or_path=url,
                description=f'Resource for {units[unit_idx].title}'
            ))
        db.session.flush()
        print(f"  Resources: {len(resource_specs)}")

        # ── 14. Student Feedback (45 records) ─────────────────────────────────
        comments_pool = [
            'More examples would help.',
            'Good pace. Enjoyed the labs.',
            'Graphs topic was hard to follow.',
            'Practice problems were very useful.',
            'Would like more interactive sessions.',
            'Linked lists need more time.',
            None,
        ]
        fb_count = 0
        for s in students:
            rating = random.randint(2, 5)
            db.session.add(StudentFeedback(
                course_id=course.id, student_id=s.id,
                week_number=14, rating=rating,
                comments=random.choice(comments_pool)
            ))
            fb_count += 1
        db.session.flush()
        print(f"  Feedback: {fb_count}")

        db.session.commit()
        print("\nSeeding complete.")
        print(f"  Total attendance records: {att_records}  (expected: 1,800)")
        assert att_records == 1800, f"Expected 1800, got {att_records}"
        print("  Assertion passed: 1,800 attendance records confirmed.")


if __name__ == '__main__':
    seed_academic()
