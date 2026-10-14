#!/usr/bin/env python3
"""
app.py
What-If Database Web Application Server.
Provides the interactive web UI with an embedded on-screen terminal and live impact dashboard.

Connects to engine.py (or mock_engine.py for testing / offline demo).
"""

import sys
import os
import json
import argparse
import logging

# Determine directory paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(BASE_DIR, "web")

# A single contract boundary is shared by HTTP, Python CLI, and Bun CLI.
from time import perf_counter
from mock_engine import run_whatif as mock_run_whatif
try:
    from engine import run_whatif as live_run_whatif
except ModuleNotFoundError as exc:
    if exc.name not in {"psycopg", "sqlglot"}:
        raise
    live_run_whatif = None

ENGINE_SOURCE = "Automatic live engine / labeled offline fallback"


def error_report(sql, message, statement_type="UNKNOWN"):
    return {"statement": sql, "statement_type": statement_type, "status": "ERROR",
            "execution_time_ms": 0.0, "tables_affected": [], "metrics": [],
            "broken_dependencies": [], "logs": [message], "error_message": message,
            "engine_backend": "live", "rolled_back": False}


def normalize_report(sql, raw, elapsed_ms):
    """Translate counts and academic snapshots into the client contract."""
    report = {"statement": sql, "statement_type": "DML",
              "status": "SIMULATED" if raw.get("rolled_back") is True else "ERROR",
              "execution_time_ms": elapsed_ms, "tables_affected": [], "metrics": [],
              "broken_dependencies": [], "logs": [], "engine_backend": "live",
              "rolled_back": raw.get("rolled_back") is True}
    before, after = raw.get("before", {}), raw.get("after", {})
    target = raw.get("target_table")
    names = set(before) | set(after) | set(raw.get("tables_affected", []))
    # Older raw reports name only one target; do not count WHERE subquery tables as updates.
    if not target and len(raw.get("tables_affected", [])) == 1:
        target = raw["tables_affected"][0]
    operation = raw.get("operation", "").upper()
    for table in sorted(names):
        delta = after.get(table, 0) - before.get(table, 0)
        rows = raw.get("rows_affected", 0) if table == target else abs(delta)
        if table == target or delta:
            report["tables_affected"].append({"table": table, "rows_changed": max(0, rows),
                "action": {"DELETE": "DELETED", "UPDATE": "UPDATED", "INSERT": "INSERTED"}.get(operation, "CHANGED") if table == target else ("ON_DELETE_CASCADE" if delta < 0 else "INSERTED")})
    for group, fields in (("attendance", (("attendance_percentage", "attendance_percentage"), ("exam_eligible", "exam_eligibility"))),
                          ("performance", (("weighted_average_score", "weighted_average_score"),))):
        old = {(r["student_id"], r.get("course_code")): r for r in raw.get("academic_before", {}).get(group, [])}
        new = {(r["student_id"], r.get("course_code")): r for r in raw.get("academic_after", {}).get(group, [])}
        for key in sorted(old.keys() | new.keys()):
            for field, name in fields:
                b, a = old.get(key, {}).get(field), new.get(key, {}).get(field)
                if b == a:
                    continue
                def value(v):
                    if v is None:
                        return "UNAVAILABLE"
                    if name == "exam_eligibility":
                        return {"YES": "ELIGIBLE", "NO": "INELIGIBLE"}.get(v, v)
                    return float(v)
                b, a = value(b), value(a)
                item = {"metric": name, "student_id": key[0], "before": b, "after": a,
                        "change": round(a - b, 2) if isinstance(a, float) and isinstance(b, float) else "CHANGED"}
                if key[1]:
                    item["course_code"] = key[1]
                report["metrics"].append(item)
    report["logs"] = ["REPEATABLE READ snapshot; baseline and after counts captured.",
                      "Academic metrics reflect the delivered schema; weighted score is not CGPA."]
    if report["rolled_back"]:
        report["logs"].append("ROLLBACK acknowledged; transaction changes discarded.")
    else:
        report["error_message"] = "Rollback was not confirmed."
    return report


def offline_report(sql):
    report = mock_run_whatif(sql)
    report["engine_backend"] = "mock"
    report["rolled_back"] = False
    # Fixtures contain historical live-sounding logs. Do not expose those as evidence.
    report["logs"] = ["OFFLINE DEMO: PostgreSQL unavailable; showing illustrative fixture data.",
                      "No SQL executed. Values are examples, not measurements of your query."]
    return report


def run_whatif(sql):
    if not isinstance(sql, str) or not sql.strip():
        return error_report("", "Enter a SQL statement.", "REJECTED")
    started = perf_counter()
    if live_run_whatif is None:
        return offline_report(sql)
    try:
        raw = live_run_whatif(sql)
        return normalize_report(sql, raw, (perf_counter() - started) * 1000)
    except ConnectionError:
        return offline_report(sql)
    except ValueError as exc:
        report = error_report(sql, str(exc), "REJECTED")
    except Exception:
        # SQL/rollback failures must never turn into successful mock reports.
        logging.getLogger(__name__).exception("Live simulation failed")
        report = error_report(sql, "Live execution failed. Check schema compatibility and database server logs; rollback is not confirmed in this report.")
    report["execution_time_ms"] = (perf_counter() - started) * 1000
    return report


