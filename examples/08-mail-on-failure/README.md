# 08 — Mail on failure

Send an email whenever a scheduled CI run fails.

## What it does

A cron entry (`0 0 * * *`) triggers `run.sh` once a day at midnight.
The script runs `python3 manage.py test core` and, only when the tests
fail, sends an email containing:

- repository name
- commit hash
- timestamp
- the tail of the test output

Test output is always saved to `$JCI_OUTPUT_DIR/test-output.txt` so you
can inspect it later regardless of pass/fail.

## Required environment variables

| Variable | Purpose |
|---|---|
| `SMTP_HOST` | SMTP server hostname (e.g. `smtp.mailgun.org`) |
| `SMTP_PORT` | SMTP port, typically `587` for STARTTLS |
| `SMTP_USER` | SMTP login username |
| `SMTP_PASS` | SMTP login password or API key |
| `MAIL_FROM` | Sender address (e.g. `ci@example.com`) |
| `MAIL_TO` | Recipient address |

Set these in your CI environment or in a `.env` file that your Jaypore CI
setup sources before running the pipeline.

## How it works

1. `run.sh` changes into `$JCI_REPO_ROOT` and runs the Django test suite.
2. Output is piped to both stdout and `$JCI_OUTPUT_DIR/test-output.txt`.
3. If the exit code is non-zero, a `send_mail()` helper uses Python's
   `smtplib` to deliver a failure report over SMTP/STARTTLS.
4. The script exits with the original test exit code so Jaypore CI
   records the run as failed.
