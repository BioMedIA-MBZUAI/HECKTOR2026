#!/usr/bin/env bash
set -e

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
DOCKER_IMAGE_TAG="hecktor2026-task"

if [ "$#" -eq 1 ]; then
    DOCKER_IMAGE_TAG="$1"
fi

echo "=+= (Re)build the container"
source "${SCRIPT_DIR}/do_build.sh" "$DOCKER_IMAGE_TAG"

build_timestamp=$( docker inspect --format='{{ .Created }}' "$DOCKER_IMAGE_TAG")

if [ -z "$build_timestamp" ]; then
    echo "Error: Failed to retrieve build information for container $DOCKER_IMAGE_TAG"
    exit 1
fi

formatted_build_info=$(echo $build_timestamp | sed -E 's/(.*)T(.*)\..*Z/\1_\2/' | sed 's/[-,:]/-/g')
output_filename="${SCRIPT_DIR}/${DOCKER_IMAGE_TAG}_${formatted_build_info}.tar.gz"

echo "Saving the container as ${output_filename}. This can take a while."
docker save "$DOCKER_IMAGE_TAG" | gzip -c > "$output_filename"

echo "Container saved as ${output_filename}"
