from agentos.behaviors import Behavior
import ray
from ray.rllib.agents.ppo import PPOTrainer, DEFAULT_CONFIG

class RayPPOBehavior(Behavior):
    def __init__(self, train_interval):
        """Init a ray PPO agent that has already been trained."""
        super().__init__()
        #TODO: make this idempotent so that it is ok if we add multiple ray behaviors to an Agent.
        ray.init()
        self.ray_agent = PPOTrainer(full_config, env=Nick2048)
        for i in range(1000):
            res = agent.train()
            print(res["episode_reward_mean"])
            # mlflow.log_metrics(res) #<-- MLflow can't handle nested dictionaries of metrics.
            mlflow.log_metric("episode_reward_mean", res["episode_reward_mean"], step=i)
