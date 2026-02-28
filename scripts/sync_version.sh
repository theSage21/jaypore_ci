#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

VERSION=$(cat $REPO_ROOT/VERSION)
INDEX_HTML="${REPO_ROOT}/www_jci/public/index.html"
sed -i "s|<span id=\"jci-version\">.*</span>|<span id=\"jci-version\">v${VERSION}</span>|" \
    "${INDEX_HTML}"
echo "  ✓ www_jci/public/index.html"
