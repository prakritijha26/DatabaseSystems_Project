#!/usr/bin/env python3
"""
demo.py
Automated evaluation runner for the 6 core review scenarios.
Part C Deliverable: Scripted demonstration of What-If Database for examiner/viva presentation.

Usage:
  python3 demo.py
  python3 demo.py --interactive   # Pause and wait for [Enter] between scenarios
"""

import sys
import time
import argparse
from cli import format_impact_report, Colors, BACKEND_NAME

from app import run_whatif
BACKEND_NAME = "Automatic live / labeled offline fallback"

DEMO_SCENARIOS = [
    {
        "number": 1,
        "title": "Attendance Deletion causing Eligibility Flip",
        "description": "Simulates deleting 14 attendance records for student 1042. Recomputed attendance falls below VIT's 75% threshold, flipping exam status from ELIGIBLE to INELIGIBLE.",
        "sql": "WHAT_IF DELETE FROM attendance WHERE student_id = 1042;"
    },
    {
        "number": 2,
        "title": "Mark Update causing CGPA Recalculation",
        "description": "Simulates adjusting student 1042's CSE202 score. The credit-weighted CGPA view re-evaluates inside snapshot isolation and reports the exact numerical delta.",
        "sql": "WHAT_IF UPDATE marks SET score = 45 WHERE student_id = 1042 AND course_id = 'CSE202';"
    },
    {
        "number": 3,
        "title": "Course Deregistration with Cascades (ON DELETE CASCADE)",
        "description": "Simulates removing a student from a course enrollment. Foreign key cascades automatically delete linked marks and attendance entries in the transaction snapshot.",
        "sql": "WHAT_IF DELETE FROM enrollments WHERE student_id = 1042 AND course_id = 'CSE202';"
    },
    {
        "number": 4,
        "title": "Hypothetical DDL with Schema Catalog Tracing (DROP COLUMN)",
        "description": "Simulates dropping column 'score' from table 'marks'. Queries pg_depend and pg_rewrite to list the broken views, triggers, and failing metric queries.",
        "sql": "WHAT_IF ALTER TABLE marks DROP COLUMN score;"
    },
    {
        "number": 5,
        "title": "Sandbox Security Violation (Attempted COMMIT Injection)",
        "description": "Simulates an adversarial attempt to commit a transaction or escape the sandbox. The AST validator intercepts and rejects the statement before snapshot acquisition.",
        "sql": "WHAT_IF COMMIT;"
    },
    {
        "number": 6,
        "title": "Post-Simulation Immutability Verification (Plain SELECT)",
        "description": "Shows the verification fixture offline; the current live DML engine rejects SELECT.",
        "sql": "SELECT student_id, name, attendance_pct, cgpa, exam_eligible FROM student_summary_view WHERE student_id = 1042;"
    }
]

def run_demo(interactive: bool = False):
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 76}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.CYAN}   WHAT-IF DATABASE: AUTOMATED DEMO & EVALUATION SUITE{Colors.ENDC}")
    print(f"{Colors.CYAN}   Course: BACSE202 (DBMS) | Snapshot Isolation: REPEATABLE READ{Colors.ENDC}")
    print(f"{Colors.CYAN}   Backend: {BACKEND_NAME}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 76}{Colors.ENDC}\n")

    for sc in DEMO_SCENARIOS:
        print(f"\n{Colors.BOLD}{Colors.HEADER}============================================================================{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.HEADER} [SCENARIO {sc['number']}/6] {sc['title'].upper()}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.HEADER}============================================================================{Colors.ENDC}")
        print(f"{Colors.BOLD}Scenario Goal:{Colors.ENDC} {sc['description']}")
        print(f"{Colors.BOLD}Input Query:{Colors.ENDC}   {Colors.CYAN}{sc['sql']}{Colors.ENDC}")

        if interactive:
            input(f"\n{Colors.DIM}Press [Enter] to simulate this scenario...{Colors.ENDC}")
        else:
            time.sleep(0.3)

        report = run_whatif(sc["sql"])
        format_impact_report(report)

    print(f"\n{Colors.BOLD}{Colors.GREEN}{'=' * 76}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.GREEN}   ✅ DEMO RUN COMPLETE — REVIEW THE SIX REPORTS.{Colors.ENDC}")
    print(f"{Colors.GREEN}   Review each report for backend mode, errors, and rollback confirmation.{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.GREEN}{'=' * 76}{Colors.ENDC}\n")

def main():
    parser = argparse.ArgumentParser(description="What-If Database Demo Runner")
    parser.add_argument("--interactive", action="store_true", help="Pause for Enter key between scenarios")
    args = parser.parse_args()
    run_demo(interactive=args.interactive)

if __name__ == "__main__":
    main()
