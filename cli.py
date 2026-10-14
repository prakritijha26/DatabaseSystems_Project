#!/usr/bin/env python3
"""
cli.py
What-If Database Interactive Command Line Interface.
Part C Deliverable: formatted terminal interface and scenario executor.

Usage:
  python3 cli.py
  python3 cli.py "WHAT_IF DELETE FROM attendance WHERE student_id = 1042;"
  python3 cli.py --json "WHAT_IF UPDATE marks SET score = 45 WHERE student_id = 1042;"
  python3 cli.py --file demo.sql
"""

import sys
import os
import json
import argparse
from typing import Dict, Any

# Import simulation engine
from app import run_whatif
BACKEND_NAME = "Automatic live / labeled offline fallback"

# Lospec Revival Palette (24-bit Truecolor ANSI)
class Colors:
    CREAM = "\033[38;2;247;247;234m"    # #f7f7ea (Parchment text)
    DENIM = "\033[38;2;71;118;195m"     # #4776c3 (Vintage denim blue)
    CYAN = "\033[38;2;47;201;237m"      # #2fc9ed (Diner turquoise)
    MINT = "\033[38;2;170;239;213m"     # #aaefd5 (Pastel mint / success)
    YELLOW = "\033[38;2;245;226;145m"   # #f5e291 (Vintage butter yellow)
    ROSE = "\033[38;2;242;156;172m"     # #f29cac (Retro pastel rose)
    RED = "\033[38;2;245;85;74m"        # #f5554a (Vintage crimson red)
    AUBERGINE = "\033[38;2;45;33;68m"   # #2d2144 (Deep plum background)

    HEADER = ROSE
    BLUE = DENIM
    GREEN = MINT
    WARNING = YELLOW
    FAIL = RED
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    DIM = "\033[38;2;165;155;185m"

def print_banner():
    banner = f"""
{Colors.CYAN}{Colors.BOLD}======================================================================
  WHAT-IF DATABASE: IMPACT ANALYSIS FOR UNIVERSITY DATABASES
  BACSE202 DBMS Project | Snapshot Sandbox (REPEATABLE READ)
  Backend: {BACKEND_NAME}
======================================================================{Colors.ENDC}
"""
    print(banner)

def format_impact_report(report: Dict[str, Any], show_json: bool = False):
    """Formats and prints an ImpactReport in clean terminal tables."""
    if show_json:
        print(json.dumps(report, indent=2))
        return

    stmt = report.get("statement", "")
    stmt_type = report.get("statement_type", "UNKNOWN")
    status = report.get("status", "UNKNOWN")
    exec_time = report.get("execution_time_ms", 0.0)

    # 1. Header Box
    print(f"\n{Colors.BOLD}┌── SIMULATION IMPACT REPORT ──────────────────────────────────────────{Colors.ENDC}")
    print(f"│ {Colors.BOLD}Statement:{Colors.ENDC}       {stmt}")
    print(f"│ {Colors.BOLD}Type:{Colors.ENDC}            {stmt_type}")
    
    if status == "ERROR":
        print(f"│ {Colors.BOLD}Status:{Colors.ENDC}          {Colors.FAIL}{Colors.BOLD}REJECTED (SAFETY FILTER){Colors.ENDC}")
        print(f"│ {Colors.BOLD}Error:{Colors.ENDC}           {Colors.FAIL}{report.get('error_message', 'Validation error')}{Colors.ENDC}")
    elif status == "VERIFIED_PRISTINE":
        print(f"│ {Colors.BOLD}Status:{Colors.ENDC}          {Colors.GREEN}{Colors.BOLD}VERIFIED PRISTINE{Colors.ENDC}")
    else:
        print(f"│ {Colors.BOLD}Status:{Colors.ENDC}          {Colors.GREEN}{Colors.BOLD}SIMULATED (SNAPSHOT ISOLATION){Colors.ENDC}")
    
    print(f"│ {Colors.BOLD}Simulation Time:{Colors.ENDC} {exec_time:.2f} ms")
    print(f"└──{'─' * 70}")

    # 2. Execution Logs
    logs = report.get("logs", [])
    if logs:
        print(f"\n{Colors.DIM}Execution Trace:{Colors.ENDC}")
        for log in logs:
            if "ERROR" in log or "❌" in log:
                print(f"  {Colors.FAIL}{log}{Colors.ENDC}")
            elif "ROLLBACK" in log:
                print(f"  {Colors.HEADER}{log}{Colors.ENDC}")
            elif "✅" in log:
                print(f"  {Colors.GREEN}{log}{Colors.ENDC}")
            else:
                print(f"  {Colors.DIM}{log}{Colors.ENDC}")

    # If rejected, stop here
    if status == "ERROR":
        return

    # 3. Tables & Rows Affected
    tables = report.get("tables_affected", [])
    print(f"\n{Colors.BOLD}📁 Tables Affected:{Colors.ENDC}")
    if not tables:
        print(f"  {Colors.DIM}(No physical tables modified; 0 rows changed){Colors.ENDC}")
    else:
        print(f"  {Colors.BOLD}{'Table':<20} {'Action':<22} {'Rows Changed':<12}{Colors.ENDC}")
        print(f"  {'-'*20} {'-'*22} {'-'*12}")
        for t in tables:
            tbl_name = t.get("table", "")
            action = t.get("action", "MODIFIED")
            rows = t.get("rows_changed", 0)
            act_color = Colors.CYAN
            if "CASCADE" in action:
                act_color = Colors.HEADER
            elif "DELETED" in action:
                act_color = Colors.FAIL
            print(f"  {tbl_name:<20} {act_color}{action:<22}{Colors.ENDC} {rows:<12}")

    # 4. Metrics Table
    metrics = report.get("metrics", [])
    if metrics:
        print(f"\n{Colors.BOLD}📊 Derived Academic Metrics:{Colors.ENDC}")
        print(f"  {Colors.BOLD}{'Metric':<25} {'Student':<12} {'Baseline':<12} {'Hypothetical':<14} {'Delta':<16}{Colors.ENDC}")
        print(f"  {'-'*25} {'-'*12} {'-'*12} {'-'*14} {'-'*16}")
        for m in metrics:
            m_name = m.get("metric", "")
            sid = str(m.get("student_id", "—"))
            unit = m.get("unit", "")
            
            # Format numbers or strings
            before = f"{m.get('before')}{unit}" if m.get("before") is not None else "—"
            after = f"{m.get('after')}{unit}" if m.get("after") is not None else "—"
            change = m.get("change")

            if isinstance(change, (int, float)):
                c_str = f"{change:+.2f}{unit}" if isinstance(change, float) else f"{change:+d}{unit}"
                c_color = Colors.GREEN if change > 0 else (Colors.FAIL if change < 0 else Colors.DIM)
            elif change == "FLIPPED_TO_NO":
                c_str = "FLIPPED TO NO ⚠️"
                c_color = f"{Colors.FAIL}{Colors.BOLD}"
            else:
                c_str = str(change) if change else "NO_CHANGE"
                c_color = Colors.DIM

            print(f"  {m_name:<25} {sid:<12} {before:<12} {after:<14} {c_color}{c_str:<16}{Colors.ENDC}")

    # 5. Schema Dependencies (DDL)
    broken = report.get("broken_dependencies", [])
    if broken:
        print(f"\n{Colors.WARNING}{Colors.BOLD}⚠️  Schema Dependencies Broken (Catalog Tracing):{Colors.ENDC}")
        print(f"  {Colors.BOLD}{'Object Name':<28} {'Type':<16} {'Reason / Impact':<35}{Colors.ENDC}")
        print(f"  {'-'*28} {'-'*16} {'-'*35}")
        for b in broken:
            name = b.get("object_name", "")
            b_type = b.get("object_type", "")
            reason = b.get("reason", "")
            print(f"  {Colors.FAIL}{name:<28}{Colors.ENDC} {b_type:<16} {Colors.DIM}{reason:<35}{Colors.ENDC}")

    # 6. Integrity Note
    message = ("Offline fixture: no SQL executed." if report.get("engine_backend") == "mock" else
               "Transaction rollback confirmed." if report.get("rolled_back") else "Rollback not confirmed.")
    print(f"\n{Colors.GREEN}Interlock:{Colors.ENDC} {message}")

