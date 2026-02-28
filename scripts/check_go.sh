#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

if ! command -v go >/dev/null 2>&1; then
    echo "Go toolchain not found in PATH."
    exit 1
fi

echo "Running gofmt checks..."
gofmt -e cmd > /dev/null
gofmt -e internal > /dev/null

echo "Running go vet..."
go vet ./...

echo "Go formatting, and vet checks passed."
