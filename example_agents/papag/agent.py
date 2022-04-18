import os
import time
from collections import deque

import a2c_ppo_acktr
import numpy as np
import torch
from a2c_ppo_acktr import utils
from a2c_ppo_acktr.algo import gail
from a2c_ppo_acktr.envs import make_vec_envs
from a2c_ppo_acktr.model import Policy
from a2c_ppo_acktr.storage import RolloutStorage

from pcs.component_run import active_component_run


class PAPAGAgent:
    """
    This example agent takes the majority of its code directly from Ilya
    Kostrikov's PyTorch A2C PPO, ACKTR, and GAIL (PAPAG) Repo's main.py.

    See here:

    https://github.com/ikostrikov/pytorch-a2c-ppo-acktr-gail
    """

    DEFAULT_ENTRY_POINT = "evaluate"

    def __init__(self, algo: str, env_name: str):
        self.algo = algo
        self.env_name = env_name
        model_name = self.get_model_name()
        self.model_input_run = self.PAPAGRun.get_last_logged_model_run(
            model_name
        )

    def evaluate(
        self,
        use_gail=False,
        gail_experts_dir="./gail_experts",
        gail_batch_size=128,
        gail_epoch=5,
        lr=0.0007,
        eps=1e-05,
        alpha=0.99,
        gamma=0.99,
        use_gae=False,
        gae_lambda=0.95,
        entropy_coef=0.01,
        value_loss_coef=0.5,
        max_grad_norm=0.5,
        seed=1,
        cuda_deterministic=False,
        num_processes=16,
        num_steps=5,
        ppo_epoch=4,
        num_mini_batch=32,
        clip_param=0.2,
        log_interval=10,
        save_interval=100,
        eval_interval=None,
        num_env_steps=10000000.0,
        log_dir="/tmp/gym/",
        save_dir="./trained_models/",
        no_cuda=False,
        use_proper_time_limits=False,
        recurrent_policy=False,
        use_linear_lr_decay=False,
        cuda=False,
    ):
        num_processes = int(num_processes)
        with self.PAPAGRun.evaluate_run(
            outer_run=active_component_run(self),
            model_input_run=self.model_input_run,
            agent_identifier=self.__component__.identifier,
            environment_identifier=self.__component__.identifier,
        ) as eval_run:
            torch.manual_seed(seed)
            torch.cuda.manual_seed_all(seed)

            if cuda and torch.cuda.is_available() and cuda_deterministic:
                torch.backends.cudnn.benchmark = False
                torch.backends.cudnn.deterministic = True

            log_dir = os.path.expanduser(log_dir)
            eval_log_dir = log_dir + "_eval"
            utils.cleanup_log_dir(log_dir)
            utils.cleanup_log_dir(eval_log_dir)

            torch.set_num_threads(1)
            device = torch.device("cuda:0" if cuda else "cpu")
            envs = make_vec_envs(
                self.env_name,
                seed,
                num_processes,
                gamma,
                log_dir,
                device,
                False,
            )
            model_name = self.get_model_name()
            actor_critic, obs_rms = self.get_actor_critic(
                model_name, eval_run, envs, recurrent_policy, device
            )

            # obs_rms = None
            # vec_normalized = utils.get_vec_normalize(envs)
            # if vec_normalized:
            #    obs_rms = vec_normalized.obs_rms
            eval_log_dir = log_dir + "_eval"
            papag_evaluate(
                actor_critic,
                obs_rms,
                self.env_name,
                seed,
                num_processes,
                eval_log_dir,
                device,
                eval_run,
            )

    def learn(
        self,
        use_gail=False,
        gail_experts_dir="./gail_experts",
        gail_batch_size=128,
        gail_epoch=5,
        lr=0.0007,
        eps=1e-05,
        alpha=0.99,
        gamma=0.99,
        use_gae=False,
        gae_lambda=0.95,
        entropy_coef=0.01,
        value_loss_coef=0.5,
        max_grad_norm=0.5,
        seed=1,
        cuda_deterministic=False,
        num_processes=16,
        num_steps=5,
        ppo_epoch=4,
        num_mini_batch=32,
        clip_param=0.2,
        log_interval=10,
        save_interval=100,
        eval_interval=None,
        num_env_steps=10000000.0,
        log_dir="/tmp/gym/",
        save_dir="./trained_models/",
        no_cuda=False,
        use_proper_time_limits=False,
        recurrent_policy=False,
        use_linear_lr_decay=False,
        cuda=False,
    ):
        num_processes = int(num_processes)
        with self.PAPAGRun.learn_run(
            outer_run=active_component_run(self),
            model_input_run=self.model_input_run,
            agent_identifier=self.__component__.identifier,
            environment_identifier=self.__component__.identifier,
        ) as learn_run:

            torch.manual_seed(seed)
            torch.cuda.manual_seed_all(seed)

            if cuda and torch.cuda.is_available() and cuda_deterministic:
                torch.backends.cudnn.benchmark = False
                torch.backends.cudnn.deterministic = True

            log_dir = os.path.expanduser(log_dir)
            eval_log_dir = log_dir + "_eval"
            utils.cleanup_log_dir(log_dir)
            utils.cleanup_log_dir(eval_log_dir)

            torch.set_num_threads(1)
            device = torch.device("cuda:0" if cuda else "cpu")

            envs = make_vec_envs(
                self.env_name,
                seed,
                num_processes,
                gamma,
                log_dir,
                device,
                False,
            )

            model_name = self.get_model_name()
            actor_critic, obs_rms = self.get_actor_critic(
                model_name, learn_run, envs, recurrent_policy, device
            )
            if self.algo == "a2c":
                agent = a2c_ppo_acktr.algo.A2C_ACKTR(
                    actor_critic,
                    value_loss_coef,
                    entropy_coef,
                    lr=lr,
                    eps=eps,
                    alpha=alpha,
                    max_grad_norm=max_grad_norm,
                )
            elif self.algo == "ppo":
                agent = a2c_ppo_acktr.algo.PPO(
                    actor_critic,
                    clip_param,
                    ppo_epoch,
                    num_mini_batch,
                    value_loss_coef,
                    entropy_coef,
                    lr=lr,
                    eps=eps,
                    max_grad_norm=max_grad_norm,
                )
            elif self.algo == "acktr":
                agent = a2c_ppo_acktr.algo.A2C_ACKTR(
                    actor_critic, value_loss_coef, entropy_coef, acktr=True
                )

            if use_gail:
                assert len(envs.observation_space.shape) == 1
                discr = gail.Discriminator(
                    envs.observation_space.shape[0]
                    + envs.action_space.shape[0],
                    100,
                    device,
                )
                file_name = os.path.join(
                    gail_experts_dir,
                    "trajs_{}.pt".format(self.env_name.split("-")[0].lower()),
                )

                expert_dataset = gail.ExpertDataset(
                    file_name, num_trajectories=4, subsample_frequency=20
                )
                drop_last = len(expert_dataset) > gail_batch_size
                gail_train_loader = torch.utils.data.DataLoader(
                    dataset=expert_dataset,
                    batch_size=gail_batch_size,
                    shuffle=True,
                    drop_last=drop_last,
                )

            rollouts = RolloutStorage(
                num_steps,
                num_processes,
                envs.observation_space.shape,
                envs.action_space,
                actor_critic.recurrent_hidden_state_size,
            )

            obs = envs.reset()
            rollouts.obs[0].copy_(obs)
            rollouts.to(device)

            episode_rewards = deque(maxlen=10)

            start = time.time()
            num_updates = int(num_env_steps) // num_steps // num_processes
            for j in range(num_updates):

                if use_linear_lr_decay:
                    # decrease learning rate linearly
                    utils.update_linear_schedule(
                        agent.optimizer,
                        j,
                        num_updates,
                        agent.optimizer.lr if self.algo == "acktr" else lr,
                    )

                for step in range(num_steps):
                    # Sample actions
                    with torch.no_grad():
                        (
                            value,
                            action,
                            action_log_prob,
                            recurrent_hidden_states,
                        ) = actor_critic.act(
                            rollouts.obs[step],
                            rollouts.recurrent_hidden_states[step],
                            rollouts.masks[step],
                        )

                    # Obser reward and next obs
                    obs, reward, done, infos = envs.step(action)

                    for info in infos:
                        if "episode" in info.keys():
                            episode_reward = info["episode"]["r"]
                            # TODO - is this actually steps?
                            episode_steps = info["episode"]["l"]
                            learn_run.add_episode_data(
                                episode_steps, episode_reward
                            )
                            episode_rewards.append(episode_reward)

                    # If done then clean the history of observations.
                    masks = torch.FloatTensor(
                        [[0.0] if done_ else [1.0] for done_ in done]
                    )
                    bad_masks = torch.FloatTensor(
                        [
                            [0.0] if "bad_transition" in info.keys() else [1.0]
                            for info in infos
                        ]
                    )
                    rollouts.insert(
                        obs,
                        recurrent_hidden_states,
                        action,
                        action_log_prob,
                        value,
                        reward,
                        masks,
                        bad_masks,
                    )

                with torch.no_grad():
                    next_value = actor_critic.get_value(
                        rollouts.obs[-1],
                        rollouts.recurrent_hidden_states[-1],
                        rollouts.masks[-1],
                    ).detach()

                if use_gail:
                    if j >= 10:
                        envs.venv.eval()

                    gail_epoch = gail_epoch
                    if j < 10:
                        gail_epoch = 100  # Warm up
                    for _ in range(gail_epoch):
                        discr.update(
                            gail_train_loader,
                            rollouts,
                            utils.get_vec_normalize(envs)._obfilt,
                        )

                    for step in range(num_steps):
                        rollouts.rewards[step] = discr.predict_reward(
                            rollouts.obs[step],
                            rollouts.actions[step],
                            gamma,
                            rollouts.masks[step],
                        )

                rollouts.compute_returns(
                    next_value,
                    use_gae,
                    gamma,
                    gae_lambda,
                    use_proper_time_limits,
                )

                value_loss, action_loss, dist_entropy = agent.update(rollouts)

                rollouts.after_update()

                # save for every interval-th episode or for the last epoch
                if j % save_interval == 0 or j == num_updates - 1:
                    learn_run.log_model(model_name, actor_critic, envs)

                if j % log_interval == 0 and len(episode_rewards) > 1:
                    total_num_steps = (j + 1) * num_processes * num_steps
                    end = time.time()
                    print(
                        f"Updates {j}, "
                        f"num timesteps {total_num_steps}, "
                        f"FPS {int(total_num_steps / (end-start))} \n "
                        f"Last {len(episode_rewards)} training episodes: "
                        f"mean/median reward {np.mean(episode_rewards):.1f}"
                        f"/{np.median(episode_rewards):.1f}, "
                        f"min/max reward {np.min(episode_rewards):.1f}"
                        f"/{np.max(episode_rewards):.1f}\n"
                    )

                if (
                    eval_interval is not None
                    and len(episode_rewards) > 1
                    and j % eval_interval == 0
                ):
                    obs_rms = utils.get_vec_normalize(envs).obs_rms
                    papag_evaluate(
                        actor_critic,
                        obs_rms,
                        self.env_name,
                        seed,
                        num_processes,
                        eval_log_dir,
                        device,
                        learn_run,
                    )

    def get_actor_critic(
        self, model_name, run, envs, recurrent_policy, device
    ):
        actor_critic, obs_rms = run.get_last_logged_model(model_name, envs)
        if actor_critic is None:
            actor_critic = Policy(
                envs.observation_space.shape,
                envs.action_space,
                base_kwargs={"recurrent": recurrent_policy},
            )
        actor_critic.to(device)
        return actor_critic, obs_rms

    def get_model_name(self):
        return f"{self.algo}_{self.env_name}.pt"


