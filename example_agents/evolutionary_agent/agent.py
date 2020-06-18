import agentos
import copy
import gym
from gym.envs.classic_control import CartPoleEnv
import numpy as np
from tensorflow import keras


class TFPolicy(agentos.Policy):
    def __init__(self, tf_model):
        self.tf_model = tf_model
        self.observation_space = CartPoleEnv().observation_space
        self.action_space = CartPoleEnv().action_space

    def compute_action(self, obs):
        assert self.observation_space.contains(obs), obs
        action = self.tf_model(np.array(obs)[np.newaxis])
        env_compatible_action = int(round(action.numpy()[0][0]))
        assert self.action_space.contains(env_compatible_action), env_compatible_action
        return env_compatible_action

    def __deepcopy__(self, memo):
        return TFPolicy(keras.models.clone_model(self.tf_model))


class EvolutionaryAgent(agentos.Agent):
    def __init__(self, env_class,
                 population_size=10,
                 num_simulations=3,
                 survival_rate=0.1,
                 max_env_steps = 200):
        super().__init__(env_class)
        assert isinstance(self.env, gym.envs.classic_control.CartPoleEnv)
        self.population = [TFPolicy(m) for m in self.init_models(population_size)]
        self.num_simulations = num_simulations
        self.survival_rate = survival_rate
        self.max_env_steps = max_env_steps
        self.steps_taken = 0
        print("initialized population of models")

    def step(self):
        self.train()
        obs = self.env.reset()
        ret = 0
        best_policy = self.population[-1]  # Population sorted worst to best.
        env_steps = 0
        while env_steps <= self.max_env_steps:
            action = best_policy.compute_action(obs)
            obs, reward, done, _ = self.env.step(action)
            ret += reward
            if done:
                break
            env_steps += 1
        self.steps_taken += 1
        print(f"Agent step {self.steps_taken} returning val: {ret, env_steps}")

    def train(self):
        """Improve policy via one generation of a simple evolution strategy."""
        carry_over_best = self.population[-1]
        top_performers = self.population[
                         -int(len(self.population) * self.survival_rate):]
        reproduction_rate = int(1/self.survival_rate)
        evolved_population = []
        for p in top_performers:
            for r in range(reproduction_rate):
                new_p = copy.deepcopy(p)
                for i in range(len(p.tf_model.weights)):
                    noise = np.random.normal(np.mean(p.tf_model.weights[i].numpy()),
                                             max(np.std(p.tf_model.weights[i].numpy()), 0.01),
                                             p.tf_model.weights[i].shape[0])
                    new_p.tf_model.weights[i] = new_p.tf_model.weights[i] + noise
                evolved_population.append(new_p)
        self.population = sorted(evolved_population[:-1] + [carry_over_best],
                                 key=lambda p: np.mean(self.simulate_episodes(p,
                                                                              self.num_simulations,
                                                                              max_steps=self.max_env_steps)))

    def init_models(self, num_models):
        assert isinstance(self.env.observation_space, gym.spaces.Box) and  \
               isinstance(self.env.action_space, gym.spaces.Discrete)
        print(f"setting up Keras NNs with input_shape {self.env.observation_space.shape}")
        return [
            keras.Sequential([
                keras.layers.Dense(4, activation='relu', input_shape=self.env.observation_space.shape),
                keras.layers.Dense(1, activation='sigmoid')
            ])
            for i in range(num_models)
        ]

