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

# ---------------------------------------------------------------------------
# Helper: build one binary inside its own Docker container.
#
# Usage: build_target <GOOS> <GOARCH> <OUTPUT_BINARY_NAME> [GOARM]
#
# Each invocation is fire-and-forget (&); collect PIDs for later wait.
# ---------------------------------------------------------------------------
PIDS=()
TARGETS=()  # human-readable label per job, index-matched to PIDS

build_target() {
    local goos="$1"
    local goarch="$2"
    local output_name="$3"
    local goarm="${4:-7}"   # only meaningful when goarch=arm

    local label="${goos}/${goarch}"
    [[ "${goarch}" == "arm" ]] && label="${label}v${goarm}"

    echo "[build] Spawning container for ${label} → bin/${output_name}"

    docker run --rm \
        -v "$PWD:/tmp/repo" \
        -e GOOS="${goos}" \
        -e GOARCH="${goarch}" \
        -e GOARM="${goarm}" \
        -e OUTPUT_BINARY_NAME="${output_name}" \
        golang:1.25 \
        "/tmp/repo/scripts/build_binary.sh" \
        &

    PIDS+=($!)
    TARGETS+=("${label} → bin/${output_name}")
}

# ---------------------------------------------------------------------------
# Step 1: Build Docker image (sequential — other steps depend on it)
# ---------------------------------------------------------------------------
echo "--- Step 1: Building Docker image via scripts/build_image.sh ---"
scripts/build_image.sh
echo ""

# ---------------------------------------------------------------------------
# Step 2: Cross-compile binaries in parallel
#
# Targets:
#   Linux   amd64       git-jci-linux-amd64
#   Linux   arm64       git-jci-linux-arm64
#   Linux   arm (v7)    git-jci-linux-armv7
#   Windows amd64       git-jci-windows-amd64.exe
#   Windows arm64       git-jci-windows-arm64.exe
# ---------------------------------------------------------------------------
echo "--- Step 2: Building binaries in parallel ---"
mkdir -p bin

build_target linux  amd64 git-jci-linux-amd64
build_target linux  arm64 git-jci-linux-arm64
build_target linux  arm   git-jci-linux-armv7   7
build_target windows amd64 git-jci-windows-amd64.exe
build_target windows arm64 git-jci-windows-arm64.exe

echo ""
echo "Waiting for all build containers to finish..."
echo ""

# ---------------------------------------------------------------------------
# Collect results — report each job individually so failures are obvious
# ---------------------------------------------------------------------------
FAILED=0
for i in "${!PIDS[@]}"; do
    pid="${PIDS[$i]}"
    label="${TARGETS[$i]}"
    if wait "${pid}"; then
        echo "[OK]   ${label}"
    else
        echo "[FAIL] ${label}"
        FAILED=$((FAILED + 1))
    fi
done

echo ""
if [[ "${FAILED}" -gt 0 ]]; then
    echo "${FAILED} build(s) failed. See output above for details."
    exit 1
fi

echo "All binaries built successfully:"
ls -lh bin/git-jci-*
echo ""

# ---------------------------------------------------------------------------
# Step 3: Build site (sequential — needs the binaries to be present)
# ---------------------------------------------------------------------------
echo "--- Step 3: Building site inside jci container ---"
docker run --rm -it -v "$PWD:/tmp/Jaypore CI" jci "/tmp/Jaypore CI/scripts/build_site.sh"
echo ""

echo "All steps completed successfully!"
