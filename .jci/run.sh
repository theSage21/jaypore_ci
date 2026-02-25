#!/bin/bash

# CI script for git-jci
# This runs in .jci/<commit>/ directory
# Environment variables available:
#   JCI_COMMIT     - Full commit hash
#   JCI_REPO_ROOT  - Repository root path
#   JCI_OUTPUT_DIR - Output directory (where artifacts should go)

set -e

echo "=== JCI CI Pipeline ==="
echo "Commit: ${JCI_COMMIT:0:12}"
echo ""

cd "$JCI_REPO_ROOT"

echo "Running tests..."
go test ./...
echo ""

echo "Building static binary (CGO_ENABLED=0)..."
CGO_ENABLED=0 go build -ldflags='-s -w -extldflags "-static"' -o "$JCI_OUTPUT_DIR/git-jci" ./cmd/git-jci

# Verify it's static
echo ""
echo "Binary info:"
file "$JCI_OUTPUT_DIR/git-jci"
ls -lh "$JCI_OUTPUT_DIR/git-jci"

echo ""
echo "All steps completed successfully!"
echo ""
echo "=== Installation ==="
echo "Download and install with:"
echo "  curl -fsSL \$(git jci web --url)/git-jci -o /tmp/git-jci && sudo install /tmp/git-jci /usr/local/bin/"
