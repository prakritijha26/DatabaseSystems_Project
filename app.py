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

# Determine directory paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(BASE_DIR, "web")

# Import simulation engine
try:
    from engine import run_whatif  # Real PostgreSQL simulation engine if available
    ENGINE_SOURCE = "engine.py (Live PostgreSQL Engine)"
except ImportError:
    from mock_engine import run_whatif  # Contract-compliant mock engine
    ENGINE_SOURCE = "mock_engine.py (Offline Contract Simulation)"

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

        data = request.json or {}
        sql = data.get("sql", "").strip()

        if not sql:
            response.status = 400
            return {"error": "Missing 'sql' query in request body"}

        report = run_whatif(sql)
        report["engine_backend"] = ENGINE_SOURCE
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
                    sql = data.get("sql", "").strip()
                    report = run_whatif(sql)
                    report["engine_backend"] = ENGINE_SOURCE
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
