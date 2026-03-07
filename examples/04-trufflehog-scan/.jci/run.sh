#!/bin/bash
set -o pipefail

cd "$JCI_REPO_ROOT" || exit 1

REPO_NAME=$(basename "$JCI_REPO_ROOT")
SHORT_COMMIT=$(echo "$JCI_COMMIT" | head -c 7)
REPORT="$JCI_OUTPUT_DIR/trufflehog-report.txt"

echo "=== TruffleHog Secret Scan ==="
echo "Repo:   $REPO_NAME"
echo "Commit: $SHORT_COMMIT"
echo "Time:   $(date '+%Y-%m-%d %H:%M:%S')"
echo

# ── Run trufflehog3 scan (current working tree, no history) ──
echo "Scanning current working tree..."
trufflehog3 --no-history . > "$REPORT" 2>&1 || true

echo "Scanning commit history..."
trufflehog3 --no-current . >> "$REPORT" 2>&1 || true

# ── Report findings ──────────────────────────────────────────
if [ -s "$REPORT" ]; then
    FINDINGS=$(grep -c 'MEDIUM\|HIGH\|CRITICAL' "$REPORT" 2>/dev/null || echo "0")
    echo "⚠️  Found $FINDINGS potential issue(s). See report:"
    cat "$REPORT"
    echo
    echo "Report saved to trufflehog-report.txt"
    # In production you might: exit 1
    # For this example, we report but don't fail
else
    echo "✅ No secrets found."
fi

echo "=== Scan Complete ==="
exit 0
