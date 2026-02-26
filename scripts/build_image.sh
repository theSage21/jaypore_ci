#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

IMAGE_NAME="jci"

echo "Building Docker image '${IMAGE_NAME}'..."

# Write a minimal Dockerfile that installs the required tools.
# The repo is NOT baked into the image; it is mounted at runtime via -v.
docker build -t "${IMAGE_NAME}" - <<'DOCKERFILE'
FROM alpine:latest
RUN apk add --no-cache git ca-certificates stagit bash lowdown
WORKDIR /work
CMD ["/bin/sh"]
DOCKERFILE

echo "Image '${IMAGE_NAME}' built successfully."
