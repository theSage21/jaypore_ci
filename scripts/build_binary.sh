#!/bin/bash
set -euo pipefail

# ---------------------------------------------------------------------------
# Build a static git-jci binary for the requested platform.
#
# Required environment variables (set by the calling docker run command):
#   GOOS                - Target OS  (linux | windows | darwin)
#   GOARCH              - Target arch (amd64 | arm64 | arm)
#   OUTPUT_BINARY_NAME  - Final filename placed in ${OUTPUT_DIR}
#                         e.g. git-jci-linux-amd64  /  git-jci-windows-amd64.exe
#
# Optional:
#   GOARM               - ARM version for GOARCH=arm  (default: 7)
# ---------------------------------------------------------------------------

REPO_DIR="/tmp/repo"
OUTPUT_DIR="${REPO_DIR}/bin"
ENTRY_POINT="./cmd/git-jci"

# Ensure required vars are present
: "${GOOS:?GOOS must be set}"
: "${GOARCH:?GOARCH must be set}"
: "${OUTPUT_BINARY_NAME:?OUTPUT_BINARY_NAME must be set}"

GOARM="${GOARM:-7}"

cd "${REPO_DIR}"

# Read the version from the VERSION file at the repo root.
VERSION="$(cat "${REPO_DIR}/VERSION" | tr -d '[:space:]')"
echo "[${OUTPUT_BINARY_NAME}] Version: ${VERSION}"

echo "[${OUTPUT_BINARY_NAME}] Downloading dependencies..."
go mod download

echo "[${OUTPUT_BINARY_NAME}] Building for GOOS=${GOOS} GOARCH=${GOARCH} GOARM=${GOARM}..."
mkdir -p "${OUTPUT_DIR}"

CGO_ENABLED=0 \
GOOS="${GOOS}" \
GOARCH="${GOARCH}" \
GOARM="${GOARM}" \
go build \
    -buildvcs=false \
    -tags "netgo osusergo" \
    -ldflags "-s -w -X main.version=${VERSION} -extldflags '-static'" \
    -o "${OUTPUT_DIR}/${OUTPUT_BINARY_NAME}" \
    "${ENTRY_POINT}"

echo "[${OUTPUT_BINARY_NAME}] Binary built successfully: ${OUTPUT_DIR}/${OUTPUT_BINARY_NAME}"
