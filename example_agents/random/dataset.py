# This file was auto-generated by `agentos init` on Feb 02, 2022 15:37:37.


class BasicDataset:
    def __init__(self):
        self.transitions = []

    def add(self, old_obs, action, new_obs, reward, done):
        self.transitions.append((old_obs, action, new_obs, reward, done))
