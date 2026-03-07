# 06 — Sub-pipelines

Run only the CI steps that matter for each commit by detecting which parts of a
monorepo actually changed.

## The problem

In a monorepo with independent services—say `python-app/`, `js-app/`, and
`go-app/`—running every linter, build, and test suite on every commit wastes
time.  A one-line docs fix in `python-app/` shouldn’t trigger the Go compiler.

## The pattern

```
git diff --name-only HEAD~1 HEAD
```

gives you the list of files touched in the latest commit.  Grep that list for
each top-level folder and conditionally execute the matching sub-pipeline:

```bash
changed=$(git diff --name-only HEAD~1 HEAD 2>/dev/null || true)

if echo "$changed" | grep -q '^python-app/'; then
    # run python lint + tests
fi
```

When the diff is empty (first commit, shallow clone, force-push) the script
falls back to running **all** sub-pipelines so nothing is silently skipped.

## What the script does

| Folder changed | Actions performed                  | Results file          |
|----------------|------------------------------------|-----------------------|
| `python-app/`  | Lint (ruff/flake8) + pytest        | `python-results.txt`  |
| `js-app/`      | npm install + eslint               | `js-results.txt`      |
| `go-app/`      | `go build` + `go test`             | `go-results.txt`      |

Each sub-pipeline writes its output to a dedicated results file in
`$JCI_OUTPUT_DIR` so you can inspect them independently.

## Adapting this to your project

- **Add more folders** — copy a sub-pipeline block and change the grep pattern.
- **Use path globs** — match `docs/` or `*.md` to trigger a docs-build step.
- **Parallel execution** — background each sub-pipeline and `wait` to run them
  concurrently.
- **Deeper diffs** — use `HEAD~N` or compare against a base branch
  (`git diff origin/main...HEAD`) for pull-request workflows.

## File layout

```
06-sub-pipelines/
├── .jci/
│   └── run.sh          # Main CI entry point
├── python-app/
│   ├── app.py          # Tiny Python module (add, greet)
│   └── test_app.py     # pytest tests
├── js-app/
│   ├── index.js        # Node module (add, greet)
│   └── package.json    # Minimal package manifest
├── go-app/
│   ├── main.go         # Go package (Add, Greet)
│   ├── main_test.go    # Go tests
│   └── go.mod          # Go module definition
└── README.md           # This file
```

Each sub-app is a self-contained, minimal demo—no external dependencies
required.  They exist purely to give the sub-pipeline script something real to
lint, build, and test.
