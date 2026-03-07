# 05 — Lint & Fix on Pre-Commit

Run lint checks automatically before every `git commit` using Jaypore CI.
This example targets a Django project (Python-heavy) but includes stubs for
Go and JavaScript files in the same repo.

## What it does

| Language   | Tool                       | Action                              |
|------------|----------------------------|-------------------------------------|
| Python     | `py_compile`, `black`      | Syntax-check all `.py` files; verify formatting |
| Go         | `gofmt`                    | List unformatted `.go` files        |
| JavaScript | `eslint --fix`             | Auto-fix and report remaining errors |

Results are saved to `$JCI_OUTPUT_DIR/lint-results.txt` so Jaypore CI can
render them in its dashboard.

## Setup

### 1. Copy the CI script into your project

```bash
mkdir -p .jci
cp .jci/run.sh /path/to/your/project/.jci/run.sh
```

### 2. Install the pre-commit hook

```bash
./install-hook.sh            # uses the current repo
# or
./install-hook.sh /path/to/your/project
```

This creates `.git/hooks/pre-commit` which calls `git jci run` before each
commit. If any lint check fails the commit is blocked.

### 3. Commit as usual

```bash
git add .
git commit -m "my changes"
# Jaypore CI runs automatically; commit proceeds only if all checks pass.
```

## How it works

1. Git fires the **pre-commit** hook before creating a commit object.
2. The hook runs `git jci run`, which executes `.jci/run.sh`.
3. `run.sh` walks through Python, Go, and JS checks, recording output to
   `lint-results.txt`.
4. If **any** check fails, `run.sh` exits non-zero → the hook exits non-zero
   → Git aborts the commit.
5. Fix the reported issues, `git add` the fixes, and commit again.

## Skipping the hook

In an emergency you can bypass the pre-commit hook:

```bash
git commit --no-verify -m "skip lint this time"
```

## Files

```
05-lint-fix-precommit/
├── .jci/
│   └── run.sh           # Jaypore CI script — lint checks
├── install-hook.sh      # Helper to install the git hook
└── README.md            # This file
```
