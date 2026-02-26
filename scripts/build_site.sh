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

# Render README.md to HTML and replace the stagit-generated content
README_SRC="${REPO_DIR}/README.md"
README_DST="${RELEASES_DIR}/file/README.md.html"
if [[ -f "${README_SRC}" && -f "${README_DST}" ]]; then
  echo "Rendering README.md to HTML via lowdown..."
  README_RENDERED="$(mktemp)"
  lowdown -o "${README_RENDERED}" "${README_SRC}"
  echo "Injecting rendered README into ${README_DST}"
  README_TMP_OUTPUT="$(mktemp)"
  awk -v rendered="${README_RENDERED}" '
BEGIN {
  in_content = 0
  inserted = 0
}
{
  if (!inserted && $0 ~ /<div id="content">/) {
    print
    while ((getline line < rendered) > 0) {
      print line
    }
    close(rendered)
    in_content = 1
    inserted = 1
    next
  }
  if (in_content) {
    if ($0 ~ /<\/div>/) {
      print $0
      in_content = 0
    }
    next
  }
  print
}
END {
  if (!inserted) {
    print "Failed to inject rendered README: <div id=\"content\"> not found" > "/dev/stderr"
    exit 1
  }
}
' "${README_DST}" > "${README_TMP_OUTPUT}"
  mv "${README_TMP_OUTPUT}" "${README_DST}"
  rm -f "${README_RENDERED}"
fi

# Clean up the temporary description file
rm -f "${REPO_DIR}/description"
rm -rf "${REPO_DIR}/binaries"

cp "${ASSETS_DIR}/git.style.css" "${RELEASES_DIR}/style.css"
cp "${ASSETS_DIR}/logo.png" "${RELEASES_DIR}/logo.png"
cp "${ASSETS_DIR}/logo.png" "${RELEASES_DIR}/favicon.png"

echo "Site generated at ${RELEASES_DIR}"
