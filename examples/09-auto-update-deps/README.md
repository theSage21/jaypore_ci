# Auto-Update Dependencies

Keep your project's Python dependencies fresh with a nightly CI job that
upgrades packages, runs the test suite, and commits the result.

## How it works

`.jci/crontab` schedules a run at midnight every day:

```
0 0 * * * run
```

When Jaypore CI fires the job, `.jci/run.sh`:

1. **Snapshots** the current `pip3 freeze` output so you have a baseline.
2. **Upgrades** every package listed in `requirements.txt` to its latest
   compatible version.
3. **Snapshots again** and produces a diff showing exactly what changed.
4. **Runs the Django test suite** (`manage.py test`) against the updated
   environment.
5. **On success** — freezes the new versions into `requirements.txt` and
   commits them automatically.
6. **On failure** — writes a report listing the updated packages and the
   test output so you can see what broke.

All intermediate artifacts (`before-update.txt`, `after-update.txt`,
`dep-diff.txt`, `test-results.txt`, and the failure report when applicable)
are saved to `$JCI_OUTPUT_DIR` for inspection.

## Why nightly updates?

* **Security** — patches land within hours, not weeks.
* **Small diffs** — a daily upgrade rarely touches more than a handful of
  packages, making breakage easy to diagnose.
* **No surprises** — if a new release breaks your tests you find out
  immediately instead of during a deadline-day deploy.

## Adapting this example

* Swap `pip3` commands for `npm`, `cargo`, `go get -u`, etc.
* Replace `manage.py test` with your project's test runner.
* Adjust the cron schedule (`0 0 * * 1` for weekly, for example).
* Add notifications (email, Slack) by extending `run.sh` after the
  success/failure branches.
