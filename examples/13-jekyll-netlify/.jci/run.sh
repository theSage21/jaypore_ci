#!/bin/bash
# ------------------------------------------------------------------
# Jaypore CI — Build Jekyll site and publish to Netlify
# ------------------------------------------------------------------
set -euo pipefail

LOG="${JCI_OUTPUT_DIR}/build.log"
exec > >(tee -a "$LOG") 2>&1

echo "=== Jekyll + Netlify CI ==="
echo "Commit  : ${JCI_COMMIT:-unknown}"
echo "Repo    : ${JCI_REPO_ROOT}"
echo "Output  : ${JCI_OUTPUT_DIR}"
echo

# ── 1. Navigate to site source ────────────────────────────────────
SITE_DIR="${JCI_REPO_ROOT}/13-jekyll-netlify/site"
cd "$SITE_DIR"
echo "Working directory: $(pwd)"

# ── 2. Ensure Jekyll is available ─────────────────────────────────
if ! command -v jekyll &>/dev/null; then
  echo "Jekyll not found — installing…"
  sudo gem install jekyll bundler --no-document 2>&1 || true
else
  echo "Jekyll found: $(jekyll --version)"
fi

# ── 3. Build ──────────────────────────────────────────────────────
DEST="${JCI_OUTPUT_DIR}/_site"
echo
echo "Building site → $DEST"
jekyll build --destination "$DEST"

if [ ! -d "$DEST" ]; then
  echo "ERROR: Build failed — $DEST does not exist."
  exit 1
fi

echo
echo "Build succeeded. Output files:"
find "$DEST" -type f | sort
echo

# ── 4. Deploy to Netlify (optional) ──────────────────────────────
if [ -n "${NETLIFY_AUTH_TOKEN:-}" ] && [ -n "${NETLIFY_SITE_ID:-}" ]; then
  echo "Deploying to Netlify (site ${NETLIFY_SITE_ID})…"

  ZIP_FILE="${JCI_OUTPUT_DIR}/_site.zip"
  (cd "$DEST" && zip -r "$ZIP_FILE" .)

  HTTP_CODE=$(curl -s -o "${JCI_OUTPUT_DIR}/netlify_response.json" \
    -w "%{http_code}" \
    -H "Content-Type: application/zip" \
    -H "Authorization: Bearer ${NETLIFY_AUTH_TOKEN}" \
    --data-binary @"$ZIP_FILE" \
    "https://api.netlify.com/api/v1/sites/${NETLIFY_SITE_ID}/deploys")

  if [ "$HTTP_CODE" -ge 200 ] && [ "$HTTP_CODE" -lt 300 ]; then
    echo "Netlify deploy succeeded (HTTP ${HTTP_CODE})."
  else
    echo "WARNING: Netlify deploy returned HTTP ${HTTP_CODE}."
    cat "${JCI_OUTPUT_DIR}/netlify_response.json"
    exit 1
  fi
else
  echo "Skipping Netlify deploy: NETLIFY_AUTH_TOKEN or NETLIFY_SITE_ID not set"
fi

# ── 5. Summary ───────────────────────────────────────────────────
echo
echo "=== Summary ==="
echo "Site source : $SITE_DIR"
echo "Build output: $DEST"
echo "Build log   : $LOG"
echo "Files built : $(find "$DEST" -type f | wc -l)"
echo "Done."
