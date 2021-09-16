# Env that models a 1D corridor (you can move left or right)
# Goal is to get to the end (i.e. move right [length] number of times)
import agentos


class Corridor(agentos.Environment):

    # Check [env_config] for corridor length, default to 10
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not hasattr(self, "length"):
            self.length = 10
        self.reset()

    def step(self, action):
        assert action in [0, 1]
        if action == 0:
            self.position = max(self.position - 1, 0)
        else:
            self.position = min(self.position + 1, self.length)
        return (self.position, -1, self.done, {})

    @property
    def done(self):
        return self.position >= self.length

    @property
    def valid_actions(self):
        return [0, 1]

    def reset(self):
        self.position = 0
        return self.position


# Unit tests for Corridor
def run_tests():
    print("Testing Corridor...")
    env = Corridor(length=5)
    assert env.reset() == 0, "Initial position is 0"
    # Left step in initial position hits a wall and does not change state
    state, reward, done, info = env.step(0)
    assert state == 0
    assert reward == -1
    assert done is False
    # Right step should move agent closer to goal
    state, reward, done, info = env.step(1)
    assert state == 1
    assert reward == -1
    assert done is False
    # Left step returns agent to initial position
    state, reward, done, info = env.step(0)
    assert state == 0
    assert reward == -1
    assert done is False
    # Step to end of corridor
    state, reward, done, info = env.step(1)
    assert state == 1
    assert done is False
    state, reward, done, info = env.step(1)
    assert state == 2
    assert done is False
    state, reward, done, info = env.step(1)
    assert state == 3
    assert done is False
    state, reward, done, info = env.step(1)
    assert state == 4
    assert done is False
    state, reward, done, info = env.step(1)
    assert state == 5
    assert done is True
    print("Tests passed!")


if __name__ == "__main__":
    run_tests()