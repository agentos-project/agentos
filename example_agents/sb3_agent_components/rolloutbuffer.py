import agentos


class RolloutBuffer(agentos.Dataset):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.experience = []

    def add(self, prev_obs, action, curr_obs, reward, done, info):
        self.experience.append(
            (prev_obs, action, curr_obs, reward, done, info)
        )
