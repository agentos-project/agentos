class BasicDataset:
    def __init__(self):
        self.transitions = []

    def add(self, old_obs, action, new_obs, reward, done):
        self.transitions.append((old_obs, action, new_obs, reward, done))
