#!/usr/bin/env bash
set -euo pipefail

: "${DOCKER_BUILDKIT:=1}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PUBLIC_DIR="${REPO_ROOT}/www_jci/public"
RELEASES_DIR="${PUBLIC_DIR}/releases"

IMAGE_NAME="jci-stagit"
CONTAINER_NAME="jci-stagit-builder"

# Ensure releases directory exists
mkdir -p "${RELEASES_DIR}"

# Build docker image with stagit (using inline Dockerfile via here-doc)
if ! docker image inspect "${IMAGE_NAME}">/dev/null 2>&1; then
  tmp_dir="$(mktemp -d)"
  mkdir -p "${tmp_dir}/repo" "${tmp_dir}/public_assets"
  cp -R "${REPO_ROOT}"/.[!.]* "${tmp_dir}/repo" 2>/dev/null || true
  cp -R "${REPO_ROOT}"/* "${tmp_dir}/repo"
  cp "${PUBLIC_DIR}/assets/logo.png" "${tmp_dir}/public_assets/logo.png"
  cp "${REPO_ROOT}/www_jci/Dockerfile" "${tmp_dir}/Dockerfile"
  docker build -t "${IMAGE_NAME}" "${tmp_dir}"
  rm -rf "${tmp_dir}"
fi

# Prepare context for stagit run
BUILD_CONTEXT="$(mktemp -d)"
mkdir -p "${BUILD_CONTEXT}/repo" "${BUILD_CONTEXT}/public_assets"
cp -a "${REPO_ROOT}/." "${BUILD_CONTEXT}/repo"
cp "${PUBLIC_DIR}/assets/logo.png" "${BUILD_CONTEXT}/public_assets/logo.png"
if [ -f "${REPO_ROOT}/ui/src/libs/git.style.css" ]; then
  cp "${REPO_ROOT}/ui/src/libs/git.style.css" "${BUILD_CONTEXT}/stagit_style.css"
else
  cat <<'EOF' > "${BUILD_CONTEXT}/stagit_style.css"
:root {font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;}
EOF
fi

docker run --rm \
  -v "${BUILD_CONTEXT}/repo:/tmp/repo" \
  -v "${PUBLIC_DIR}/assets/logo.png:/data/www_jci/public/assets/logo.png" \
  -v "${RELEASES_DIR}:/gitrepo" \
  "${IMAGE_NAME}"

rm -rf "${BUILD_CONTEXT}"

echo "Releases site generated at ${RELEASES_DIR}"
