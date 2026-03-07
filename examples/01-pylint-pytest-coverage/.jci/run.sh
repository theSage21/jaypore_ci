#!/bin/bash
set -euo pipefail

# Jaypore CI run script
# ---------------------
# This script is executed by Jaypore CI.
#
# Available environment variables:
#   JCI_COMMIT      - The git commit being tested
#   JCI_REPO_ROOT   - Absolute path to the repository root
#   JCI_OUTPUT_DIR  - Directory for CI artifacts (cwd at start)
#
# Any files written to JCI_OUTPUT_DIR become CI artifacts.

echo "=== Jaypore CI: Pylint + Pytest + Coverage ==="
echo "Commit : $JCI_COMMIT"
echo "Repo   : $JCI_REPO_ROOT"
echo "Output : $JCI_OUTPUT_DIR"
echo

cd "$JCI_REPO_ROOT"

# ---- 1. Pylint ----
echo "--- Running Pylint on core/ ---"
DJANGO_SETTINGS_MODULE=mysite.settings \
pylint core/ \
    --output-format=text \
    --disable=C0114,C0115,C0116 \
    | tee "$JCI_OUTPUT_DIR/pylint-report.txt" \
    || true   # don't fail the build on lint warnings
echo

# ---- 2. Pytest + Coverage ----
echo "--- Running Pytest with Coverage ---"
pytest \
    --cov=core \
    --cov-report=html:"$JCI_OUTPUT_DIR/htmlcov" \
    --cov-report=term \
    | tee "$JCI_OUTPUT_DIR/pytest-results.txt"
echo

# ---- 3. Summary ----
echo "=== Summary ==="
echo "Pylint report : pylint-report.txt"
echo "Pytest output : pytest-results.txt"
echo "Coverage HTML : htmlcov/index.html"
echo "All artifacts are in $JCI_OUTPUT_DIR"
