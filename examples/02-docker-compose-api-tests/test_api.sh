#!/bin/bash
# test_api.sh — Run API tests against the Django app
#
# Usage: ./test_api.sh <base_url> <output_dir>

set -euo pipefail

BASE_URL="${1:-http://localhost:8000}"
OUTPUT_DIR="${2:-.}"

PASSED=0
FAILED=0
RESULTS=""

run_test() {
    local name="$1"
    local url="$2"
    local expected_code="$3"
    local expected_body="$4"  # substring to look for in response body

    echo -n "TEST: $name ... "

    local http_code body
    body=$(curl -s -w '\n%{http_code}' "$url" 2>&1) || true
    http_code=$(echo "$body" | tail -1)
    body=$(echo "$body" | sed '$d')

    local status="PASS"
    local detail=""

    if [ "$http_code" != "$expected_code" ]; then
        status="FAIL"
        detail="expected HTTP $expected_code, got $http_code"
    elif [ -n "$expected_body" ] && ! echo "$body" | grep -q "$expected_body"; then
        status="FAIL"
        detail="response body missing '$expected_body'"
    fi

    if [ "$status" = "PASS" ]; then
        echo "PASS"
        PASSED=$((PASSED + 1))
    else
        echo "FAIL ($detail)"
        FAILED=$((FAILED + 1))
    fi

    RESULTS+="$status  $name  (HTTP $http_code)  $detail\n"
}

echo "========================================"
echo "API Tests — $BASE_URL"
echo "========================================"
echo

# --- Health endpoint ---
run_test "GET /health/ returns 200"       "$BASE_URL/health/" 200 '"status"'
run_test "GET /health/ contains ok"        "$BASE_URL/health/" 200 '"ok"'

# --- Items endpoint ---
run_test "GET /items/ returns 200"         "$BASE_URL/items/"  200 '"items"'
run_test "GET /items/ returns JSON array"  "$BASE_URL/items/"  200 'items'

# --- Not Found ---
run_test "GET /nonexistent/ returns 404"   "$BASE_URL/nonexistent/" 404 ''

echo
echo "========================================"
echo "Results: $PASSED passed, $FAILED failed"
echo "========================================"

# Write results file
{
    echo "API Test Results"
    echo "================"
    echo "Base URL: $BASE_URL"
    echo "Date: $(date -u)"
    echo
    echo -e "$RESULTS"
    echo "Total: $PASSED passed, $FAILED failed"
} > "$OUTPUT_DIR/api-test-results.txt"

if [ "$FAILED" -gt 0 ]; then
    exit 1
fi
