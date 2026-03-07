#!/bin/bash
set -euo pipefail

# ── Auto-Update Dependencies ─────────────────────────────────────────
# Scheduled at midnight via .jci/crontab.
# Updates all pip packages, runs the test suite, and reports results.
# ─────────────────────────────────────────────────────────────────────

cd "$JCI_REPO_ROOT"

echo "==> Snapshot current dependency versions"
pip3 freeze 2>/dev/null > "$JCI_OUTPUT_DIR/before-update.txt"

echo "==> Upgrading packages from requirements.txt"
pip3 install --break-system-packages --upgrade -r requirements.txt 2>&1 | tee "$JCI_OUTPUT_DIR/upgrade-log.txt" || true

echo "==> Snapshot new dependency versions"
pip3 freeze 2>/dev/null > "$JCI_OUTPUT_DIR/after-update.txt"

echo "==> Dependency diff"
if diff "$JCI_OUTPUT_DIR/before-update.txt" "$JCI_OUTPUT_DIR/after-update.txt" \
     > "$JCI_OUTPUT_DIR/dep-diff.txt" 2>&1; then
    echo "No dependency changes."
else
    echo "Changed packages:"
    cat "$JCI_OUTPUT_DIR/dep-diff.txt"
fi

echo "==> Running test suite"
if python3 manage.py test core --no-input 2>&1 | tee "$JCI_OUTPUT_DIR/test-results.txt"; then
    echo "==> Tests passed after update"

    # Freeze the verified versions back into requirements.txt
    # In a real setup, you'd commit updated requirements:
    # pip3 freeze > requirements.txt && git add requirements.txt && git commit -m "chore: auto-update deps"
    echo "Dependencies verified — would commit in a real workflow"

    echo "SUCCESS" > "$JCI_OUTPUT_DIR/status.txt"
else
    echo "==> Tests FAILED after update"
    echo "The following packages were updated:" > "$JCI_OUTPUT_DIR/failure-report.txt"
    cat "$JCI_OUTPUT_DIR/dep-diff.txt"        >> "$JCI_OUTPUT_DIR/failure-report.txt"
    echo ""                                    >> "$JCI_OUTPUT_DIR/failure-report.txt"
    echo "Test output:"                        >> "$JCI_OUTPUT_DIR/failure-report.txt"
    cat "$JCI_OUTPUT_DIR/test-results.txt"     >> "$JCI_OUTPUT_DIR/failure-report.txt"

    echo "Failure report:"
    cat "$JCI_OUTPUT_DIR/failure-report.txt"

    echo "FAILURE" > "$JCI_OUTPUT_DIR/status.txt"
    exit 1
fi