def papag_evaluate(
    actor_critic,
    obs_rms,
    env_name,
    seed,
    num_processes,
    eval_log_dir,
    device,
    run,
):
    eval_envs = make_vec_envs(
        env_name,
        seed + num_processes,
        num_processes,
        None,
        eval_log_dir,
        device,
        True,
    )

    vec_norm = utils.get_vec_normalize(eval_envs)
    if vec_norm is not None and obs_rms is not None:
        vec_norm.eval()
        vec_norm.obs_rms = obs_rms

    eval_episode_rewards = []

    obs = eval_envs.reset()
    eval_recurrent_hidden_states = torch.zeros(
        num_processes, actor_critic.recurrent_hidden_state_size, device=device
    )
    eval_masks = torch.zeros(num_processes, 1, device=device)

    step_count = 0
    while len(eval_episode_rewards) < 10:
        with torch.no_grad():
            _, action, _, eval_recurrent_hidden_states = actor_critic.act(
                obs,
                eval_recurrent_hidden_states,
                eval_masks,
                deterministic=True,
            )

        # Obser reward and next obs
        obs, _, done, infos = eval_envs.step(action)
        step_count += 1

        eval_masks = torch.tensor(
            [[0.0] if done_ else [1.0] for done_ in done],
            dtype=torch.float32,
            device=device,
        )

        for info in infos:
            if "episode" in info.keys():
                eval_episode_rewards.append(info["episode"]["r"])
                run.add_episode_data(step_count, info["episode"]["r"])
                step_count = 0

    eval_envs.close()

    print(
        " Evaluation using {} episodes: mean reward {:.5f}\n".format(
            len(eval_episode_rewards), np.mean(eval_episode_rewards)
        )
    )