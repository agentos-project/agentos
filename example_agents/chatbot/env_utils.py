import numpy as np
from sys import stdin
import threading
import time


class RandomSpeaker(threading.Thread):
    """Says random things in an env."""
    def __init__(self, env):
        super().__init__()
        self.env = env
        self.done = False

    def run(self):
        """Run env loop in main thread to simulate a command line interface"""
        i = 0
        while True:
            rand_str = env.action_space.sample()
            print(f"RandomSpeaker saying a random string: {rand_str}")
            obs, reward, done, _ = self.env.step(rand_str)
            if any(map(lambda x: len(x) > 0, obs)):
                print(f"RandomSpeaker heard in the env: {obs}")
            if done or self.done:
                break
            sleep_time = np.random.randint(2, 5)
            time.sleep(sleep_time)
            i += 1


class EnvListener(threading.Thread):
    def __init__(self, env):
        super().__init__()
        self.env = env

    def run(self):
        print("Started env listener.")
        while True:
            msgs_out, _, _, _ = self.env.step("")
            if msgs_out:
                print("someone said:")
                for msg_out in msgs_out:
                    print(msg_out)
            time.sleep(1 / 40)


class CommandLineClient(threading.Thread):
    def __init__(self, env):
        super().__init__()
        self.env = env

    def run(self):
        print("Started command line listener.")
        while True:
            msg_in = stdin.readline()
            msgs_out, _, _, _ = self.env.step(msg_in)
            if msgs_out:
                print(msgs_out)


