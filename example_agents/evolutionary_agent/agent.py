"""This agent's simple Evolutionary Strategy solves CartPole surprisingly fast.

This strategy was discussed in https://arxiv.org/pdf/1712.06567.pdf
This agent can be run with the agentos CLI using:
    $ pip install -r requirements.txt
    $ agentos run agent.py gym.envs.classic_control.CartPoleEnv
"""
import copy

import gym
import numpy as np
from gym.envs.classic_control import CartPoleEnv
from tensorflow import keras

import agentos


class TFPolicy(agentos.Policy):
    def __init__(self, tf_model):
        self.tf_model = tf_model
        self.observation_space = CartPoleEnv().observation_space
        self.action_space = CartPoleEnv().action_space

    def compute_action(self, obs):
        assert self.observation_space.contains(obs), obs
        action = self.tf_model(np.array(obs)[np.newaxis])
        env_compatible_action = int(round(action.numpy()[0][0]))
        assert self.action_space.contains(
            env_compatible_action
        ), env_compatible_action
        return env_compatible_action

    def __deepcopy__(self, memo):
        return TFPolicy(keras.models.clone_model(self.tf_model))


class EvolutionaryAgent(agentos.Runnable):
    def __init__(
        self,
        env_class,
        population_size=10,
        num_simulations=3,
        survival_rate=0.1,
        max_steps=200,
    ):
        self.env = env_class()
        assert isinstance(self.env, gym.envs.classic_control.CartPoleEnv)
        self.population = [
            TFPolicy(m) for m in self.init_models(population_size)
        ]
        self.num_simulations = num_simulations
        self.survival_rate = survival_rate
        self.max_steps = max_steps
        self.iter_count = 0
        print("initialized population of models")

    def advance(self):
        self.train()
        best_policy = self.population[-1]  # Population sorted worst to best.
        policy_eval = agentos.rollout(
            best_policy, self.env.__class__, max_steps=self.max_steps
        )
        self.iter_count += 1
        print(
            f"Agent iter {self.iter_count} returns: {sum(policy_eval.rewards)}"
        )

    def train(self):
        """Improve policy via one generation of a simple evolution strategy."""
        carry_over_best = self.population[-1]
        population_cutoff = -int(len(self.population) * self.survival_rate)
        top_performers = self.population[population_cutoff:]
        reproduction_rate = int(1 / self.survival_rate)
        evolved_population = []
        for p in top_performers:
            for _ in range(reproduction_rate):
                new_p = copy.deepcopy(p)
                for i in range(len(p.tf_model.weights)):
                    noise = np.random.normal(
                        np.mean(p.tf_model.weights[i].numpy()),
                        max(np.std(p.tf_model.weights[i].numpy()), 0.01),
                        p.tf_model.weights[i].shape[0],
                    )
                    new_p.tf_model.weights[i] = (
                        new_p.tf_model.weights[i] + noise
                    )
                evolved_population.append(new_p)

        def avg_return(policy):
            results = agentos.rollouts(
                policy,
                self.env.__class__,
                self.num_simulations,
                max_steps=self.max_steps,
            )
            rollout_returns = [sum(x.rewards) for x in results]
            return np.mean(rollout_returns)

        self.population = sorted(
            evolved_population[:-1] + [carry_over_best], key=avg_return
        )

    def init_models(self, num_models):
        assert isinstance(
            self.env.observation_space, gym.spaces.Box
        ) and isinstance(self.env.action_space, gym.spaces.Discrete)
        print(
            "setting up Keras NNs with input_shape "
            f"{self.env.observation_space.shape}"
        )
        return [
            keras.Sequential(
                [
                    keras.layers.Dense(
                        4,
                        activation="relu",
                        input_shape=self.env.observation_space.shape,
                    ),
                    keras.layers.Dense(1, activation="sigmoid"),
                ]
            )
            for _ in range(num_models)
        ]
