#!/usr/bin/env bash
# ==============================================================================
# WHAT-IF DATABASE: INTERACTIVE TERMINAL LAUNCHER (whatif.sh)
# BACSE202 - Database Systems Project (Final Review 3)
# ==============================================================================

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# Check for --online / --live flags
for arg in "$@"; do
    if [ "$arg" = "--online" ] || [ "$arg" = "--live" ] || [ "$arg" = "-l" ]; then
        export WHATIF_REQUIRE_LIVE=1
        break
    fi
done

# Filter out --online / --live / -l from arguments passed down
NEW_ARGS=()
for arg in "$@"; do
    if [ "$arg" != "--online" ] && [ "$arg" != "--live" ] && [ "$arg" != "-l" ]; then
        NEW_ARGS+=("$arg")
    fi
done
set -- ${NEW_ARGS[@]+"${NEW_ARGS[@]}"}

# Check Python / Bun runtimes
if [ -f "./.venv/bin/python3" ]; then
    PYTHON_CMD="./.venv/bin/python3"
else
    PYTHON_CMD="python3"
fi
export WHATIF_PYTHON="$PYTHON_CMD"

if [ "$1" = "--web" ] || [ "$1" = "-w" ]; then
    exec ./start_demo.sh "${2:-8000}"
elif [ "$1" = "--demo" ] || [ "$1" = "-d" ]; then
    if command -v bun >/dev/null 2>&1; then
        exec bun run demo
    else
        exec $PYTHON_CMD demo.py
    fi
elif [ -n "$1" ]; then
    # Direct query execution
    if command -v bun >/dev/null 2>&1; then
        exec bun run src/cli.ts "$@"
    else
        exec $PYTHON_CMD cli.py "$@"
    fi
else
    # Interactive REPL
    if command -v bun >/dev/null 2>&1; then
        exec bun run src/cli.ts
    else
        exec $PYTHON_CMD cli.py
    fi
fi
