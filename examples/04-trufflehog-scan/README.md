# TruffleHog Secret Scan

Automatically scan your repository for leaked secrets every hour using
[trufflehog3](https://github.com/feeltheajf/trufflehog3).

## What is TruffleHog?

TruffleHog scans a Git repository for accidentally committed secrets—API keys,
tokens, passwords, private keys, and other high-entropy strings that should
never appear in source control. It checks both the current working tree and the
full commit history, so even secrets that were "deleted" in a later commit are
caught.

## How the hourly scan works

The file `.jci/crontab` contains:

```
0 * * * * run
```

This tells Jaypore CI to execute `.jci/run.sh` once every hour (at minute 0).

To install (or update) this schedule into the system crontab, run:

```bash
git jci cron sync
```

`cron sync` reads `.jci/crontab`, translates each line into a real crontab
entry that invokes `git jci run` inside the repository, and writes it to the
current user's crontab. Run the command again after changing `.jci/crontab` to
pick up new schedules.

## What the scan does

1. `cd` into the repo root.
2. Run `trufflehog3` against the current working tree to find secrets in
   checked-out files.
3. Run `trufflehog3` against the commit history to find secrets that were ever
   committed.
4. Merge both results into `$JCI_OUTPUT_DIR/trufflehog-report.txt`.
5. If any secrets are found, print the report and exit with code **1** so
   Jaypore CI records the run as failed.
6. If the repo is clean, exit with code **0**.

## Customisation

You can tweak the scan by editing `.jci/run.sh`:

- **Severity filter** – add `--severity HIGH` to only flag high-confidence
  findings.
- **Limit history depth** – add `--depth 100` to scan only the last 100
  commits.
- **Custom rules** – pass `--rules /path/to/rules.yaml` to use your own
  patterns.
- **JSON output** – change `--format TEXT` to `--format JSON` for
  machine-readable results.
