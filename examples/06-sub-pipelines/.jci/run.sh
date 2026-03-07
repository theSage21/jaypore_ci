#!/bin/bash
set -euo pipefail

# 06-sub-pipelines: Run CI steps only for parts of the monorepo that changed.
#
# Detects which top-level folders were modified in the latest commit and
# launches the matching sub-pipeline (python / js / go).  When no diff is
# available (e.g. the very first commit) every pipeline runs.

cd "$JCI_REPO_ROOT"

# ── Detect changed folders ───────────────────────────────────────────
changed_files=$(git diff --name-only HEAD~1 HEAD 2>/dev/null || true)

run_python=false
run_js=false
run_go=false

if [ -z "$changed_files" ]; then
    echo "No diff detected (first commit or shallow clone) — running all sub-pipelines."
    run_python=true
    run_js=true
    run_go=true
else
    echo "Changed files:"
    echo "$changed_files" | sed 's/^/  /'
    echo

    if echo "$changed_files" | grep -q '^06-sub-pipelines/python-app/'; then
        run_python=true
    fi
    if echo "$changed_files" | grep -q '^06-sub-pipelines/js-app/'; then
        run_js=true
    fi
    if echo "$changed_files" | grep -q '^06-sub-pipelines/go-app/'; then
        run_go=true
    fi
fi

pipelines_ran=0
summary=""

# ── Python sub-pipeline ──────────────────────────────────────────────
if $run_python; then
    echo "═══ Python sub-pipeline ═══"
    result_file="$JCI_OUTPUT_DIR/python-results.txt"
    {
        echo "Python sub-pipeline results"
        echo "Commit: $JCI_COMMIT"
        echo "Run at: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
        echo

        # Lint
        echo "── Lint ──"
        if [ -d 06-sub-pipelines/python-app ] && command -v python3 &>/dev/null; then
            if command -v ruff &>/dev/null; then
                echo "Running: ruff check 06-sub-pipelines/python-app/"
                ruff check 06-sub-pipelines/python-app/ 2>&1 && echo "Lint: PASS" || echo "Lint: FAIL"
            elif command -v flake8 &>/dev/null; then
                echo "Running: flake8 06-sub-pipelines/python-app/"
                flake8 06-sub-pipelines/python-app/ 2>&1 && echo "Lint: PASS" || echo "Lint: FAIL"
            else
                echo "No Python linter found (ruff/flake8) — checking syntax only."
                find 06-sub-pipelines/python-app -name '*.py' -exec python3 -m py_compile {} + 2>&1 \
                    && echo "Syntax check: PASS" || echo "Syntax check: FAIL"
            fi
        else
            echo "06-sub-pipelines/python-app/ directory or python3 not found — skipped."
        fi
        echo

        # Tests
        echo "── Tests ──"
        if [ -d 06-sub-pipelines/python-app ] && command -v python3 &>/dev/null; then
            if [ -f 06-sub-pipelines/python-app/requirements.txt ]; then
                echo "Installing dependencies…"
                pip install -q -r 06-sub-pipelines/python-app/requirements.txt 2>&1 || true
            fi
            echo "Running: python3 -m pytest 06-sub-pipelines/python-app/"
            python3 -m pytest 06-sub-pipelines/python-app/ 2>&1 && echo "Tests: PASS" || echo "Tests: FAIL"
        else
            echo "06-sub-pipelines/python-app/ directory or python3 not found — skipped."
        fi
    } | tee "$result_file"

    pipelines_ran=$((pipelines_ran + 1))
    summary="${summary}  ✔ python-app\n"
    echo
fi

# ── JS sub-pipeline ──────────────────────────────────────────────────
if $run_js; then
    echo "═══ JS sub-pipeline ═══"
    result_file="$JCI_OUTPUT_DIR/js-results.txt"
    {
        echo "JS sub-pipeline results"
        echo "Commit: $JCI_COMMIT"
        echo "Run at: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
        echo

        # Lint
        echo "── Lint ──"
        if [ -d 06-sub-pipelines/js-app ]; then
            if [ -f 06-sub-pipelines/js-app/package.json ] && command -v npm &>/dev/null; then
                echo "Installing dependencies…"
                (cd 06-sub-pipelines/js-app && npm ci --ignore-scripts 2>&1) || true
                if [ -x 06-sub-pipelines/js-app/node_modules/.bin/eslint ]; then
                    echo "Running: eslint 06-sub-pipelines/js-app/"
                    06-sub-pipelines/js-app/node_modules/.bin/eslint 06-sub-pipelines/js-app/ 2>&1 \
                        && echo "Lint: PASS" || echo "Lint: FAIL"
                else
                    echo "eslint not installed — listing JS files instead."
                    find 06-sub-pipelines/js-app -name '*.js' -o -name '*.ts' | head -20
                    echo "Lint: SKIPPED"
                fi
            else
                echo "No package.json or npm not available — checking syntax with node."
                if command -v node &>/dev/null; then
                    find 06-sub-pipelines/js-app -name '*.js' -exec node --check {} \; 2>&1 \
                        && echo "Syntax check: PASS" || echo "Syntax check: FAIL"
                else
                    echo "node not found — skipped."
                fi
            fi
        else
            echo "06-sub-pipelines/js-app/ directory not found — skipped."
        fi
    } | tee "$result_file"

    pipelines_ran=$((pipelines_ran + 1))
    summary="${summary}  ✔ js-app\n"
    echo
fi

# ── Go sub-pipeline ──────────────────────────────────────────────────
if $run_go; then
    echo "═══ Go sub-pipeline ═══"
    result_file="$JCI_OUTPUT_DIR/go-results.txt"
    {
        echo "Go sub-pipeline results"
        echo "Commit: $JCI_COMMIT"
        echo "Run at: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
        echo

        # Build & test
        echo "── Build & Test ──"
        if [ -d 06-sub-pipelines/go-app ]; then
            if command -v go &>/dev/null; then
                echo "Running: go build ./06-sub-pipelines/go-app/..."
                (cd 06-sub-pipelines/go-app && go build ./...) 2>&1 && echo "Build: PASS" || echo "Build: FAIL"
                echo
                echo "Running: go test ./06-sub-pipelines/go-app/..."
                (cd 06-sub-pipelines/go-app && go test ./...) 2>&1 && echo "Test: PASS" || echo "Test: FAIL"
            else
                echo "go not found — skipped."
            fi
        else
            echo "06-sub-pipelines/go-app/ directory not found — skipped."
        fi
    } | tee "$result_file"

    pipelines_ran=$((pipelines_ran + 1))
    summary="${summary}  ✔ go-app\n"
    echo
fi

# ── Summary ──────────────────────────────────────────────────────────
echo "═══════════════════════════════════════"
echo "Sub-pipeline summary  ($pipelines_ran ran)"
echo "═══════════════════════════════════════"

if [ $pipelines_ran -eq 0 ]; then
    echo "  No sub-pipelines matched the changed files."
else
    printf "$summary"
fi

echo
echo "Result files in $JCI_OUTPUT_DIR:"
ls -1 "$JCI_OUTPUT_DIR"/*.txt 2>/dev/null || echo "  (none)"
