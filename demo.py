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

import json
import os
from pathlib import Path
DEMO_SCENARIOS = json.loads(Path(__file__).with_name('scenarios.json').read_text())

def run_demo(interactive: bool = False):
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 76}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.CYAN}   WHAT-IF DATABASE: AUTOMATED DEMO & EVALUATION SUITE{Colors.ENDC}")
    print(f"{Colors.CYAN}   Course: BACSE202 (DBMS) | Snapshot Isolation: REPEATABLE READ{Colors.ENDC}")
    print(f"{Colors.CYAN}   Backend: {BACKEND_NAME}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 76}{Colors.ENDC}\n")

    failures = 0
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
        if (report["status"] != "ERROR" if sc["number"] == 5 else report["status"] == "ERROR") or (os.getenv("WHATIF_REQUIRE_LIVE") == "1" and report.get("engine_backend") != "live"):
            failures += 1

    if failures:
        raise RuntimeError(f"{failures} review scenarios failed expectations.")
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
