#!/bin/bash
set -o pipefail

# Jaypore CI run script
# ---------------------
# This script is executed by Jaypore CI.
#
# Available environment variables:
#   JCI_COMMIT      - The git commit being tested
#   JCI_REPO_ROOT   - Absolute path to the repository root
#   JCI_OUTPUT_DIR  - Directory for CI artifacts (cwd at start)
#
# This example demonstrates managing secrets with Mozilla SOPS.
# Secrets are stored encrypted in the repo and decrypted at CI time.

echo "=== Jaypore CI: Secrets + Telegram ==="
echo "Commit : $JCI_COMMIT"
echo "Repo   : $JCI_REPO_ROOT"
echo "Output : $JCI_OUTPUT_DIR"
echo

cd "$JCI_REPO_ROOT" || exit 1

REPO_NAME=$(basename "$JCI_REPO_ROOT")
SHORT_COMMIT=$(echo "$JCI_COMMIT" | head -c 7)
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# ── Load secrets ─────────────────────────────────────────────
# Strategy:
#   1. If `sops` is installed and secrets.enc.json exists, decrypt it.
#   2. Otherwise fall back to plain environment variables.

load_secrets_from_sops() {
    local secrets_file="secrets.enc.json"
    if [ ! -f "$secrets_file" ]; then
        echo "WARNING: $secrets_file not found, skipping SOPS decryption"
        return 1
    fi
    echo "--- Decrypting secrets with SOPS ---"
    local decrypted
    decrypted=$(sops -d "$secrets_file" 2>&1)
    if [ $? -ne 0 ]; then
        echo "ERROR: sops decryption failed:"
        echo "$decrypted"
        return 1
    fi
    # Extract values from the decrypted JSON
    TELEGRAM_BOT_TOKEN=$(echo "$decrypted" | python3 -c "import sys,json; print(json.load(sys.stdin)['TELEGRAM_BOT_TOKEN'])")
    TELEGRAM_CHAT_ID=$(echo "$decrypted" | python3 -c "import sys,json; print(json.load(sys.stdin)['TELEGRAM_CHAT_ID'])")
    export TELEGRAM_BOT_TOKEN TELEGRAM_CHAT_ID
    echo "Secrets loaded from $secrets_file"
    return 0
}

if command -v sops &> /dev/null; then
    load_secrets_from_sops || echo "Falling back to environment variables"
else
    echo "--- SOPS not installed ---"
    echo "Install it to use encrypted secrets:"
    echo "  # Debian/Ubuntu"
    echo "  curl -LO https://github.com/getsops/sops/releases/download/v3.9.4/sops_3.9.4_amd64.deb"
    echo "  sudo dpkg -i sops_3.9.4_amd64.deb"
    echo ""
    echo "  # macOS"
    echo "  brew install sops"
    echo ""
    echo "Falling back to environment variables"
fi

# ── Run Django tests ─────────────────────────────────────────
echo
echo "--- Running Django tests ---"
TEST_OUTPUT=$(python3 manage.py test core 2>&1)
TEST_EXIT=$?

echo "$TEST_OUTPUT"
echo "$TEST_OUTPUT" > "$JCI_OUTPUT_DIR/test_output.txt"
echo "$TEST_EXIT"   > "$JCI_OUTPUT_DIR/exit_code.txt"

if [ "$TEST_EXIT" -eq 0 ]; then
    STATUS="✅ PASSED"
else
    STATUS="❌ FAILED"
fi

# ── Send Telegram notification ───────────────────────────────
MESSAGE=$(cat <<EOF
*CI Build — Secrets Example*

Repo: \`${REPO_NAME}\`
Commit: \`${SHORT_COMMIT}\`
Status: ${STATUS}
Time: ${TIMESTAMP}
EOF
)

if [ -n "$TELEGRAM_BOT_TOKEN" ] && [ -n "$TELEGRAM_CHAT_ID" ]; then
    echo
    echo "--- Sending Telegram notification ---"
    RESPONSE=$(curl -s -X POST \
        "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
        -d chat_id="$TELEGRAM_CHAT_ID" \
        -d text="$MESSAGE" \
        -d parse_mode="Markdown")
    echo "$RESPONSE" > "$JCI_OUTPUT_DIR/telegram_response.json"
    echo "Notification sent."
else
    echo
    echo "WARNING: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set, skipping notification"
fi

# ── Summary ──────────────────────────────────────────────────
echo
echo "=== Summary ==="
echo "Test result    : $STATUS"
echo "Test output    : test_output.txt"
echo "Exit code      : exit_code.txt"
echo "All artifacts in $JCI_OUTPUT_DIR"

exit "$TEST_EXIT"