def repl():
    """Interactive command-line loop."""
    print_banner()
    print("Type a WHAT_IF statement or SQL query (or 'help', 'scenarios', 'exit'):\n")

    while True:
        try:
            line = input(f"{Colors.GREEN}{Colors.BOLD}whatif>{Colors.ENDC} ").strip()
            if not line:
                continue
            if line.lower() in ("exit", "quit", "\\q"):
                print("Exiting What-If Database shell. Goodbye!")
                break
            if line.lower() == "help":
                print("\nAvailable commands:")
                print("  WHAT_IF DELETE FROM attendance WHERE student_id = 1042;")
                print("  WHAT_IF UPDATE marks SET score = 45 WHERE student_id = 1042 AND course_id = 'CSE202';")
                print("  WHAT_IF DELETE FROM enrollments WHERE student_id = 1042 AND course_id = 'CSE202';")
                print("  WHAT_IF ALTER TABLE marks DROP COLUMN score;")
                print("  scenarios  - List all 6 scripted review scenarios")
                print("  exit       - Exit shell\n")
                continue
            if line.lower() == "scenarios":
                print("\n--- 6 EVALUATION SCENARIOS ---")
                print("1. WHAT_IF DELETE FROM attendance WHERE student_id = 1042;")
                print("2. WHAT_IF UPDATE marks SET score = 45 WHERE student_id = 1042 AND course_id = 'CSE202';")
                print("3. WHAT_IF DELETE FROM enrollments WHERE student_id = 1042 AND course_id = 'CSE202';")
                print("4. WHAT_IF ALTER TABLE marks DROP COLUMN score;")
                print("5. WHAT_IF COMMIT;")
                print("6. SELECT student_id, name, attendance_pct, cgpa, exam_eligible FROM student_summary_view WHERE student_id = 1042;\n")
                continue

            report = run_whatif(line)
            format_impact_report(report)
            print()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            break

def main():
    parser = argparse.ArgumentParser(description="What-If Database CLI")
    parser.add_argument("sql", nargs="?", help="SQL statement to evaluate")
    parser.add_argument("--json", action="store_true", help="Print output as raw JSON")
    parser.add_argument("--file", help="Path to SQL file with statements to evaluate")
    args = parser.parse_args()

    if args.file:
        if not os.path.exists(args.file):
            print(f"Error: file '{args.file}' not found.")
            sys.exit(1)
        with open(args.file, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("--"):
                    print(f"\n{Colors.BOLD}>>> Running: {line}{Colors.ENDC}")
                    report = run_whatif(line)
                    format_impact_report(report, show_json=args.json)
        return

    if args.sql:
        report = run_whatif(args.sql)
        format_impact_report(report, show_json=args.json)
    else:
        repl()

if __name__ == "__main__":
    main()
