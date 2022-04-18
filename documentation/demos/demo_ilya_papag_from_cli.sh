#!/bin/bash
cd "$(dirname "$0")"  # cd to dir that this shell script is in.
cd ../..  # cd to agentos root
PAPAG_DIR=./example_agents/papag

agentos freeze agent --registry-file $PAPAG_DIR/components.yaml > /tmp/papag-components.yaml
agentos run agent --registry-file /tmp/papag-components.yaml --entry-point learn --arg-set-file $PAPAG_DIR/a2c_pong_args.yaml > output.txt
AGENT_RUN_ID=$(grep -Eo 'AgentRun ([0-9,a-f]+)' output.txt|grep -o ' [0-9,a-f]\+')
USE_LOCAL_SERVER=True agentos publish-run $AGENT_RUN_ID