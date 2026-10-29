#!/usr/bin/env bash
# ==============================================================================
# WHAT-IF DATABASE: POSTGRESQL 15 STARTER SCRIPT
# Starts the whatif_postgres container using native docker (no compose needed)
# ==============================================================================

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

CONTAINER_NAME="whatif_postgres"

# Check if docker is installed
if ! command -v docker >/dev/null 2>&1; then
    echo "❌ Docker is not installed on this system."
    exit 1
fi

# Detect whether sudo is needed for docker
DOCKER_CMD="docker"
if ! docker ps >/dev/null 2>&1; then
    DOCKER_CMD="sudo docker"
fi

echo "🐘 Starting PostgreSQL 15 Container ($CONTAINER_NAME)..."

# 1. Check if container is already running
if $DOCKER_CMD ps --format '{{.Names}}' 2>/dev/null | grep -q "^${CONTAINER_NAME}$"; then
    echo "✅ Container '$CONTAINER_NAME' is already running on port 5432."
    exit 0
fi

# 2. Check if stopped container exists
if $DOCKER_CMD ps -a --format '{{.Names}}' 2>/dev/null | grep -q "^${CONTAINER_NAME}$"; then
    echo "▶️  Starting existing container '$CONTAINER_NAME'..."
    $DOCKER_CMD start "$CONTAINER_NAME"
else
    echo "📦 Creating and launching container '$CONTAINER_NAME'..."
    $DOCKER_CMD run -d \
        --name "$CONTAINER_NAME" \
        -e POSTGRES_DB=whatif_practice \
        -e POSTGRES_USER=postgres \
        -e POSTGRES_PASSWORD=25BDS0066 \
        -p 5432:5432 \
        -v "$PROJECT_DIR/schema.sql:/docker-entrypoint-initdb.d/01-schema.sql:ro" \
        -v "$PROJECT_DIR/seed.sql:/docker-entrypoint-initdb.d/02-seed.sql:ro" \
        postgres:15-alpine
fi

echo "⏳ Waiting for PostgreSQL to initialize..."
for i in $(seq 1 15); do
    if $DOCKER_CMD exec "$CONTAINER_NAME" pg_isready -U postgres -d whatif_practice >/dev/null 2>&1; then
        echo "✅ PostgreSQL is ready and accepting connections on port 5432!"
        exit 0
    fi
    sleep 1
done

echo "ℹ️  Container '$CONTAINER_NAME' started. Verifying database connection..."
