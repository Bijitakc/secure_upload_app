#!/usr/bin/env bash
set -euo pipefail

IMAGE_TAG="${1:?Usage: ./deploy.sh <image-tag>}"
IMAGE="ghcr.io/bijitakc/secure-upload-app:${IMAGE_TAG}"

echo "Pulling application image: ${IMAGE}"
docker pull "${IMAGE}"

echo "Image pulled successfully."