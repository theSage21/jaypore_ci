#!/bin/bash
# Jaypore CI — Build Docusaurus (or simple static site) and publish to S3.
#
# Environment (provided by Jaypore CI):
#   JCI_COMMIT      — current commit SHA
#   JCI_REPO_ROOT   — repository root path
#   JCI_OUTPUT_DIR  — directory for CI artifacts (cwd at start)
#
# Optional environment:
#   AWS_ACCESS_KEY_ID      — AWS credentials for S3 deploy
#   AWS_SECRET_ACCESS_KEY  — AWS credentials for S3 deploy
#   S3_BUCKET              — target bucket  (e.g. s3://my-docs-bucket)
#   AWS_REGION             — AWS region      (default: us-east-1)

set -euo pipefail

PROJECT_DIR="$JCI_REPO_ROOT/14-docusaurus-s3"
BUILD_LOG="$JCI_OUTPUT_DIR/build.log"

# ── Helpers ──────────────────────────────────────────────────────────
log()  { echo "[jci] $*" | tee -a "$BUILD_LOG"; }

# Start the build log
echo "=== Build log — $(date -u '+%Y-%m-%dT%H:%M:%SZ') ===" > "$BUILD_LOG"
log "Commit : ${JCI_COMMIT:-unknown}"
log "Project: $PROJECT_DIR"
log ""

cd "$PROJECT_DIR"

# ── 1. Build ─────────────────────────────────────────────────────────
if [ -f package.json ] && grep -q '"docusaurus"' package.json 2>/dev/null; then
    log "Detected Docusaurus project — running npm build"
    npm ci              2>&1 | tee -a "$BUILD_LOG"
    npm run build       2>&1 | tee -a "$BUILD_LOG"
    SITE_DIR="$PROJECT_DIR/build"
else
    log "No Docusaurus project found — using simple build.sh fallback"
    bash build.sh       2>&1 | tee -a "$BUILD_LOG"
    SITE_DIR="$PROJECT_DIR/build"
fi

# ── 2. Copy build output to CI artifacts ─────────────────────────────
log ""
log "Copying build output to \$JCI_OUTPUT_DIR/build/"
mkdir -p "$JCI_OUTPUT_DIR/build"
cp -r "$SITE_DIR"/* "$JCI_OUTPUT_DIR/build/"
log "Artifact files:"
ls -lR "$JCI_OUTPUT_DIR/build/" 2>&1 | tee -a "$BUILD_LOG"

# ── 3. Deploy to S3 (optional) ───────────────────────────────────────
log ""
if [ -n "${AWS_ACCESS_KEY_ID:-}" ] && [ -n "${S3_BUCKET:-}" ]; then
    AWS_REGION="${AWS_REGION:-us-east-1}"
    log "Deploying to $S3_BUCKET (region: $AWS_REGION)"
    aws s3 sync "$JCI_OUTPUT_DIR/build/" "$S3_BUCKET" \
        --region "$AWS_REGION" \
        --delete \
        2>&1 | tee -a "$BUILD_LOG"
    log "S3 deploy complete."
else
    log "Skipping S3 deploy: AWS credentials or S3_BUCKET not set"
fi

# ── 4. Summary ───────────────────────────────────────────────────────
log ""
log "========================================"
log "  Build & deploy finished successfully"
log "  Pages : $(find "$JCI_OUTPUT_DIR/build" -name '*.html' | wc -l)"
log "  Log   : \$JCI_OUTPUT_DIR/build.log"
log "========================================"
