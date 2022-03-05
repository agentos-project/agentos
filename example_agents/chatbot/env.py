import string
import threading
from collections import deque
from secrets import token_bytes

import numpy as np
from gym import Space


class TextSpace(Space):
    """A Gym Space of possible strings with length up to max_chars."""

    def __init__(self, max_chars):
        super().__init__()
        self._max_chars = max_chars

    def sample(self):
        n = np.random.randint(1, self._max_chars)
        return "".join(
            np.random.choice(list(string.printable)) for x in range(n)
        )

    def contains(self, x):
        return isinstance(x, str) and len(x) <= self._max_chars


class MultiChatEnv:
    class ChatClientEnv:
        """A multi-agent chat environment.

        Actions are "speaking events", like a person speaking in a room.
        Passing an action value of None means say nothing at this timestep.

        States returned are the most recent N strings that have been said in
        the room env, i.e. things that an agent would hear if they were
        standing in a room and somebody said something in that room.

        The intention is that an agent usually would query the env in a loop
        constantly listening to what is said. They, can and usually will be
        silent most of the time they call step(), i.e. they will send a message
        with value None. Whenever they want to speak, they will send a message.

        This class conforms to as many of the gym.Env class requirements as
        possible, but varies where necessary to support multiple concurrent
        agents.
        """

        metadata = {"render.modes": ["ansi"]}

        def __init__(self, lock, agent_buffers, max_chars=1024):
            self.action_space = TextSpace(max_chars)
            self.observation_space = TextSpace(max_chars)

            self.lock = lock
            self.agent_id = token_bytes()
            self.agent_buffers = agent_buffers

            self.lock.acquire()
            self.agent_buffers[self.agent_id] = deque()
            self.lock.release()

        def reset(self):
            self.lock.acquire()
            print(
                "resetting agent buffer for thread %s " % threading.get_ident()
            )
            self.agent_buffers[self.agent_id] = deque()
            self.lock.release()
            return ""

        def step(self, msg):
            """Take a step in this environment.

            :param agent_id: the id agent calling step, provided when agent
            joins.

            :param msg: a string representing an agent saying something out
            loud in the environment for listeners (agents who have joined the
            env) to hear.

            :return observation: the buffer of strings that were said since the
            last time this agent called step(), all concatenated into a single
            string (separated by triple newlines), with oldest message first.
            """
            assert isinstance(msg, str)
            self.lock.acquire()
            if msg:
                for a_id, buffer in self.agent_buffers.items():
                    if a_id != self.agent_id:
                        buffer.append(msg)
            messages = "\n\n\n".join(self.agent_buffers[self.agent_id])
            self.agent_buffers[self.agent_id].clear()
            self.lock.release()
            return messages, len(messages), False, None

        def render(self, mode="ansi"):
            if mode == "ansi":
                return f"Agents Buffers: {self.agent_buffers}"
            else:
                super().render(mode=mode)  # just raise an exception

    def __init__(self, max_chars=1024):
        self.max_chars = max_chars
        self.lock = threading.Lock()  # shared lock for generated envs.
        self.agent_buffers = {}

    def __call__(self):
        """
        Each time this is called generate a new Env object, with all
        generated objects having the same shared underlying state.
        This makes it possible to have a agents interact with each
        using the standard single-agent style Env API.
        """
        return MultiChatEnv.ChatClientEnv(
            self.lock, self.agent_buffers, max_chars=self.max_chars
        )
