#!/usr/bin/env bash
set -euo pipefail

# ── Navigate to the project directory ────────────────────────────────────────
cd "$JCI_REPO_ROOT/00-golang-lint-build-test"
echo "==> Working directory: $(pwd)"
echo "==> Commit: ${JCI_COMMIT:-unknown}"
echo

# ── Initialise Go module if needed ───────────────────────────────────────────
if [ ! -f go.mod ]; then
    echo "==> No go.mod found – initialising module"
    go mod init example.com/server
fi

# ── Lint (go vet) ────────────────────────────────────────────────────────────
echo "==> Running go vet ./..."
go vet ./... 2>&1 | tee "$JCI_OUTPUT_DIR/vet-report.txt"
echo "    vet report saved to \$JCI_OUTPUT_DIR/vet-report.txt"
echo

# ── Format check ─────────────────────────────────────────────────────────────
echo "==> Checking formatting with gofmt"
unformatted=$(gofmt -l .)
if [ -n "$unformatted" ]; then
    echo "    ERROR: the following files need gofmt:"
    echo "$unformatted"
    exit 1
fi
echo "    all files formatted correctly"
echo

# ── Build ────────────────────────────────────────────────────────────────────
echo "==> Building binary"
go build -o "$JCI_OUTPUT_DIR/server" .
echo "    binary saved to \$JCI_OUTPUT_DIR/server"
echo

# ── Test ─────────────────────────────────────────────────────────────────────
echo "==> Running tests"
go test -v -cover ./... 2>&1 | tee "$JCI_OUTPUT_DIR/test-results.txt"
echo "    test results saved to \$JCI_OUTPUT_DIR/test-results.txt"
echo

# ── Publish (optional) ───────────────────────────────────────────────────────
if [ -n "${PUBLISH_DIR:-}" ]; then
    echo "==> Publishing binary to $PUBLISH_DIR"
    mkdir -p "$PUBLISH_DIR"
    cp "$JCI_OUTPUT_DIR/server" "$PUBLISH_DIR/server"
    echo "    published successfully"
else
    echo "==> PUBLISH_DIR not set – skipping publish step"
fi
echo

# ── Summary ──────────────────────────────────────────────────────────────────
echo "========================================"
echo "  Pipeline complete"
echo "  Commit  : ${JCI_COMMIT:-unknown}"
echo "  Binary  : $JCI_OUTPUT_DIR/server"
echo "  Vet     : $JCI_OUTPUT_DIR/vet-report.txt"
echo "  Tests   : $JCI_OUTPUT_DIR/test-results.txt"
echo "========================================"
