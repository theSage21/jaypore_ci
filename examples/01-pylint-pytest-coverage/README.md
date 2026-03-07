# Example 01 — Pylint + Pytest + Coverage

This Jaypore CI example runs three checks on a Django project:

| Step | Tool | What it does |
|------|------|--------------|
| 1 | **Pylint** | Static analysis of the `core/` app. |
| 2 | **Pytest** | Runs the test suite. |
| 3 | **Coverage** | Generates a terminal summary and an HTML coverage report. |

## Artifacts produced

| File | Description |
|------|-------------|
| `pylint-report.txt` | Full Pylint output. |
| `pytest-results.txt` | Pytest output including the coverage summary. |
| `htmlcov/index.html` | Browsable HTML coverage report. |

## Project layout assumed

```
your-repo/
├── manage.py
├── mysite/
│   └── settings.py
├── core/            # the Django app under test
└── .jci/
    └── run.sh       # ← this script
```

## How to use

1. Copy the `.jci/` directory into your Django project's repository root:

   ```bash
   cp -r 01-pylint-pytest-coverage/.jci /path/to/your-repo/.jci
   ```

2. Make sure the required Python packages are installed:

   ```bash
   pip install pylint pytest pytest-cov pytest-django
   ```

3. Run Jaypore CI:

   ```bash
   git jci run
   ```

   Jaypore CI will execute `.jci/run.sh`, and the generated artifacts will be
   available in the CI output directory.

## Customisation

- **Different app name** — replace `core` with your app name in `run.sh`.
- **Different settings module** — change `mysite.settings` to match yours.
- **Fail on lint score** — remove `|| true` after the `pylint` command to make
  the build fail when Pylint reports issues.
