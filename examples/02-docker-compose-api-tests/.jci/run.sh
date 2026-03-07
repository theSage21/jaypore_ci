#!/bin/bash
set -e

echo "=== Jaypore CI: Docker Compose API Tests ==="
echo "Commit: $JCI_COMMIT"
echo "Repo root: $JCI_REPO_ROOT"
echo "Output dir: $JCI_OUTPUT_DIR"

PROJECT_DIR="$JCI_REPO_ROOT/02-docker-compose-api-tests"
cd "$PROJECT_DIR"

COMPOSE_PROJECT="jci-api-tests-$$"

cleanup() {
    echo "=== Cleaning up ==="
    docker compose -p "$COMPOSE_PROJECT" down -v --remove-orphans 2>/dev/null || true
}
trap cleanup EXIT

# ---- Start services ----
echo "=== Starting services ==="
docker compose -p "$COMPOSE_PROJECT" up -d --build 2>&1 | tee "$JCI_OUTPUT_DIR/compose-up.log"

# ---- Wait for web service to respond ----
echo "=== Waiting for web service ==="
MAX_WAIT=90
ELAPSED=0

# Find the mapped port for web:8000
while [ $ELAPSED -lt $MAX_WAIT ]; do
    WEB_PORT=$(docker compose -p "$COMPOSE_PROJECT" port web 8000 2>/dev/null | cut -d: -f2 || true)
    if [ -n "$WEB_PORT" ]; then
        # Check if web responds
        if curl -sf "http://localhost:$WEB_PORT/health/" >/dev/null 2>&1; then
            echo "  Web service healthy on port $WEB_PORT!"
            break
        fi
    fi
    echo "  [$ELAPSED s] waiting..."
    sleep 5
    ELAPSED=$((ELAPSED + 5))
done

if [ $ELAPSED -ge $MAX_WAIT ]; then
    echo "ERROR: Services did not become healthy within ${MAX_WAIT}s"
    docker compose -p "$COMPOSE_PROJECT" ps 2>&1 | tee "$JCI_OUTPUT_DIR/compose-ps.log"
    docker compose -p "$COMPOSE_PROJECT" logs 2>&1 | tee "$JCI_OUTPUT_DIR/compose-logs.log"
    exit 1
fi

BASE_URL="http://localhost:${WEB_PORT}"
echo "=== Web service at $BASE_URL ==="

# ---- Run API tests ----
echo "=== Running API tests ==="
bash "$PROJECT_DIR/test_api.sh" "$BASE_URL" "$JCI_OUTPUT_DIR" 2>&1 \
    | tee "$JCI_OUTPUT_DIR/test-output.log"
TEST_EXIT=${PIPESTATUS[0]}

# ---- Capture logs for artifacts ----
docker compose -p "$COMPOSE_PROJECT" logs 2>&1 > "$JCI_OUTPUT_DIR/compose-logs.log"

echo "=== CI Complete (exit $TEST_EXIT) ==="
exit $TEST_EXIT
