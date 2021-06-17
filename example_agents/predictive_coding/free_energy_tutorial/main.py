"""
Based on https://sciencedirect.com/science/article/pii/S0022249615000759
by Rafal Bogacz.
"""
import agentos
from collections import defaultdict
from decimal import Decimal
import gym
import matplotlib.pyplot as plt
import numpy as np

np.random.seed(47)

env_stats = defaultdict(list)
mouse_stats = defaultdict(list)


class CookieSensorEnv(gym.Env):
    """Simple environment representing a cookie viewed via a light sensor.

    CookieSensorEnv represents a world that has a cookie and a sensor in it.
    In this world, only one cookie exists at a time, and that cookie
    reflects light as a function of its size.
    An agent senses the light bouncing off the cookie by calling step(),
    which returns a scalar representing light intensity.
    Cookie size is random, determined by a normal distribution with
    with parameters specified via __init__() or left to their default values.
    Sensor output is also random, specified by a 2nd normal distribution,
    with mean set to a function g(x) of the output of the cookie_size
    distribution, and variance specified via __init__(). To summarize the flow:

    0) an agent calls step() on this env, receives a sample of light_intensity
       generated per the following:

    1) a cookie is generated with a random size per normal dist. with user
       provided mean and variance.

    2) size transformed and used as light_mean via:
       light_mean = g(size) = size^2

    3) a sensor reading is generated and returned with random intensity per
       normal distribution using light_mean as mean and user provided variance.
    """

    def __init__(
        self,
        cookie_size_mean=3,
        cookie_size_var=1,
        area_to_light_fn=lambda x: x * x,
        light_intensity_var=1,
        new_cookie_period=20000,
    ):
        self.cookie_size_mean = Decimal(cookie_size_mean)
        self.cookie_size_var = Decimal(cookie_size_var)
        self.area_to_light_fn = area_to_light_fn
        self.light_intensity_var = Decimal(light_intensity_var)
        self.new_cookie_period = new_cookie_period
        self.reset()

    def reset(self):
        self.cookie_period_counter = 0
        self.last_cookie_size_sample = None
        self.last_light_intensity_mean = 0
        self.last_light_intensity_sample = None

    def step(self, action):
        """Observe the cookie in the world. Actions not supported yet.

        :param action: right now, no actions accepted, i.e. action must be
        None.

        :returns: light intensity at this timestep.
        """
        assert not action
        if (
            self.last_light_intensity_sample is None
            or self.cookie_period_counter >= self.new_cookie_period
        ):
            self.cookie_period_counter = 0
            self.last_cookie_size_sample = np.random.normal(
                self.cookie_size_mean, self.cookie_size_var
            )
            self.last_light_intensity_mean = self.area_to_light_fn(
                self.last_cookie_size_sample
            )
            self.last_light_intensity_sample = Decimal(
                np.random.normal(
                    self.last_light_intensity_mean, self.light_intensity_var
                )
            )
        self.cookie_period_counter += 1

        # env_stats["cookie_size_mean"].append(self.cookie_size_mean)
        # env_stats["cookie_size_var"].append(self.cookie_size_var)
        env_stats["last_cookie_size_sample"].append(
            self.last_cookie_size_sample
        )
        # env_stats["last_light_intensity_mean"].append(self.last_light_intensity_mean)
        env_stats["last_light_intensity_sample"].append(
            self.last_light_intensity_sample
        )
        return self.last_light_intensity_sample, 0, False, {}


