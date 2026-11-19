"""
Academic Data Validation Engine — TeachWise AI
Deterministic Python validation. Granite is never called here.

Supports:
  - attendance CSV
  - marks/exam CSV
  - quiz results CSV
  - assignment submissions CSV
  - student records CSV
  - question bank CSV
  - feedback CSV

Each validator returns a ValidationReport with:
  total, valid, rejected, warning_count,
  errors [{row, field, value, issue, suggestion}],
  warnings [{row, field, value, issue, suggestion}]
"""

from __future__ import annotations
import io
import json
from dataclasses import dataclass, field, asdict
from typing import Any

import pandas as pd


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class ValidationIssue:
    row: int
    field: str
    value: Any
    issue: str
    suggestion: str


@dataclass
class ValidationReport:
    import_type: str
    total: int = 0
    valid: int = 0
    rejected: int = 0
    warning_count: int = 0
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

    def add_error(self, row, fld, val, issue, suggestion):
        self.errors.append(ValidationIssue(row, fld, str(val)[:100], issue, suggestion).__dict__)
        self.rejected += 1

    def add_warning(self, row, fld, val, issue, suggestion):
        self.warnings.append(ValidationIssue(row, fld, str(val)[:100], issue, suggestion).__dict__)
        self.warning_count += 1

    def to_dict(self):
        return {
            'import_type': self.import_type,
            'total': self.total,
            'valid': self.valid,
            'rejected': self.rejected,
            'warning_count': self.warning_count,
            'errors': self.errors,
            'warnings': self.warnings,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


# ── Utilities ─────────────────────────────────────────────────────────────────

def _read_csv_safe(file_bytes: bytes) -> tuple[pd.DataFrame | None, str]:
    """Parse CSV bytes. Returns (df, error_msg). error_msg='' on success."""
    if len(file_bytes) > 5 * 1024 * 1024:
        return None, 'File exceeds 5MB limit.'
    if len(file_bytes) == 0:
        return None, 'File is empty.'
    try:
        text = file_bytes.decode('utf-8')
    except UnicodeDecodeError:
        try:
            text = file_bytes.decode('latin-1')
        except Exception:
            return None, 'File encoding could not be read. Please save as UTF-8.'
    try:
        df = pd.read_csv(io.StringIO(text))
        if len(df) == 0:
            return None, 'CSV contains no data rows.'
        return df, ''
    except Exception as exc:
        return None, f'Could not parse CSV: {exc}'


def _require_cols(df: pd.DataFrame, required: list[str]) -> str:
    """Return error message if any required column is missing."""
    df.columns = [c.lower().strip() for c in df.columns]
    missing = [c for c in required if c not in df.columns]
    if missing:
        return f'Missing required columns: {", ".join(missing)}'
    return ''


def _is_valid_number(val, lo=0, hi=None) -> bool:
    try:
        f = float(val)
        if f < lo:
            return False
        if hi is not None and f > hi:
            return False
        return True
    except (TypeError, ValueError):
        return False


# ── Validators ────────────────────────────────────────────────────────────────

class AcademicDataValidator:

    # ── Students ──────────────────────────────────────────────────────────────
    @staticmethod
    def validate_students(file_bytes: bytes) -> ValidationReport:
        """Required columns: student_code. Optional: section, batch_year."""
        report = ValidationReport('students')
        df, err = _read_csv_safe(file_bytes)
        if err:
            report.add_error(0, 'file', '', err, 'Fix the file and re-upload.')
            return report

        df.columns = [c.lower().strip() for c in df.columns]
        col_err = _require_cols(df, ['student_code'])
        if col_err:
            report.add_error(0, 'columns', '', col_err, 'Add required columns.')
            return report

        report.total = len(df)
        seen_codes = set()

        for row_idx, row in df.iterrows():
            rn = row_idx + 2  # 1-based with header
            code = str(row.get('student_code', '')).strip()

            if not code or code.lower() == 'nan':
                report.add_error(rn, 'student_code', code, 'student_code is required.', 'Provide a unique student code (e.g. S001).')
                continue

            import re
            if not re.match(r'^S\d{3,4}$', code, re.IGNORECASE):
                report.add_warning(rn, 'student_code', code,
                    f'student_code "{code}" does not match expected pattern S001–S9999.',
                    'Use format S followed by 3–4 digits (e.g. S001).')

            if code in seen_codes:
                report.add_error(rn, 'student_code', code, f'Duplicate student_code: {code}.', 'Remove or correct the duplicate row.')
                continue
            seen_codes.add(code)

            if 'batch_year' in df.columns:
                yr = row.get('batch_year')
                if pd.notna(yr) and not _is_valid_number(yr, 2000, 2050):
                    report.add_warning(rn, 'batch_year', yr, 'batch_year is outside expected range 2000–2050.', 'Check the year value.')

        report.valid = report.total - report.rejected
        return report

    # ── Attendance ────────────────────────────────────────────────────────────
    @staticmethod
    def validate_attendance(
        file_bytes: bytes,
        valid_student_codes: set[str] | None = None,
        valid_class_dates: set[str] | None = None,
    ) -> ValidationReport:
        """Required: student_code, class_date, status."""
        report = ValidationReport('attendance')
        df, err = _read_csv_safe(file_bytes)
        if err:
            report.add_error(0, 'file', '', err, 'Fix the file and re-upload.')
            return report

        df.columns = [c.lower().strip() for c in df.columns]
        col_err = _require_cols(df, ['student_code', 'class_date', 'status'])
        if col_err:
            report.add_error(0, 'columns', '', col_err, 'Add required columns.')
            return report

        report.total = len(df)
        valid_statuses = {'present', 'absent', 'late', 'excused'}
        seen_pairs = set()

        for row_idx, row in df.iterrows():
            rn = row_idx + 2
            code = str(row.get('student_code', '')).strip()
            cdate = str(row.get('class_date', '')).strip()
            status = str(row.get('status', '')).strip().lower()

            if not code or code.lower() == 'nan':
                report.add_error(rn, 'student_code', code, 'student_code required.', 'Provide a valid student code.')
                continue
            if not cdate or cdate.lower() == 'nan':
                report.add_error(rn, 'class_date', cdate, 'class_date required.', 'Provide date in YYYY-MM-DD format.')
                continue

            if valid_student_codes and code not in valid_student_codes:
                report.add_error(rn, 'student_code', code, f'student_code {code} not enrolled in this course.', 'Verify the student code against the enrollment list.')
                continue

            if valid_class_dates and cdate not in valid_class_dates:
                report.add_error(rn, 'class_date', cdate, f'class_date {cdate} does not exist for this course.', 'Verify the class date.')
                continue

            if status not in valid_statuses:
                report.add_error(rn, 'status', status, f'Invalid status "{status}". Must be: present, absent, late, excused.', f'Use one of: {", ".join(sorted(valid_statuses))}.')
                continue

            # Late is a WARNING — record still imports
            if status == 'late':
                report.add_warning(rn, 'status', status, 'Student marked late. Record will import with late flag.', 'No action required unless late policy violation.')

            pair = (code, cdate)
            if pair in seen_pairs:
                report.add_error(rn, 'student_code+class_date', pair, f'Duplicate attendance record for {code} on {cdate}.', 'Remove the duplicate row.')
                continue
            seen_pairs.add(pair)

        report.valid = report.total - report.rejected
        return report

    # ── Marks / Exam results ──────────────────────────────────────────────────
    @staticmethod
    def validate_marks(
        file_bytes: bytes,
        exam_definitions: dict[str, float] | None = None,
        valid_student_codes: set[str] | None = None,
    ) -> ValidationReport:
        """Required: student_code, exam_title, marks_obtained.
        exam_definitions: {exam_title: max_marks}"""
        report = ValidationReport('exam_marks')
        df, err = _read_csv_safe(file_bytes)
        if err:
            report.add_error(0, 'file', '', err, 'Fix and re-upload.')
            return report

        df.columns = [c.lower().strip() for c in df.columns]
        col_err = _require_cols(df, ['student_code', 'exam_title', 'marks_obtained'])
        if col_err:
            report.add_error(0, 'columns', '', col_err, 'Add required columns.')
            return report

        report.total = len(df)
        seen_pairs = set()

        for row_idx, row in df.iterrows():
            rn = row_idx + 2
            code = str(row.get('student_code', '')).strip()
            title = str(row.get('exam_title', '')).strip()
            marks_raw = row.get('marks_obtained')

            if not code or code.lower() == 'nan':
                report.add_error(rn, 'student_code', code, 'student_code required.', 'Provide a valid student code.')
                continue
            if not title or title.lower() == 'nan':
                report.add_error(rn, 'exam_title', title, 'exam_title required.', 'Provide the exam title.')
                continue
            if valid_student_codes and code not in valid_student_codes:
                report.add_error(rn, 'student_code', code, f'{code} not enrolled.', 'Verify student code.')
                continue

            # Marks validation
            if not _is_valid_number(marks_raw, 0):
                report.add_error(rn, 'marks_obtained', marks_raw, 'marks_obtained must be a non-negative number.', 'Enter a numeric value ≥ 0.')
                continue

            marks = float(marks_raw)
            if exam_definitions and title in exam_definitions:
                max_m = exam_definitions[title]
                if marks > max_m:
                    report.add_error(rn, 'marks_obtained', marks, f'Marks {marks} exceed maximum {max_m} for "{title}".', f'Correct to ≤ {max_m}.')
                    continue
            elif exam_definitions and title not in exam_definitions:
                report.add_error(rn, 'exam_title', title, f'Exam "{title}" not found in this course.', 'Use an exam title that exists in the course.')
                continue

            pair = (code, title)
            if pair in seen_pairs:
                report.add_error(rn, 'student_code+exam_title', pair, f'Duplicate mark for {code} in {title}.', 'Remove duplicate.')
                continue
            seen_pairs.add(pair)

        report.valid = report.total - report.rejected
        return report

    # ── Assignment submissions ─────────────────────────────────────────────────
    @staticmethod
    def validate_assignment_submissions(
        file_bytes: bytes,
        assignment_definitions: dict[str, float] | None = None,
        valid_student_codes: set[str] | None = None,
    ) -> ValidationReport:
        """Required: student_code, assignment_title, marks_obtained. Optional: submitted_at."""
        report = ValidationReport('assignment_submissions')
        df, err = _read_csv_safe(file_bytes)
        if err:
            report.add_error(0, 'file', '', err, 'Fix and re-upload.')
            return report

        df.columns = [c.lower().strip() for c in df.columns]
        col_err = _require_cols(df, ['student_code', 'assignment_title', 'marks_obtained'])
        if col_err:
            report.add_error(0, 'columns', '', col_err, 'Add required columns.')
            return report

        report.total = len(df)
        seen_pairs = set()

        for row_idx, row in df.iterrows():
            rn = row_idx + 2
            code = str(row.get('student_code', '')).strip()
            title = str(row.get('assignment_title', '')).strip()
            marks_raw = row.get('marks_obtained')
            submitted_at = row.get('submitted_at') if 'submitted_at' in df.columns else None
            due_date = row.get('due_date') if 'due_date' in df.columns else None

            if not code or code.lower() == 'nan':
                report.add_error(rn, 'student_code', code, 'student_code required.', 'Provide a valid student code.')
                continue
            if not title or title.lower() == 'nan':
                report.add_error(rn, 'assignment_title', title, 'assignment_title required.', 'Provide the assignment title.')
                continue
            if valid_student_codes and code not in valid_student_codes:
                report.add_error(rn, 'student_code', code, f'{code} not enrolled.', 'Verify student code.')
                continue
            if not _is_valid_number(marks_raw, 0):
                report.add_error(rn, 'marks_obtained', marks_raw, 'marks_obtained must be ≥ 0.', 'Enter a numeric value.')
                continue

            marks = float(marks_raw)
            if assignment_definitions and title in assignment_definitions:
                max_m = assignment_definitions[title]
                if marks > max_m:
                    report.add_error(rn, 'marks_obtained', marks, f'Marks {marks} exceed maximum {max_m}.', f'Correct to ≤ {max_m}.')
                    continue

            # Late submission: WARNING, not rejection
            if due_date and submitted_at and pd.notna(submitted_at) and pd.notna(due_date):
                try:
                    sub_dt = pd.to_datetime(submitted_at)
                    due_dt = pd.to_datetime(due_date)
                    if sub_dt > due_dt:
                        report.add_warning(rn, 'submitted_at', str(submitted_at),
                            f'Submitted after due date {due_date}. Will be flagged as late.',
                            'Review late submission policy. Record will import with is_late=True.')
                except Exception:
                    pass

            if submitted_at is None or (pd.isna(submitted_at) if hasattr(submitted_at, '__class__') and submitted_at.__class__.__name__ == 'float' else False):
                report.add_warning(rn, 'submitted_at', '', 'No submission timestamp. Record will import without submission date.', 'Add submitted_at if available.')

            pair = (code, title)
            if pair in seen_pairs:
                report.add_error(rn, 'student_code+assignment', pair, f'Duplicate submission for {code} / {title}.', 'Remove duplicate.')
                continue
            seen_pairs.add(pair)

        report.valid = report.total - report.rejected
        return report

    # ── Quiz results ──────────────────────────────────────────────────────────
    @staticmethod
    def validate_quiz_results(
        file_bytes: bytes,
        quiz_definitions: dict[str, float] | None = None,
        valid_student_codes: set[str] | None = None,
    ) -> ValidationReport:
        """Required: student_code, quiz_title, marks_obtained."""
        report = ValidationReport('quiz_results')
        df, err = _read_csv_safe(file_bytes)
        if err:
            report.add_error(0, 'file', '', err, 'Fix and re-upload.')
            return report

        df.columns = [c.lower().strip() for c in df.columns]
        col_err = _require_cols(df, ['student_code', 'quiz_title', 'marks_obtained'])
        if col_err:
            report.add_error(0, 'columns', '', col_err, 'Add required columns.')
            return report

        report.total = len(df)
        seen_pairs = set()

        for row_idx, row in df.iterrows():
            rn = row_idx + 2
            code = str(row.get('student_code', '')).strip()
            title = str(row.get('quiz_title', '')).strip()
            marks_raw = row.get('marks_obtained')

            if not code or code.lower() == 'nan':
                report.add_error(rn, 'student_code', code, 'student_code required.', 'Provide a valid student code.')
                continue
            if not title or title.lower() == 'nan':
                report.add_error(rn, 'quiz_title', title, 'quiz_title required.', 'Provide the quiz title.')
                continue
            if valid_student_codes and code not in valid_student_codes:
                report.add_error(rn, 'student_code', code, f'{code} not enrolled.', 'Verify student code.')
                continue
            if not _is_valid_number(marks_raw, 0):
                report.add_error(rn, 'marks_obtained', marks_raw, 'marks_obtained must be ≥ 0.', 'Enter a numeric value.')
                continue

            marks = float(marks_raw)
            if quiz_definitions and title in quiz_definitions:
                max_m = quiz_definitions[title]
                if marks > max_m:
                    report.add_error(rn, 'marks_obtained', marks, f'Marks {marks} exceed maximum {max_m}.', f'Correct to ≤ {max_m}.')
                    continue
            elif quiz_definitions and title not in quiz_definitions:
                report.add_error(rn, 'quiz_title', title, f'Quiz "{title}" not found in this course.', 'Use a quiz title that exists in the course.')
                continue

            pair = (code, title)
            if pair in seen_pairs:
                report.add_error(rn, 'student_code+quiz', pair, f'Duplicate result for {code} / {title}.', 'Remove duplicate.')
                continue
            seen_pairs.add(pair)

        report.valid = report.total - report.rejected
        return report

    # ── Question bank ─────────────────────────────────────────────────────────
    @staticmethod
    def validate_question_bank(
        file_bytes: bytes,
        valid_co_codes: set[str] | None = None,
        valid_unit_titles: set[str] | None = None,
    ) -> ValidationReport:
        """Required: question_text, question_type, difficulty."""
        report = ValidationReport('question_bank')
        df, err = _read_csv_safe(file_bytes)
        if err:
            report.add_error(0, 'file', '', err, 'Fix and re-upload.')
            return report

        df.columns = [c.lower().strip() for c in df.columns]
        col_err = _require_cols(df, ['question_text', 'question_type', 'difficulty'])
        if col_err:
            report.add_error(0, 'columns', '', col_err, 'Add required columns.')
            return report

        report.total = len(df)
        valid_types = {'mcq', 'short', 'long', 'coding'}
        valid_diffs = {'easy', 'medium', 'hard'}

        for row_idx, row in df.iterrows():
            rn = row_idx + 2
            qtext = str(row.get('question_text', '')).strip()
            qtype = str(row.get('question_type', '')).strip().lower()
            diff = str(row.get('difficulty', '')).strip().lower()
            co_code = str(row.get('co_code', '')).strip() if 'co_code' in df.columns else ''
            unit_title = str(row.get('unit_title', '')).strip() if 'unit_title' in df.columns else ''

            if not qtext or qtext.lower() == 'nan' or len(qtext) < 5:
                report.add_error(rn, 'question_text', qtext[:40], 'question_text is required and must be meaningful.', 'Provide a complete question.')
                continue
            if qtype not in valid_types:
                report.add_error(rn, 'question_type', qtype, f'Invalid type "{qtype}". Must be: MCQ, Short, Long, Coding.', 'Use one of the valid types.')
                continue
            if diff not in valid_diffs:
                report.add_error(rn, 'difficulty', diff, f'Invalid difficulty "{diff}". Must be: Easy, Medium, Hard.', 'Use one of the valid difficulty levels.')
                continue

            if co_code and co_code.lower() != 'nan' and valid_co_codes and co_code not in valid_co_codes:
                report.add_error(rn, 'co_code', co_code, f'CO code "{co_code}" not found in this course.', 'Use a CO code from the course (e.g. CO1).')
                continue

            if unit_title and unit_title.lower() != 'nan' and valid_unit_titles and unit_title not in valid_unit_titles:
                report.add_warning(rn, 'unit_title', unit_title, f'Unit "{unit_title}" not found. Question will import without unit link.', 'Verify the unit title.')

        report.valid = report.total - report.rejected
        return report

    # ── Student feedback ──────────────────────────────────────────────────────
    @staticmethod
    def validate_feedback(
        file_bytes: bytes,
        valid_student_codes: set[str] | None = None,
    ) -> ValidationReport:
        """Required: rating. Optional: student_code, comments, week_number."""
        report = ValidationReport('student_feedback')
        df, err = _read_csv_safe(file_bytes)
        if err:
            report.add_error(0, 'file', '', err, 'Fix and re-upload.')
            return report

        df.columns = [c.lower().strip() for c in df.columns]
        col_err = _require_cols(df, ['rating'])
        if col_err:
            report.add_error(0, 'columns', '', col_err, 'Add required columns.')
            return report

        report.total = len(df)

        for row_idx, row in df.iterrows():
            rn = row_idx + 2
            rating_raw = row.get('rating')
            if not _is_valid_number(rating_raw, 1, 5):
                report.add_error(rn, 'rating', rating_raw, 'Rating must be a number between 1 and 5.', 'Enter an integer 1–5.')
                continue

            # Student code optional (anonymous feedback permitted) — warning only if provided but not enrolled
            if 'student_code' in df.columns:
                code = str(row.get('student_code', '')).strip()
                if code and code.lower() != 'nan' and valid_student_codes and code not in valid_student_codes:
                    report.add_warning(rn, 'student_code', code, f'{code} not found in enrolled students.', 'Feedback will import anonymously.')

        report.valid = report.total - report.rejected
        return report
