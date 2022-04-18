#!/bin/bash
cd "$(dirname "$0")"  # cd to dir that this shell script is in.
cd ../..  # cd to agentos root
PAPAG_DIR=./example_agents/papag

agentos freeze agent --registry-file $PAPAG_DIR/components.yaml > /tmp/papag-components.yaml
agentos run agent --registry-file /tmp/papag-components.yaml --entry-point learn --arg-set-file $PAPAG_DIR/a2c_pong_args.yam