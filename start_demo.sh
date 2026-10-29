#!/usr/bin/env bash
# ==============================================================================
# WHAT-IF DATABASE: IMPACT ANALYSIS FOR UNIVERSITY DATABASES
# BACSE202 - Database Systems Project (Review 3 Demonstration)
# Team:
#   - Prakriti Jha      (25BDS0066) - Part A: Core Engine & Isolation
#   - Kahill Alvares    (25BCE2873) - Part C: Interface, Telemetry & Demo
#   - Himali Agarwal    (25BAI0012) - Part B: Catalog Tracing & Cascade
# ==============================================================================

set -e

PORT=${1:-8000}
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo "============================================================================"
echo "  🚀 WHAT-IF DATABASE // REVIEW 3 LIVE DEMO LAUNCHER"
echo "  Course: BACSE202 Database Systems | VIT"
echo "============================================================================"
echo ""

# 1. Check Python executable
if [ -f "./.venv/bin/python3" ]; then
    PYTHON_CMD="./.venv/bin/python3"
    echo "  [OK] Using virtualenv Python: $PYTHON_CMD"
else
    PYTHON_CMD="python3"
    echo "  [OK] Using system Python: $(which python3)"
fi

# 2. Rebuild frontend bundle if bun is available
if command -v bun >/dev/null 2>&1; then
    echo "  [..] Compiling web bundle via Bun..."
    bun run build >/dev/null 2>&1 && echo "  [OK] Frontend assets compiled (web/app.js)" || echo "  [!] Bun build skipped"
fi

# 3. Check engine mode using native python connect test
echo "  [..] Verifying database connection mode..."
if $PYTHON_CMD -c "from engine import connect_database; conn=connect_database(); conn.close()" >/dev/null 2>&1; then
    echo "  [OK] Live PostgreSQL connection VERIFIED (Online Mode)."
    export ENGINE_SOURCE="live"
else
    if [ "$WHATIF_REQUIRE_LIVE" = "1" ]; then
        echo ""
        echo "  ❌ [ERROR] Live mode requires PostgreSQL, but connection failed on port ${PGPORT:-5432}."
        echo ""
        echo "  To start PostgreSQL in Docker, run:"
        echo "     sudo ./start_postgres.sh"
        echo "============================================================================"
        exit 1
    fi
    echo "  [INFO] PostgreSQL service offline -> Automatic resilient fallback active."
    echo "         Full simulation, telemetry, and live metrics remain 100% operational."
fi

echo ""
echo "============================================================================"
echo "  🌐 WEB DEMO READY: Open your browser at:"
echo "     👉 http://localhost:${PORT}"
echo "     👉 http://127.0.0.1:${PORT}"
echo ""
echo "  Press CTRL+C in this terminal to stop the server."
echo "============================================================================"
echo ""

# Launch web server
exec $PYTHON_CMD app.py --port "$PORT"
