#!/bin/bash
set -o pipefail

# --- Send mail via Python smtplib ---
send_mail() {
    local subject="$1"
    local body="$2"
    python3 - "$subject" "$body" <<'PYMAIL'
import sys, smtplib, os
from email.mime.text import MIMEText

subject = sys.argv[1]
body    = sys.argv[2]

msg = MIMEText(body)
msg["Subject"] = subject
msg["From"]    = os.environ["MAIL_FROM"]
msg["To"]      = os.environ["MAIL_TO"]

with smtplib.SMTP(os.environ["SMTP_HOST"], int(os.environ["SMTP_PORT"])) as srv:
    srv.starttls()
    srv.login(os.environ["SMTP_USER"], os.environ["SMTP_PASS"])
    srv.sendmail(msg["From"], [msg["To"]], msg.as_string())

print("Mail sent.")
PYMAIL
}

# --- Run tests ---
cd "$JCI_REPO_ROOT"

repo_name=$(basename "$JCI_REPO_ROOT")
timestamp=$(date -u +"%Y-%m-%d %H:%M:%S UTC")

python3 manage.py test core 2>&1 | tee "$JCI_OUTPUT_DIR/test-output.txt"
exit_code=${PIPESTATUS[0]}

# --- Notify on failure ---
if [ "$exit_code" -ne 0 ]; then
    subject="CI failure: ${repo_name} @ ${JCI_COMMIT:0:8}"
    body="Repository : ${repo_name}
Commit     : ${JCI_COMMIT}
Timestamp  : ${timestamp}
Exit code  : ${exit_code}

--- Test output (last 80 lines) ---
$(tail -n 80 "$JCI_OUTPUT_DIR/test-output.txt")"

    if [ -n "${SMTP_HOST:-}" ] && [ -n "${MAIL_FROM:-}" ] && [ -n "${MAIL_TO:-}" ]; then
        send_mail "$subject" "$body"
    else
        echo "WARNING: SMTP_HOST, MAIL_FROM, or MAIL_TO not set — skipping email notification"
    fi
fi

exit "$exit_code"
