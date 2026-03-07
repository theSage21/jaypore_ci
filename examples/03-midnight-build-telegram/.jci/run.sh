#!/bin/bash
set -o pipefail

cd "$JCI_REPO_ROOT" || exit 1

REPO_NAME=$(basename "$JCI_REPO_ROOT")
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
SHORT_COMMIT=$(echo "$JCI_COMMIT" | head -c 7)

# ── Run Django tests ─────────────────────────────────────────
TEST_OUTPUT=$(python3 manage.py test core 2>&1)
TEST_EXIT=$?

# ── Save results to output dir ───────────────────────────────
echo "$TEST_OUTPUT" > "$JCI_OUTPUT_DIR/test_output.txt"
echo "$TEST_EXIT"   > "$JCI_OUTPUT_DIR/exit_code.txt"

if [ "$TEST_EXIT" -eq 0 ]; then
    STATUS="✅ PASSED"
else
    STATUS="❌ FAILED"
fi

# ── Send Telegram notification ───────────────────────────────
MESSAGE=$(cat <<EOF
*Midnight Build Report*

Repo: \`${REPO_NAME}\`
Commit: \`${SHORT_COMMIT}\`
Status: ${STATUS}
Timestamp: ${TIMESTAMP}
EOF
)

if [ -n "$TELEGRAM_BOT_TOKEN" ] && [ -n "$TELEGRAM_CHAT_ID" ]; then
    curl -s -X POST \
        "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
        -d chat_id="$TELEGRAM_CHAT_ID" \
        -d text="$MESSAGE" \
        -d parse_mode="Markdown" \
        > /dev/null
else
    echo "WARNING: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set, skipping notification"
fi

exit "$TEST_EXIT"
