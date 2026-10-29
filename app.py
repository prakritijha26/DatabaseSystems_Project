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
    report = {"statement": sql, "statement_type": raw.get("statement_type", "DML"),
              "status": "SIMULATED" if raw.get("rolled_back") is True else "ERROR",
              "execution_time_ms": elapsed_ms, "tables_affected": [], "metrics": [],
              "broken_dependencies": raw.get("broken_dependencies", []), "logs": [], "engine_backend": "live",
              "rolled_back": raw.get("rolled_back") is True}
    report["committed"] = raw.get("committed") is True
    if report["committed"]:
        report.update(status="COMMITTED", rolled_back=False, commit_scope="postgresql",
                      interlock_message="Permanent write confirmed. Transaction committed to PostgreSQL.")
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
                "action": {"DELETE": "DELETED", "UPDATE": "UPDATED", "INSERT": "INSERTED", "DROP_TABLE": "TABLE_DROPPED" if report["committed"] else "TABLE_DROPPED (hypothetical)", "DROP_COLUMN": "COLUMN_DROPPED" if report["committed"] else "COLUMN_DROPPED (hypothetical)"}.get(operation, "CHANGED") if table == target else ("ON_DELETE_CASCADE" if delta < 0 else "INSERTED")})
    for group, fields in (("attendance", (("attendance_percentage", "attendance_percentage"), ("exam_eligible", "exam_eligibility"))),
                          ("performance", (("weighted_average_score", "weighted_average_score"), ("weighted_gpa", "weighted_gpa")))):
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
    report["logs"] = raw.get("logs", [])
    for key in ("ddl_mode", "query_columns", "query_rows", "query_truncated", "message"):
        if key in raw:
            report[key] = raw[key]
    if report["rolled_back"] and report["statement_type"] == "VERIFICATION_SELECT":
        report["status"] = "VERIFIED_PRISTINE"
    if not report["rolled_back"] and not report["committed"]:
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
        return error_report(sql, "Live engine dependencies unavailable.") if os.getenv("WHATIF_REQUIRE_LIVE") == "1" else offline_report(sql)
    try:
        raw = live_run_whatif(sql)
        return normalize_report(sql, raw, (perf_counter() - started) * 1000)
    except ConnectionError:
        return error_report(sql, "PostgreSQL unavailable; live mode forbids mock fallback.") if os.getenv("WHATIF_REQUIRE_LIVE") == "1" else offline_report(sql)
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
        response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"

        origin = request.headers.get("Origin")
        if origin and origin != f"{request.urlparts.scheme}://{request.headers.get('Host')}":
            response.status = 403
            return error_report("", "Cross-origin SQL execution is not allowed.", "REJECTED")
        if request.method == "OPTIONS":
            return {}

        if request.content_type.split(";", 1)[0].lower() != "application/json":
            response.status = 415
            return error_report("", "SQL requests require application/json.", "REJECTED")
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
        with open(os.path.join(BASE_DIR, "scenarios.json")) as source:
            return {"scenarios": json.load(source)}


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

        def do_GET(self):
            if self.path == "/api/scenarios":
                try:
                    with open(os.path.join(BASE_DIR, "scenarios.json"), "r", encoding="utf-8") as source:
                        data = {"scenarios": json.load(source)}
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(json.dumps(data).encode("utf-8"))
                except Exception as ex:
                    self.send_response(500)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": str(ex)}).encode("utf-8"))
                return
            return super().do_GET()

        def do_POST(self):
            if self.path == "/api/whatif":
                origin = self.headers.get("Origin")
                if origin and origin != f"http://{self.headers.get('Host')}":
                    self.send_error(403, "Cross-origin SQL execution is not allowed.")
                    return
                if self.headers.get("Content-Type", "").split(";", 1)[0].lower() != "application/json":
                    self.send_error(415, "SQL requests require application/json.")
                    return
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
