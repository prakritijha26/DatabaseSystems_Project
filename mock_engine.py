"""
mock_engine.py
Mock engine providing the agreed ImpactReport interface contract for Part C (Interface & Demo).
This enables building, testing, and presenting the UI & CLI while the underlying PostgreSQL engine
is being integrated.
"""

import time
import re
from typing import Dict, Any, List

SCENARIO_1_SQL = "WHAT_IF DELETE FROM attendance WHERE student_id = 1042;"
SCENARIO_2_SQL = "WHAT_IF UPDATE marks SET score = 45 WHERE student_id = 1042 AND course_id = 'CSE202';"
SCENARIO_3_SQL = "WHAT_IF DELETE FROM enrollments WHERE student_id = 1042 AND course_id = 'CSE202';"
SCENARIO_4_SQL = "WHAT_IF ALTER TABLE marks DROP COLUMN score;"
SCENARIO_5_SQL = "WHAT_IF COMMIT;"
SCENARIO_6_SQL = "SELECT student_id, name, attendance_pct, cgpa, exam_eligible FROM student_summary_view WHERE student_id = 1042;"

def run_whatif(sql: str) -> Dict[str, Any]:
    """
    Executes a WHAT_IF statement or plain verification query and returns an ImpactReport dictionary.
    Contract matches README.md and Project Plan specifications.
    """
    sql_clean = sql.strip().rstrip(";") + ";"
    sql_upper = sql_clean.upper()

    # Reject forbidden control commands or multi-statements
    if "COMMIT" in sql_upper or "ROLLBACK" in sql_upper and not sql_upper.startswith("WHAT_IF"):
        return {
            "statement": sql,
            "statement_type": "REJECTED",
            "status": "ERROR",
            "error_message": "Safety violation: Transaction control statements (COMMIT / ROLLBACK) are strictly prohibited inside WHAT_IF.",
            "tables_affected": [],
            "metrics": [],
            "broken_dependencies": [],
            "logs": [
                "[1/6] [PARSE] Validating statement syntax and safety rules...",
                "[ERROR] Statement validation failed: explicit transaction control prohibited."
            ],
            "execution_time_ms": 1.2
        }

    # Check for multi-statement injection
    statements = [s.strip() for s in sql.split(";") if s.strip()]
    if len(statements) > 1:
        return {
            "statement": sql,
            "statement_type": "REJECTED",
            "status": "ERROR",
            "error_message": "Safety violation: Multi-statement execution is disabled to prevent transaction escapes.",
            "tables_affected": [],
            "metrics": [],
            "broken_dependencies": [],
            "logs": [
                "[1/6] [PARSE] Validating statement syntax and safety rules...",
                "[ERROR] Multiple statements detected. Only a single atomic WHAT_IF command is permitted."
            ],
            "execution_time_ms": 1.4
        }

    # Scenario 5: WHAT_IF COMMIT;
    if "COMMIT" in sql_upper:
        return {
            "statement": sql,
            "statement_type": "REJECTED",
            "status": "ERROR",
            "error_message": "Safety violation: Cannot execute 'COMMIT' inside hypothetical simulation sandbox.",
            "tables_affected": [],
            "metrics": [],
            "broken_dependencies": [],
            "logs": [
                "[1/6] [PARSE] Checking statement against whitelist...",
                "[1/6] [REJECT] AST validation failed: statement 'COMMIT' violates sandbox safety policy.",
                "[ABORT] Execution halted before transaction acquisition."
            ],
            "execution_time_ms": 1.1
        }

    # Scenario 6: Plain SELECT query (Verification)
    if sql_upper.startswith("SELECT"):
        return {
            "statement": sql,
            "statement_type": "VERIFICATION_SELECT",
            "status": "VERIFIED_PRISTINE",
            "tables_affected": [],
            "metrics": [
                {
                    "metric": "live_data_state",
                    "student_id": 1042,
                    "student_name": "Aarav Sharma",
                    "current_attendance_pct": 82.5,
                    "current_cgpa": 8.74,
                    "exam_eligibility": "ELIGIBLE",
                    "status": "UNCHANGED"
                }
            ],
            "broken_dependencies": [],
            "logs": [
                "[1/2] [VERIFY] Executing direct SELECT query against live PostgreSQL tables...",
                "[2/2] [CONFIRM] Verification complete: Live tables and views remain in original pristine state.",
                "[STATUS] Zero persistent mutations recorded."
            ],
            "execution_time_ms": 3.8
        }

    # Scenario 4: Schema Change (DROP COLUMN)
    if "DROP COLUMN" in sql_upper or "ALTER TABLE" in sql_upper:
        return {
            "statement": sql,
            "statement_type": "DDL_SCHEMA_CHANGE",
            "status": "SIMULATED",
            "tables_affected": [
                {"table": "marks", "rows_changed": 0, "action": "COLUMN_DROPPED (hypothetical)"}
            ],
            "metrics": [],
            "broken_dependencies": [
                {
                    "object_name": "student_cgpa_view",
                    "object_type": "VIEW",
                    "reason": "Direct reference to dropped column 'score' in weighted GPA calculation.",
                    "severity": "CRITICAL_BREAK"
                },
                {
                    "object_name": "course_grade_summary_view",
                    "object_type": "VIEW",
                    "reason": "Aggregates 'score' column for grade distributions.",
                    "severity": "CRITICAL_BREAK"
                },
                {
                    "object_name": "check_score_bounds_trg",
                    "object_type": "TRIGGER",
                    "reason": "Validation trigger operates on NEW.score.",
                    "severity": "TRIGGER_INVALIDATED"
                },
                {
                    "object_name": "cgpa_metric_query",
                    "object_type": "METRIC_QUERY",
                    "reason": "Metric query depends on student_cgpa_view.",
                    "severity": "EXECUTION_FAILURE"
                }
            ],
            "logs": [
                "[1/6] [PARSE] Stripped WHAT_IF prefix; AST validated as permitted DDL (DROP COLUMN).",
                "[2/6] [CATALOG] Tracing reverse dependencies in pg_depend and pg_rewrite...",
                "[3/6] [SNAPSHOT] BEGIN ISOLATION LEVEL REPEATABLE READ.",
                "[4/6] [EXECUTE] Simulated schema modification inside snapshot transaction.",
                "[5/6] [CATALOG] Catalog scan identified 2 broken views, 1 broken trigger, 1 failing metric query.",
                "[6/6] [ROLLBACK] Issued ROLLBACK — physical catalogs and table definitions remain intact."
            ],
            "execution_time_ms": 11.4
        }

    # Scenario 1: Attendance Drop (Eligibility flips)
    if "DELETE FROM ATTENDANCE" in sql_upper:
        student_id = 1042
        m = re.search(r"student_id\s*=\s*(\d+)", sql, re.IGNORECASE)
        if m:
            student_id = int(m.group(1))

        return {
            "statement": sql,
            "statement_type": "DML",
            "status": "SIMULATED",
            "tables_affected": [
                {"table": "attendance", "rows_changed": 14, "action": "DELETED"}
            ],
            "metrics": [
                {
                    "metric": "attendance_percentage",
                    "student_id": student_id,
                    "student_name": "Aarav Sharma",
                    "course_code": "CSE202 (Database Systems)",
                    "before": 82.5,
                    "after": 61.2,
                    "change": -21.3,
                    "threshold": 75.0,
                    "unit": "%"
                },
                {
                    "metric": "exam_eligibility",
                    "student_id": student_id,
                    "student_name": "Aarav Sharma",
                    "course_code": "CSE202 (Database Systems)",
                    "before": "ELIGIBLE",
                    "after": "INELIGIBLE",
                    "change": "FLIPPED_TO_NO",
                    "reason": "Simulated attendance (61.2%) dropped below the mandatory 75% threshold."
                },
                {
                    "metric": "cgpa",
                    "student_id": student_id,
                    "student_name": "Aarav Sharma",
                    "before": 8.74,
                    "after": 8.74,
                    "change": 0.0,
                    "unit": "GPA"
                }
            ],
            "broken_dependencies": [],
            "logs": [
                "[1/6] [PARSE] Stripped WHAT_IF prefix; AST validated as DML (DELETE).",
                "[2/6] [BASELINE] Baseline metrics captured: Attendance = 82.5%, Exam Eligibility = ELIGIBLE.",
                "[3/6] [SNAPSHOT] BEGIN ISOLATION LEVEL REPEATABLE READ.",
                "[4/6] [EXECUTE] Executed hypothetical DELETE on table 'attendance' (14 rows affected).",
                "[5/6] [SAVEPOINTS] Recomputed metrics in isolated savepoints: Attendance = 61.2% (< 75%).",
                "[6/6] [ROLLBACK] Issued ROLLBACK — persistent rows modified: 0."
            ],
            "execution_time_ms": 8.6
        }

    # Scenario 2: Mark Update (CGPA changes)
    if "UPDATE MARKS" in sql_upper:
        student_id = 1042
        m = re.search(r"student_id\s*=\s*(\d+)", sql, re.IGNORECASE)
        if m:
            student_id = int(m.group(1))

        return {
            "statement": sql,
            "statement_type": "DML",
            "status": "SIMULATED",
            "tables_affected": [
                {"table": "marks", "rows_changed": 1, "action": "UPDATED"}
            ],
            "metrics": [
                {
                    "metric": "cgpa",
                    "student_id": student_id,
                    "student_name": "Aarav Sharma",
                    "before": 8.74,
                    "after": 8.18,
                    "change": -0.56,
                    "unit": "GPA"
                },
                {
                    "metric": "attendance_percentage",
                    "student_id": student_id,
                    "student_name": "Aarav Sharma",
                    "before": 82.5,
                    "after": 82.5,
                    "change": 0.0,
                    "unit": "%"
                },
                {
                    "metric": "exam_eligibility",
                    "student_id": student_id,
                    "student_name": "Aarav Sharma",
                    "before": "ELIGIBLE",
                    "after": "ELIGIBLE",
                    "change": "NO_CHANGE"
                }
            ],
            "broken_dependencies": [],
            "logs": [
                "[1/6] [PARSE] Stripped WHAT_IF prefix; AST validated as DML (UPDATE).",
                "[2/6] [BASELINE] Baseline metrics captured: CGPA = 8.74.",
                "[3/6] [SNAPSHOT] BEGIN ISOLATION LEVEL REPEATABLE READ.",
                "[4/6] [EXECUTE] Simulated UPDATE on table 'marks' (score adjusted). Trigger validation passed.",
                "[5/6] [SAVEPOINTS] Recomputed credit-weighted CGPA: 8.74 -> 8.18 (delta -0.56).",
                "[6/6] [ROLLBACK] Issued ROLLBACK — persistent records untouched."
            ],
            "execution_time_ms": 7.9
        }

    # Scenario 3: Course Deregistration Cascade
    if "DELETE FROM ENROLLMENTS" in sql_upper:
        student_id = 1042
        m = re.search(r"student_id\s*=\s*(\d+)", sql, re.IGNORECASE)
        if m:
            student_id = int(m.group(1))

        return {
            "statement": sql,
            "statement_type": "DML",
            "status": "SIMULATED",
            "tables_affected": [
                {"table": "enrollments", "rows_changed": 1, "action": "PRIMARY_DELETE"},
                {"table": "attendance", "rows_changed": 26, "action": "ON_DELETE_CASCADE"},
                {"table": "marks", "rows_changed": 3, "action": "ON_DELETE_CASCADE"}
            ],
            "metrics": [
                {
                    "metric": "cgpa",
                    "student_id": student_id,
                    "student_name": "Aarav Sharma",
                    "before": 8.74,
                    "after": 8.90,
                    "change": 0.16,
                    "reason": "Dropped 4-credit course; remaining credit-weighted average recalculated.",
                    "unit": "GPA"
                },
                {
                    "metric": "enrolled_courses_count",
                    "student_id": student_id,
                    "before": 5,
                    "after": 4,
                    "change": -1,
                    "unit": "Courses"
                }
            ],
            "broken_dependencies": [],
            "logs": [
                "[1/6] [PARSE] Stripped WHAT_IF prefix; AST validated as DML (DELETE).",
                "[2/6] [BASELINE] Baseline metrics captured across enrolled courses.",
                "[3/6] [SNAPSHOT] BEGIN ISOLATION LEVEL REPEATABLE READ.",
                "[4/6] [CASCADE] Foreign keys executed ON DELETE CASCADE into attendance (26 rows) and marks (3 rows).",
                "[5/6] [SAVEPOINTS] Recomputed academic metrics: CGPA shifted from 8.74 to 8.90.",
                "[6/6] [ROLLBACK] Issued ROLLBACK — all cascaded deletions cleanly reverted."
            ],
            "execution_time_ms": 9.8
        }

    # Generic Fallback Simulation for arbitrary WHAT_IF queries
    return {
        "statement": sql,
        "statement_type": "DML",
        "status": "SIMULATED",
        "tables_affected": [
            {"table": "simulated_target", "rows_changed": 2, "action": "MODIFIED"}
        ],
        "metrics": [
            {
                "metric": "attendance_percentage",
                "student_id": 1042,
                "student_name": "Aarav Sharma",
                "before": 82.5,
                "after": 76.0,
                "change": -6.5,
                "unit": "%"
            },
            {
                "metric": "cgpa",
                "student_id": 1042,
                "student_name": "Aarav Sharma",
                "before": 8.74,
                "after": 8.65,
                "change": -0.09,
                "unit": "GPA"
            },
            {
                "metric": "exam_eligibility",
                "student_id": 1042,
                "student_name": "Aarav Sharma",
                "before": "ELIGIBLE",
                "after": "ELIGIBLE",
                "change": "NO_CHANGE"
            }
        ],
        "broken_dependencies": [],
        "logs": [
            f"[1/6] [PARSE] Parsed query: '{sql_clean}'",
            "[2/6] [BASELINE] Baseline metrics captured.",
            "[3/6] [SNAPSHOT] BEGIN ISOLATION LEVEL REPEATABLE READ.",
            "[4/6] [EXECUTE] Simulation evaluated in snapshot transaction.",
            "[5/6] [SAVEPOINTS] Savepoint metric re-evaluations complete.",
            "[6/6] [ROLLBACK] Issued ROLLBACK — persistent storage intact."
        ],
        "execution_time_ms": 6.5
    }
