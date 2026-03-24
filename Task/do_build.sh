#!/usr/bin/env bash
set -e

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
DOCKER_IMAGE_TAG="hecktor2026-task"

if [ "$#" -eq 1 ]; then
    DOCKER_IMAGE_TAG="$1"
fi

docker build "$SCRIPT_DIR" \
  --platform=linux/amd64 \
  --tag "$DOCKER_IMAGE_TAG" 2>&1
