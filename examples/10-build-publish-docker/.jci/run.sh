#!/bin/bash
set -euo pipefail

# Jaypore CI run script
# ---------------------
# This script is executed by Jaypore CI.
#
# Available environment variables:
#   JCI_COMMIT      - The git commit being tested
#   JCI_REPO_ROOT   - Absolute path to the repository root
#   JCI_OUTPUT_DIR  - Directory for CI artifacts (cwd at start)
#
# Optional environment variables:
#   DOCKER_REGISTRY  - Registry to push to (e.g. registry.example.com)
#   DOCKER_USERNAME  - Registry login username
#   DOCKER_PASSWORD  - Registry login password
#
# Any files written to JCI_OUTPUT_DIR become CI artifacts.

echo "=== Jaypore CI: Build & Publish Docker Image ==="
echo "Commit : $JCI_COMMIT"
echo "Repo   : $JCI_REPO_ROOT"
echo "Output : $JCI_OUTPUT_DIR"
echo

cd "$JCI_REPO_ROOT"

IMAGE_NAME="mysite"
SHORT_SHA=$(echo "$JCI_COMMIT" | cut -c1-12)
TAG_COMMIT="${IMAGE_NAME}:${SHORT_SHA}"
TAG_LATEST="${IMAGE_NAME}:latest"

# If a registry is configured, prefix the image name
if [ -n "${DOCKER_REGISTRY:-}" ]; then
    TAG_COMMIT="${DOCKER_REGISTRY}/${TAG_COMMIT}"
    TAG_LATEST="${DOCKER_REGISTRY}/${TAG_LATEST}"
fi

echo "Image tags:"
echo "  $TAG_COMMIT"
echo "  $TAG_LATEST"
echo

# ---- 1. Build the Docker image ----
echo "--- Building Docker image ---"
docker build \
    -f 10-build-publish-docker/Dockerfile \
    -t "$TAG_COMMIT" \
    -t "$TAG_LATEST" \
    . \
    2>&1 | tee "$JCI_OUTPUT_DIR/docker-build.log"

echo
echo "Build complete."
echo

# ---- 2. Run tests inside the container ----
echo "--- Running tests inside the container ---"
docker run --rm "$TAG_COMMIT" \
    python3 manage.py test core --verbosity=2 \
    2>&1 | tee "$JCI_OUTPUT_DIR/docker-test.log"

echo
echo "Tests passed."
echo

# ---- 3. Save image metadata ----
echo "--- Saving image info ---"
docker inspect "$TAG_COMMIT" > "$JCI_OUTPUT_DIR/image-inspect.json"
docker images --filter "reference=${IMAGE_NAME}" \
    --format 'table {{.Repository}}\t{{.Tag}}\t{{.ID}}\t{{.Size}}' \
    | tee "$JCI_OUTPUT_DIR/image-info.txt"
echo

# ---- 4. Push to registry (if configured) ----
if [ -n "${DOCKER_REGISTRY:-}" ]; then
    echo "--- Pushing to $DOCKER_REGISTRY ---"

    if [ -n "${DOCKER_USERNAME:-}" ] && [ -n "${DOCKER_PASSWORD:-}" ]; then
        echo "$DOCKER_PASSWORD" | docker login "$DOCKER_REGISTRY" \
            -u "$DOCKER_USERNAME" --password-stdin \
            2>&1 | tee -a "$JCI_OUTPUT_DIR/docker-push.log"
    fi

    docker push "$TAG_COMMIT" 2>&1 | tee -a "$JCI_OUTPUT_DIR/docker-push.log"
    docker push "$TAG_LATEST" 2>&1 | tee -a "$JCI_OUTPUT_DIR/docker-push.log"

    echo
    echo "Push complete."
else
    echo "--- DOCKER_REGISTRY not set, skipping push ---"
fi

echo

# ---- 5. Summary ----
echo "=== Summary ==="
echo "Image          : $TAG_COMMIT"
echo "Build log      : docker-build.log"
echo "Test log       : docker-test.log"
echo "Image metadata : image-inspect.json"
echo "Image info     : image-info.txt"
[ -n "${DOCKER_REGISTRY:-}" ] && echo "Push log       : docker-push.log"
echo "All artifacts are in $JCI_OUTPUT_DIR"