class Mouse(agentos.Agent):
    """
    The mouse brain has variables to track its beliefs about the world.
    Beliefs consist of estimates of the parameters in the environment,
    which from the mouses point of view are latent variables that must
    be learned through repeated experience of the end result of the physical
    processes, namely the output of the mouses noisy light sensor (its eye).

    These variables fall roughly into two categories:
    1) beliefs that can be updated quickly in response to sensory input
       such as the belief that a recently viewed cookie was 2cm.
       These are analogous to the near-realtime changes to the output
       of a Tensorflow DNN when new inputs are applied to it.
    2) beliefs that evolve more slowly over time which in the brain
       are implemented using synaptic plasticity, analogous to the way
       params are updated via backprop in TensorFlow.
    """

    def __init__(self, env):
        super().__init__(environment=env)
        self.light_intensity_error_belief = Decimal(0)  # epsilon_u
        self.cookie_size_error_belief = Decimal(0)  # epsilon_p
        self.cookie_size_belief = Decimal(0)  # phi

        self.cookie_size_var_belief = Decimal(1)  # sigma_p
        self.light_intensity_var_belief = Decimal(1)  # sigma_u
        self.cookie_size_mean_belief = Decimal(3)  # v_p
        self.area_to_light_belief_fn = lambda x: x ** Decimal(2)  # g()
        self.area_to_light_deriv_belief_fn = lambda x: Decimal(2) * x  # g'()

        self.step_size = Decimal(0.05)
        self.step_count = 0

    def advance(self):
        """This agent will never stop on it's own"""
        obs, reward, done, _ = self.environment.step("")
        self.update_world_model(obs)
        self.step_count += 1
        return False

    def update_world_model(self, obs):
        try:
            # update neural network node vals (belief type 1)
            epsilon_p = (
                self.cookie_size_belief - self.cookie_size_mean_belief
            ) / self.cookie_size_var_belief
            epsilon_u = (
                obs - self.area_to_light_belief_fn(self.cookie_size_belief)
            ) / self.light_intensity_var_belief

            dF_dPhi = (
                epsilon_u
                * self.area_to_light_deriv_belief_fn(self.cookie_size_belief)
                - epsilon_p
            )
            self.cookie_size_belief += self.step_size * dF_dPhi

            # update neural network synaptic weights (belief type 2)
            dF_dSigma_p = Decimal(0.5) * (
                epsilon_p ** 2 - 1 / self.cookie_size_var_belief
            )  # dF/dSigma_p
            dF_dSigma_u = Decimal(0.5) * (
                epsilon_u ** 2 - 1 / self.light_intensity_var_belief
            )  # dF/dSigma_u
            dF_dvp = epsilon_p  # dF/dv_p

            self.cookie_size_var_belief += self.step_size * dF_dSigma_p
            self.light_intensity_var_belief += self.step_size * dF_dSigma_u
            self.cookie_size_mean_belief += self.step_size * dF_dvp

            mouse_stats["belief_size"].append(self.cookie_size_belief)
            mouse_stats["belief_size_var"].append(self.cookie_size_var_belief)
            mouse_stats["belief_light_var"].append(
                self.light_intensity_var_belief
            )
            mouse_stats["belief_size_mean"].append(
                self.cookie_size_mean_belief
            )
        except Exception:
            return None


if __name__ == "__main__":
    """Create a mouse agent and see what it learns as its best guess of the
    size of cookies it is seeing."""
    import argparse

    parser = argparse.ArgumentParser(
        description=(
            "Run a MouseAgent that learns by looking at cookies "
            "using Friston's Free Energy principle. This agent "
            "is an implementation of the tutorial by Rafal Bogacz at "
            "https://sciencedirect.com/science/article/pii/S0022249615000759"
        )
    )
    parser.add_argument("--max-iters", type=int, default=150)
    parser.add_argument("-p", "--plot-results", action="store_true")
    args = parser.parse_args()
    print(f"Running mouse agent  for {args.max_iters} steps...")
    print("------------------------------------------------")
    mouse = Mouse(CookieSensorEnv())
    agentos.run_agent(mouse, max_iters=args.max_iters)
    if args.plot_results:
        plt.figure(figsize=(15, 10))
        for k, v in mouse_stats.items():
            if k != "belief_light_var" and k != "belief_size_var":
                plt.plot(v, label=k)

        for k, v in env_stats.items():
            plt.plot(v, label=k)

        plt.legend()
        plt.title("Mouse beliefs over time")
        plt.show()
