import agentos
from collections import deque
from env import MultiChatEnv
from env_utils import CommandLineClient
from numpy import random as np_random


class ChatBot(agentos.Agent):
    """A simple chatbot that speaks by parroting back things it has heard."""

    def __init__(self, env):
        super().__init__(env)
        self.memory = deque(maxlen=2048)
        self.reply_flag = False

    def advance(self):
        msg = ""
        if self.reply_flag:
            msg = np_random.choice(self.memory)
            self.reply_flag = False
        obs, reward, done, _ = self.env.step(msg)
        if obs:
            self.memory.append(obs)
            self.reply_flag = True


if __name__ == "__main__":
    env_generator = MultiChatEnv()
    agentos.run_agent(ChatBot, env_generator, 1, as_thread=True)

    cmd_line = CommandLineClient(env_generator())
    cmd_line.start()
