## AgentOS Basic Agent

This directory contains a basic agent that was automatically created by running
the `agentos init` command.

### Overview

This agent attempts to walk down a 1D corridor (i.e. the agent can only walk
left or right) consisting of five rooms.  The agent starts in the far left room
of the corridor and successfully completes an episode when it enters the far
right room.  At each timestep, the agent chooses randomly to move into the room
to its left or right.

### To Run

To run this agent, execute the following command in the agent directory:

```
agentos run agent
```

This command runs the default agent entry point (`run_episodes()`) and will
print out information about the agent's performance.

To adjust the number of episodes run by this agent, you can pass the
`num_episodes` argument like so:

```
agentos run agent -A num_episodes=10
```

### Structure

This agent is composed of a number of Components and supporting files that are
used by the Python Component System and AgentOS to instantiate and run the
agent:

* `components.yaml` - A registry file that describes each Component in the
  agent system and how they depend on each other.

* `agent.py` - A Component that contains the core agent implementation and
  logic to rollout various episodes in the environment.

* `dataset.py` - A Component that records each transition the agent makes in
  the environment to enable analysis of the agent's performance.

* `environment.py` - The environment Component that simulates the 1D corridor.

* `policy.py` - This Component contains the random policy that the agent uses
  to decide what action to take in the environment at each timestep. 

* `requirements.txt` - A text file listing the external pip dependencies of
  this agent.  In this case, the file is empty because no external dependencies
  are required to run this agent.
