#!/bin/bash

# CI script for git-jci
# This runs in .jci/<commit>/ directory
# Environment variables available:
#   JCI_COMMIT     - Full commit hash
#   JCI_REPO_ROOT  - Repository root path
#   JCI_OUTPUT_DIR - Output directory (where artifacts should go)

set -eo pipefail

PIPELINE_NAME="JayporeCI"

# Summary bookkeeping --------------------------------------------------------
declare -a SUMMARY_PIPELINE=()
declare -a SUMMARY_BUILD_MATRIX=()

add_pipeline_summary() {
    local icon="$1"
    local label="$2"
    local ref="$3"
    SUMMARY_PIPELINE+=("${icon}|${label}|${ref}")
}

add_build_matrix_entry() {
    local icon="$1"
    local label="$2"
    local artifact="$3"
    SUMMARY_BUILD_MATRIX+=("${icon}|${label}|${artifact}")
}

print_summary() {
    local exit_code="$1"
    local commit="${JCI_COMMIT:-unknown}"
    local short_sha="${commit:0:12}"
    local overall_icon="🟢"
    [[ "${exit_code}" -ne 0 ]] && overall_icon="🔴"

    printf "╔ %s : %s       [sha %s]\n" "${overall_icon}" "${PIPELINE_NAME}" "${short_sha}"
    echo   "┏━ Pipeline"
    echo   "┃"

    if [[ ${#SUMMARY_PIPELINE[@]} -eq 0 ]]; then
        echo "┃ ⚪ : Pipeline exited before recording any steps"
    else
        for entry in "${SUMMARY_PIPELINE[@]}"; do
            IFS='|' read -r icon label ref <<< "${entry}"
            printf "┃ %s : %-20s [%s]\n" "${icon}" "${label}" "${ref}"
        done
    fi

    if [[ ${#SUMMARY_BUILD_MATRIX[@]} -gt 0 ]]; then
        echo "┃"
        printf "┃ 🧱 Build Matrix (%d targets)\n" "${#SUMMARY_BUILD_MATRIX[@]}"
        for entry in "${SUMMARY_BUILD_MATRIX[@]}"; do
            IFS='|' read -r icon label artifact <<< "${entry}"
            printf "┃    %s : %-18s [%s]\n" "${icon}" "${label}" "${artifact}"
        done
    fi

    echo "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛"
}

run_step() {
    local label="$1"
    local ref="$2"
    shift 2

    set +e
    "$@"
    local exit_code=$?
    set -e

    local icon="🟢"
    [[ ${exit_code} -ne 0 ]] && icon="🔴"
    add_pipeline_summary "${icon}" "${label}" "${ref}"

    return ${exit_code}
}

# ---------------------------------------------------------------------------
# Helper: build one binary inside its own Docker container.
#
# Usage: build_target <GOOS> <GOARCH> <OUTPUT_BINARY_NAME> [GOARM]
#
# Each invocation is fire-and-forget (&); collect PIDs for later wait.
# ---------------------------------------------------------------------------
PIDS=()
TARGETS=()        # human-readable label per job, index-matched to PIDS
TARGET_ARTIFACTS=()

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
    TARGETS+=("${label}")
    TARGET_ARTIFACTS+=("${output_name}")
}

trap 'print_summary $?' EXIT

echo "=== JCI CI Pipeline ==="
echo "Commit: ${JCI_COMMIT:0:12}"
echo ""

cd "$JCI_REPO_ROOT"

# ---------------------------------------------------------------------------
echo "--- Step 1: Updating code with latest VERSION ---"
run_step "Sync Version" "scripts/sync_version.sh" scripts/sync_version.sh
echo ""

# Step 2: Build Docker image (sequential — other steps depend on it)
# ---------------------------------------------------------------------------
echo "--- Step 2: Building Docker image via scripts/build_image.sh ---"
run_step "Build Image" "scripts/build_image.sh" scripts/build_image.sh
echo ""

# ---------------------------------------------------------------------------
# Step 3: Static analysis / sanity checks
# ---------------------------------------------------------------------------
echo "--- Step 3: Go formatting, vet, and build checks ---"
run_step "Go Lint" "scripts/check_go.sh" \
    docker run --rm -v "$PWD:/tmp/repo" -w /tmp/repo golang:1.25 \
        bash -c "/tmp/repo/scripts/check_go.sh"
echo ""

# ---------------------------------------------------------------------------
# Step 4: Cross-compile binaries in parallel
#
# Targets:
#   Linux   amd64       git-jci-linux-amd64
#   Linux   arm64       git-jci-linux-arm64
#   Linux   arm (v7)    git-jci-linux-armv7
#   Linux   386         git-jci-linux-386
#   Windows amd64       git-jci-windows-amd64.exe
#   Windows arm64       git-jci-windows-arm64.exe
# ---------------------------------------------------------------------------
echo "--- Step 4: Building binaries in parallel ---"
mkdir -p bin

build_target linux  amd64 git-jci-linux-amd64
build_target linux  arm64 git-jci-linux-arm64
build_target linux  arm   git-jci-linux-armv7   7
build_target linux  386   git-jci-linux-386
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
    artifact="${TARGET_ARTIFACTS[$i]}"
    if wait "${pid}"; then
        echo "[OK]   ${label} → bin/${artifact}"
        add_build_matrix_entry "🟢" "${label}" "${artifact}"
    else
        echo "[FAIL] ${label} → bin/${artifact}"
        add_build_matrix_entry "🔴" "${label}" "${artifact}"
        FAILED=$((FAILED + 1))
    fi
done

echo ""

total_targets=${#TARGETS[@]}
if [[ "${FAILED}" -gt 0 ]]; then
    echo "${FAILED} build(s) failed. See output above for details."
    add_pipeline_summary "🔴" "Build Matrix" "${FAILED}/${total_targets} failed"
    exit 1
fi

add_pipeline_summary "🟢" "Build Matrix" "${total_targets} targets"

echo "All binaries built successfully:"
ls -lh bin/git-jci-*
echo ""

# ---------------------------------------------------------------------------
# Step 5: Build site (sequential — needs the binaries to be present)
# ---------------------------------------------------------------------------
echo "--- Step 5: Building site inside jci container ---"
run_step "Docs & Site" "scripts/build_site.sh" \
    docker run --rm -v "$PWD:/tmp/Jaypore CI" jci "/tmp/Jaypore CI/scripts/build_site.sh"
echo ""

echo "All steps completed successfully!"
