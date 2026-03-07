#!/bin/bash
set -euo pipefail

# Jaypore CI: Lint & fix for a multi-language repo (Python/Go/JS)
# Intended to run as a pre-commit check via `git jci run`.
#
# Environment provided by Jaypore CI:
#   JCI_COMMIT      - the commit being checked
#   JCI_REPO_ROOT   - root of the git repository
#   JCI_OUTPUT_DIR  - directory for build artifacts (cwd at start)

RESULTS="${JCI_OUTPUT_DIR}/lint-results.txt"
: > "$RESULTS"

cd "$JCI_REPO_ROOT"

overall_status=0

# ── Python ──────────────────────────────────────────────────────────
echo "=== Python lint ===" | tee -a "$RESULTS"

# Syntax check every .py file
py_files=$(find . -name '*.py' -not -path './.git/*' -not -path './node_modules/*' || true)
if [ -n "$py_files" ]; then
    py_errors=0
    while IFS= read -r f; do
        if ! python3 -m py_compile "$f" 2>>"$RESULTS"; then
            py_errors=$((py_errors + 1))
        fi
    done <<< "$py_files"

    if [ "$py_errors" -gt 0 ]; then
        echo "FAIL: $py_errors Python file(s) have syntax errors" | tee -a "$RESULTS"
        overall_status=1
    else
        echo "OK: all Python files pass syntax check" | tee -a "$RESULTS"
    fi

    # Formatter check (black)
    if command -v black &>/dev/null; then
        echo "--- black --check ---" | tee -a "$RESULTS"
        if ! black --check . 2>&1 | tee -a "$RESULTS"; then
            echo "FAIL: black found files that need reformatting" | tee -a "$RESULTS"
            echo "  Run 'black .' to fix, then re-commit." | tee -a "$RESULTS"
            overall_status=1
        else
            echo "OK: black is happy" | tee -a "$RESULTS"
        fi
    else
        echo "SKIP: black not installed" | tee -a "$RESULTS"
    fi
else
    echo "SKIP: no .py files found" | tee -a "$RESULTS"
fi

# ── Go ──────────────────────────────────────────────────────────────
echo "" | tee -a "$RESULTS"
echo "=== Go lint ===" | tee -a "$RESULTS"

go_files=$(find . -name '*.go' -not -path './.git/*' -not -path './vendor/*' || true)
if [ -n "$go_files" ]; then
    if command -v gofmt &>/dev/null; then
        unformatted=$(gofmt -l . 2>&1 || true)
        if [ -n "$unformatted" ]; then
            echo "FAIL: the following Go files need formatting:" | tee -a "$RESULTS"
            echo "$unformatted" | tee -a "$RESULTS"
            echo "  Run 'gofmt -w .' to fix, then re-commit." | tee -a "$RESULTS"
            overall_status=1
        else
            echo "OK: all Go files are formatted" | tee -a "$RESULTS"
        fi
    else
        echo "SKIP: gofmt not installed" | tee -a "$RESULTS"
    fi
else
    echo "SKIP: no .go files found" | tee -a "$RESULTS"
fi

# ── JavaScript ──────────────────────────────────────────────────────
echo "" | tee -a "$RESULTS"
echo "=== JavaScript lint ===" | tee -a "$RESULTS"

js_files=$(find . -name '*.js' -not -path './.git/*' -not -path './node_modules/*' || true)
if [ -n "$js_files" ]; then
    if [ -f package.json ] && command -v npx &>/dev/null; then
        echo "--- eslint --fix ---" | tee -a "$RESULTS"
        # --fix rewrites files in place; the pre-commit hook should
        # stage the corrections automatically.
        if ! npx eslint --fix . 2>&1 | tee -a "$RESULTS"; then
            echo "FAIL: eslint reported errors that could not be auto-fixed" | tee -a "$RESULTS"
            overall_status=1
        else
            echo "OK: eslint passed (auto-fixable issues were corrected)" | tee -a "$RESULTS"
        fi
    else
        echo "SKIP: npx/package.json not available" | tee -a "$RESULTS"
    fi
else
    echo "SKIP: no .js files found" | tee -a "$RESULTS"
fi

# ── Summary ─────────────────────────────────────────────────────────
echo "" | tee -a "$RESULTS"
if [ "$overall_status" -eq 0 ]; then
    echo "✅ All lint checks passed." | tee -a "$RESULTS"
else
    echo "❌ Some lint checks failed. See above for details." | tee -a "$RESULTS"
fi

exit "$overall_status"
