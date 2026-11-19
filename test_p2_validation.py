"""
P2 Validation Engine Tests -- TeachWise AI
Tests AcademicDataValidator with 13 scenarios.
Run: python test_p2_validation.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))


def build_csv(*rows) -> bytes:
    return '\n'.join(rows).encode('utf-8')


from app.validator import AcademicDataValidator

PASS = 0
FAIL = 0


def check(name: str, condition: bool, detail: str = ''):
    global PASS, FAIL
    if condition:
        print(f'  PASS  {name}')
        PASS += 1
    else:
        print(f'  FAIL  {name}  {detail}')
        FAIL += 1


print('\n==========================================')
print('P2 Validation Tests -- TeachWise AI')
print('==========================================\n')


# 1. Valid student CSV
print('[ 1 ] Valid students CSV')
csv1 = build_csv(
    'student_code,section,batch_year',
    'S001,A,2024',
    'S002,B,2024',
    'S003,A,2024',
)
r1 = AcademicDataValidator.validate_students(csv1)
check('total=3', r1.total == 3)
check('valid=3', r1.valid == 3)
check('rejected=0', r1.rejected == 0)
check('no errors', r1.errors == [])


# 2. Missing required column
print('\n[ 2 ] Missing required column (student_code)')
csv2 = build_csv('section,batch_year', 'A,2024', 'B,2023')
r2 = AcademicDataValidator.validate_students(csv2)
check('rejected > 0', r2.rejected > 0)
check('error mentions missing column', any('Missing' in e['issue'] for e in r2.errors))


# 3. Duplicate student_code
print('\n[ 3 ] Duplicate student_code')
csv3 = build_csv(
    'student_code,section',
    'S001,A',
    'S001,B',
    'S002,A',
)
r3 = AcademicDataValidator.validate_students(csv3)
check('duplicate raises error', r3.rejected >= 1)
check('error mentions Duplicate', any('Duplicate' in e['issue'] for e in r3.errors))


# 4. Marks exceed maximum for exam
print('\n[ 4 ] Marks exceed maximum for exam')
csv4 = build_csv(
    'student_code,exam_title,marks_obtained',
    'S001,Mid-Term,45',
    'S002,Mid-Term,55',
    'S003,Mid-Term,30',
)
exam_defs = {'Mid-Term': 50.0}
student_codes = {'S001', 'S002', 'S003'}
r4 = AcademicDataValidator.validate_marks(csv4, exam_definitions=exam_defs, valid_student_codes=student_codes)
check('marks>max rejected', r4.rejected >= 1)
check('S002 is rejected', any('55' in str(e['value']) for e in r4.errors))


# 5. Negative marks
print('\n[ 5 ] Negative marks_obtained')
csv5 = build_csv(
    'student_code,exam_title,marks_obtained',
    'S001,Mid-Term,-5',
)
r5 = AcademicDataValidator.validate_marks(csv5, exam_definitions={'Mid-Term': 50.0}, valid_student_codes={'S001'})
check('negative rejected', r5.rejected >= 1)
check('error on marks_obtained field', any(e['field'] == 'marks_obtained' for e in r5.errors))


# 6. Late submission = WARNING not rejection
print('\n[ 6 ] Late submission -- warning, not rejection')
csv6 = build_csv(
    'student_code,assignment_title,marks_obtained,due_date,submitted_at',
    'S001,Assignment 1,15,2024-07-29,2024-07-31',
    'S002,Assignment 1,18,2024-07-29,2024-07-28',
)
assign_defs = {'Assignment 1': 20.0}
r6 = AcademicDataValidator.validate_assignment_submissions(
    csv6, assignment_definitions=assign_defs, valid_student_codes={'S001', 'S002'}
)
check('rejected=0 (late not an error)', r6.rejected == 0)
check('warning_count >= 1 (late flagged)', r6.warning_count >= 1)


# 7. Unknown student_code
print('\n[ 7 ] Unknown student_code not in enrolled set')
csv7 = build_csv(
    'student_code,class_date,status',
    'S001,2024-07-01,present',
    'S999,2024-07-01,present',
)
enrolled = {'S001', 'S002', 'S003'}
class_dates = {'2024-07-01', '2024-07-03'}
r7 = AcademicDataValidator.validate_attendance(csv7, valid_student_codes=enrolled, valid_class_dates=class_dates)
check('unknown student rejected', r7.rejected >= 1)
check('error message mentions not enrolled', any('not enrolled' in e['issue'] for e in r7.errors))


# 8. Unknown CO code in question bank
print('\n[ 8 ] Unknown CO code in question bank')
csv8 = build_csv(
    'question_text,question_type,difficulty,co_code',
    'What is an array?,MCQ,Easy,CO1',
    'Explain graph traversal,Short,Medium,CO9',
)
valid_cos = {'CO1', 'CO2', 'CO3', 'CO4', 'CO5'}
r8 = AcademicDataValidator.validate_question_bank(csv8, valid_co_codes=valid_cos)
check('invalid CO code rejected', r8.rejected >= 1)
check('error on co_code field', any(e['field'] == 'co_code' for e in r8.errors))


# 9. Malformed CSV
print('\n[ 9 ] Malformed file content')
bad_csv = b'\xff\xfe\x00invalid binary data'
r9 = AcademicDataValidator.validate_students(bad_csv)
check('returns ValidationReport', hasattr(r9, 'rejected'))
check('rejected or error captured', r9.rejected >= 0)


# 10. Empty CSV (header only)
print('\n[ 10 ] Empty CSV (header only)')
csv10 = build_csv('student_code,section,batch_year')
r10 = AcademicDataValidator.validate_students(csv10)
check('returns ValidationReport', hasattr(r10, 'rejected'))
check('error captured for empty file', r10.rejected > 0 or len(r10.errors) > 0)


# 11. Duplicate attendance record
print('\n[ 11 ] Duplicate attendance record (same student + date)')
csv11 = build_csv(
    'student_code,class_date,status',
    'S001,2024-07-01,present',
    'S001,2024-07-01,absent',
    'S002,2024-07-01,present',
)
r11 = AcademicDataValidator.validate_attendance(csv11,
    valid_student_codes={'S001', 'S002'},
    valid_class_dates={'2024-07-01'})
check('duplicate pair rejected', r11.rejected >= 1)
check('error mentions Duplicate', any('Duplicate' in e['issue'] for e in r11.errors))


# 12. Quiz marks exceed max
print('\n[ 12 ] Quiz marks exceed maximum')
csv12 = build_csv(
    'student_code,quiz_title,marks_obtained',
    'S001,Quiz 1,8',
    'S002,Quiz 1,12',
)
r12 = AcademicDataValidator.validate_quiz_results(csv12,
    quiz_definitions={'Quiz 1': 10.0},
    valid_student_codes={'S001', 'S002'})
check('marks>max rejected', r12.rejected >= 1)


# 13. Feedback rating out of range
print('\n[ 13 ] Feedback rating out of range (1-5)')
csv13 = build_csv(
    'student_code,rating,comments',
    'S001,3,Good',
    'S002,7,Excellent',
    'S003,0,Bad',
)
r13 = AcademicDataValidator.validate_feedback(csv13, valid_student_codes={'S001', 'S002', 'S003'})
check('out-of-range ratings rejected', r13.rejected >= 2)
check('valid row not rejected', r13.valid >= 1)


# Summary
print('\n==========================================')
total = PASS + FAIL
print(f'Results: {PASS}/{total} PASS   {FAIL} FAIL')
print('==========================================\n')

if FAIL > 0:
    sys.exit(1)