# Use bottle if available (available in standard Ubuntu / Python environment)
try:
    from bottle import Bottle, request, response, static_file, run
    USE_BOTTLE = True
except ImportError:
    USE_BOTTLE = False

def create_bottle_app():
    app = Bottle()

    @app.route("/")
    def index():
        return static_file("index.html", root=WEB_DIR)

    @app.route("/static/<filename:path>")
    def serve_static(filename):
        return static_file(filename, root=WEB_DIR)

    @app.route("/api/whatif", method=["POST", "OPTIONS"])
    def api_whatif():
        response.content_type = "application/json"
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"

        if request.method == "OPTIONS":
            return {}

        data = request.json
        sql = data.get("sql") if isinstance(data, dict) else None

        if not isinstance(sql, str) or not sql.strip():
            response.status = 400
            return error_report("", "A nonempty sql string is required.", "REJECTED")

        report = run_whatif(sql)
        return report

    @app.route("/api/scenarios", method="GET")
    def api_scenarios():
        response.content_type = "application/json"
        return {
            "scenarios": [
                {
                    "id": "1",
                    "title": "Attendance Deletion (Eligibility Flip)",
                    "sql": "WHAT_IF DELETE FROM attendance WHERE student_id = 1042;",
                    "description": "Attendance drops below 75%; exam eligibility flips to INELIGIBLE."
                },
                {
                    "id": "2",
                    "title": "Mark Update (CGPA Recalculation)",
                    "sql": "WHAT_IF UPDATE marks SET score = 45 WHERE student_id = 1042 AND course_id = 'CSE202';",
                    "description": "Calculates exact CGPA shift."
                },
                {
                    "id": "3",
                    "title": "Course Deregistration (Cascade)",
                    "sql": "WHAT_IF DELETE FROM enrollments WHERE student_id = 1042 AND course_id = 'CSE202';",
                    "description": "ON DELETE CASCADE removes attendance and marks automatically."
                },
                {
                    "id": "4",
                    "title": "Drop Column (Broken Schema)",
                    "sql": "WHAT_IF ALTER TABLE marks DROP COLUMN score;",
                    "description": "pg_depend & pg_rewrite report broken views and failing metrics."
                },
                {
                    "id": "5",
                    "title": "Safety Filter Rejection",
                    "sql": "WHAT_IF COMMIT;",
                    "description": "Rejects COMMIT and transaction escapements."
                },
                {
                    "id": "6",
                    "title": "Verify Pristine State",
                    "sql": "SELECT student_id, name, attendance_pct, cgpa, exam_eligible FROM student_summary_view WHERE student_id = 1042;",
                    "description": "Confirms live database remains unchanged."
                }
            ]
        }

    return app

def run_http_server(host: str, port: int):
    """Fallback standard library HTTP server if external frameworks are not present."""
    from http.server import HTTPServer, SimpleHTTPRequestHandler
    import urllib.parse

    class WhatIfHandler(SimpleHTTPRequestHandler):
        def translate_path(self, path):
            if path == "/" or path == "/index.html":
                return os.path.join(WEB_DIR, "index.html")
            if path.startswith("/static/"):
                rel = path[len("/static/"):]
                return os.path.join(WEB_DIR, rel)
            return super().translate_path(path)

        def do_POST(self):
            if self.path == "/api/whatif":
                content_len = int(self.headers.get("Content-Length", 0))
                post_body = self.rfile.read(content_len)
                try:
                    data = json.loads(post_body.decode("utf-8"))
                    sql = data.get("sql") if isinstance(data, dict) else None
                    report = run_whatif(sql)
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps(report).encode("utf-8"))
                except Exception as ex:
                    self.send_response(500)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": str(ex)}).encode("utf-8"))
            else:
                self.send_response(404)
                self.end_headers()

    server = HTTPServer((host, port), WhatIfHandler)
    print(f"🚀 What-If Database UI running at http://{host}:{port}/ (standard http.server)")
    print(f"🔗 Engine backend: {ENGINE_SOURCE}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")

def main():
    parser = argparse.ArgumentParser(description="What-If Database Web Interface Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on (default: 8000)")
    args = parser.parse_args()

    print("=" * 60)
    print("  WHAT-IF DATABASE: IMPACT ANALYSIS INTERFACE")
    print(f"  Backend: {ENGINE_SOURCE}")
    print(f"  URL:     http://{args.host}:{args.port}")
    print("=" * 60)

    if USE_BOTTLE:
        app = create_bottle_app()
        run(app, host=args.host, port=args.port, quiet=False)
    else:
        run_http_server(args.host, args.port)

if __name__ == "__main__":
    main()
