#!/bin/bash

set -eu

# https://stackoverflow.com/a/246128
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
ROOT_DIR="$SCRIPT_DIR/../.."

docker run \
    --rm \
    --name acme_test \
    --mount type=bind,source="$ROOT_DIR",target=/home/"$USER"/agentos \
    --mount type=bind,source="$HOME/.ssh",target=/home/"$USER"/.ssh \
    -id acme_r2d2