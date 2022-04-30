#!/bin/bash
set -xe
cd "$(dirname "$0")"  # cd to dir that this shell script is in.
cd ../..  # cd to agentos root
PAPAG_DIR=./example_agents/papag
SB3_DIR=./example_agents/sb3_agent

# Run PAPAG using Pong environment
agentos freeze agent --registry-file $PAPAG_DIR/components.yaml --output-file /tmp/papag-components.yaml
agentos run agent --registry-file /tmp/papag-components.yaml --entry-point learn --arg-set-file $PAPAG_DIR/ppo_pong_args.yaml > papag_output.txt
AGENT_RUN_ID=$(grep -Eo 'AgentRun ([0-9,a-f]+)' papag_output.txt|grep -o ' [0-9,a-f]\+')
USE_LOCAL_SERVER=True agentos publish-run $AGENT_RUN_ID

# Run SB3 using Pong environment
agentos freeze sb3_agent --registry-file $SB3_DIR/components.yaml --output-file /tmp/sb3-agent-components.yaml
agentos run sb3_agent --registry-file /tmp/sb3-agent-components.yaml --entry-point learn --arg-set-file $SB3_DIR/ppo_pong_args.yaml > sb3_output.txt
AGENT_RUN_ID=$(grep -Eo 'AgentRun ([0-9,a-f]+)' sb3_output.txt|grep -o ' [0-9,a-f]\+')
USE_LOCAL_SERVER=True agentos publish-run $AGENT_RUN_ID
