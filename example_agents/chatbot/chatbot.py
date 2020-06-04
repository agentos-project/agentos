import agentos
from collections import deque
from env import MultiChatEnv
from env_utils import CommandLineClient
from numpy import random as np_random


class ChatBot(agentos.Agent):
    def __init__(self, env):
        super().__init__(env)
        self.memory = deque(maxlen=2048)
        self.reply_flag = False

    def step(self):
        msg = ''
        if self.reply_flag:
            msg = np_random.choice(self.memory)
            self.reply_flag = False
        obs, reward, done, _ = self.env.step(msg)
        if obs:
            self.memory.append(obs)
            self.reply_flag = True


env_generator = MultiChatEnv()
agentos.run_agent(ChatBot, env_generator, 1, as_thread=True)

cmd_line = CommandLineClient(env_generator())
cmd_line.start()
