***********
Quick Start
***********

AgentOS is a **command line interface and Python developer API** for building,
running, and sharing flexible learning agents.

AgentOS proposes a standard minimal architecture for a learning agent, and
includes an API and example agent implementations for developers. The benefits
of standard agent-related abstractions include:

  * It is easier and faster to build agents since creators can focus on what is
    important to them without having to rewrite the parts that are less
    interesting but necessary in all agents (e.g., code to manage long running
    processes, parallelism, etc.).

  * A simple open standard makes it easier to talk about agents, share agent
    code, and quickly understand agents created by others. These benefits are
    similar to those of the OpenAI Gym standard API for agent environments
    (`gym.Env <https://github.com/openai/gym/blob/master/gym/core.py>`_).

The best way to understand AgentOS is to use it, so let’s install agentos and
write a simple agent in Python that behaves randomly. Installation is easy::

  $ pip install agentos

Writing a trivial agent is also easy::

  # Save this code in ./simple_agent.py
  import agentos

  class SimpleAgent(agentos.Agent):
      def advance(self):
          obs, reward, done, _ = self.env.step(self.env.action_space.sample())
          print(f"Took a random step, done = {done}.")
          return done

That’s it. Only one function is required to create an agent: ``advance()``. It
takes no arguments, has access to the agent’s environment, and returns a
boolean indicating if the agent is done.

Next let’s open a Python shell::

  $ python

... and then make an instance of our agent, pass its constructor an environment
(or env) class that the agent will interact with, and have the agent advance
(i.e., take one step of action) in that environment::

  >>> from simple_agent import SimpleAgent
  >>> from gym.envs.classic_control import CartPoleEnv
  >>> agent = SimpleAgent(CartPoleEnv)
  >>> agent.advance()
  Took a random step, done = False.
  False

The return value of ``False`` indicates that the agent is not yet “done”.
Notice that in this code we are using an OpenAI gym environment (more about
that below).

Let’s continue running our agent using a while loop until it is done::

  >>> done = False
  >>> while not done:
  >>>     done = agent.advance()
  Took a random step, done = False.
  …
  Took a random step, done = False.
  Took a random step, done = True.

The number of steps that the agent takes before being done is random since its
behavior is random (also the environment has randomness in it).

Now, instead of writing our own while loop, let’s run the agent in a Python
Thread using a convenience function that AgentOS provides which serves as an
Agent Runner::

  >>> from agentos import run_agent
  >>> run_agent(SimpleAgent, CartPoleEnv)
  Took a random step, done = False.
  …
  Took a random step, done = False.
  Took a random step, done = True.

Or we can run the agent via the AgentOS CLI::

  $ agentos run simple_agent.py gym.envs.classic_control.CartPoleEnv
  Took a random step, done = False.
  …
  Took a random step, done = False.
  Took a random step, done = True.

As an alternative to using our custom agent above, let’s go back into the
Python shell we opened above and use AgentOS’s RandomAgent::

  >>> from agentos.agents import RandomAgent
  >>> from agentos import run_agent
  >>> from gym.envs.classic_control import CartPoleEnv
  >>> run_agent(RandomAgent, CartPoleEnv)
  Took a random step, done = False.
  …
  Took a random step, done = False.
  Took a random step, done = True.

So far, we created and ran an agent, but what is an agent? Colloquially
speaking, it is an entity that can do things in its environment. In our
examples above, the agent is interacting with an instance of a simple physics
simulator provided by OpenAI Gym called `CartPole
<https://github.com/openai/gym/blob/master/gym/envs/classic_control/cartpole.py>`_
(if you're not familiar with gym, learn more about it `here
<https://gym.openai.com/>`_). In this environment, or world, the agent is
trying to balance a pole on a cart by nudging the cart to the left or right.
Because we made her a ``RandomAgent``, she is flipping a fair coin at each
timestep to decide which way to nudge the cart.

We have essentially created a simplistic being with some virtual sensors and
motors, and given her the ability to use them to interact with her world,
making observations and taking random actions in it. That’s a start, but note
that she’s not learning anything as she goes, nor behaving intelligently.
Still, you can start to get a sense of how to compose an agent with AgentOS.

In this simple example, you have interacted with some of AgentOS’s core
abstractions:

  * **Environment** - A stateful model of the world with a simple API. Used by
    an agent to make observations and take actions.

  * **Agent** - Encapsulates a decision-making process (and memory) that uses
    observations to decide what actions to take, which obviously can impact
    what observations will come next. An agent is also responsible for
    learning, i.e., improving itself over time through experience, e.g.,
    through RL algorithms.

  * **Agent Runner** - an abstraction responsible for running an agent with a
    given environment.


If you’re familiar with reinforcement learning (RL), both the environment and
agent concepts in AgentOS are derived from RL (more on this in
:doc:`/architecture_and_design`).
