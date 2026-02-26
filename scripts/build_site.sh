#!/usr/bin/env bash

# Runs INSIDE the container.
# The host repo is mounted at /tmp/repo (read-write).
# Generated site is written to /tmp/repo/www_jci/public/releases.
set -euo pipefail

export REPO_DIR="/tmp/Jaypore CI"
export PUBLIC_DIR="${REPO_DIR}/www_jci/public"
export BUILD_DIR="/build"
export RELEASES_DIR="${PUBLIC_DIR}/releases"
export ASSETS_DIR="${PUBLIC_DIR}/assets"
cd "$REPO_DIR"

echo "==============="
env
echo "==============="

# Ensure output directory exists
mkdir -p "${RELEASES_DIR}"
mkdir -p "${BUILD_DIR}"

# Build a description line from the repo README for stagit
(
  cd "${REPO_DIR}"
  head README.md | grep '>' > description 2>/dev/null || echo "jci" > description
)

cp -r "${REPO_DIR}/bin" "${REPO_DIR}/binaries"
cp -r "${REPO_DIR}/bin" "${PUBLIC_DIR}/binaries"
(cd "${BUILD_DIR}" && pwd && stagit -u /releases/git "${REPO_DIR}")
cp -r "${BUILD_DIR}/." "${RELEASES_DIR}"

# Clean up the temporary description file
rm -f "${REPO_DIR}/description"
rm -rf "${REPO_DIR}/binaries"

cp "${ASSETS_DIR}/git.style.css" "${RELEASES_DIR}/style.css"
cp "${ASSETS_DIR}/logo.png" "${RELEASES_DIR}/logo.png"
cp "${ASSETS_DIR}/logo.png" "${RELEASES_DIR}/favicon.png"

echo "Site generated at ${RELEASES_DIR}"
