import agentos
from collections import deque
from example_agents.chatbot.env import MultiChatEnv
from example_agents.chatbot.env_utils import CommandLineClient
from numpy import random as np_random


class ChatBot(agentos.Runnable):
    """A simple chatbot that speaks by parroting back things it has heard."""

    def __init__(self, env_class=None):
        super().__init__()
        self.memory = deque(maxlen=2048)
        self.reply_flag = False
        if env_class:
            self.env = env_class()

    def init(self):
        self.env = self.env_class()

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
    chat_bot = ChatBot(env_generator)
    chat_bot.run(1, as_thread=True)

    cmd_line = CommandLineClient(env_generator())
    cmd_line.start()
