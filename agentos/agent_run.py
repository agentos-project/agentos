import statistics
from collections import namedtuple
from typing import Optional

from mlflow.entities import RunStatus
from mlflow.utils.mlflow_tags import MLFLOW_PARENT_RUN_ID, MLFLOW_RUN_NAME

from pcs.run import Run

_EPISODE_KEY = "episode_count"
_STEP_KEY = "step_count"

_RUN_STATS_MEMBERS = [
    _EPISODE_KEY,
    _STEP_KEY,
    "max_reward",
    "median_reward",
    "mean_reward",
    "min_reward",
    "training_episode_count",
    "training_step_count",
]

RunStats = namedtuple("RunStats", _RUN_STATS_MEMBERS)


class AgentRun(Run):
    """
    An AgentRun provides an API that agents can use to log agent related
    data/stats/tags/etc. AgentRun can be one of two flavors (which we call
    ``run_type``), 'evaluate' and 'learn'.

    The AgentRun can contain tags that reference other AgentRuns for tracking
    the training history of an agent.

    An ``AgentRun`` inherits from ``Run``, and adds functionality specific to
    runs of agents, such as runs that *evaluate* the agent's performance in an
    environment, or runs that cause the agent to *learn* in an environment.

    Like a ``Run``, an ``AgentRun`` can be used as a context manager, so that
    the developer doesn't need to remember to mark a run as finished, for
    example::

         with AgentRun('evaluate',
                       parent_run=self.__component__.active_run) as run:
              # run an episode
              run.log_episode(
                    # episode_data
                    ...
              )
    """

    IS_AGENT_RUN_TAG = "pcs.is_agent_run"
    LEARN_KEY = "learn"
    RESET_KEY = "reset"
    RESTORE_KEY = "restore"
    EVALUATE_KEY = "evaluate"
    RUN_TYPE_TAG = "run_type"
    AGENT_NAME_KEY = "agent_name"
    ENV_NAME_KEY = "environment_name"

    def __init__(
        self,
        run_type: str,
        parent_run: Optional[str] = None,
        agent_name: Optional[str] = None,
        environment_name: Optional[str] = None,
    ) -> None:
        """
        Create a new AgentRun.

        :param run_type: must be 'evaluate' or 'learn'
        :param parent_run: Optionally, specify the identifier of another Run
            that this run is a sub-run of. Setting this will result in this
            AgentRun being visually nested under the parent_run in the MLflow
            UI.
        :param agent_name: The name of the agent component being evaluated or
            trained. Defaults to "agent".
        :param environment_name: The name of the environment component being
            evaluated or trained. Defaults to "environment".
        """
        super().__init__()
        self.parent_run = parent_run
        self.set_tag(self.IS_AGENT_RUN_TAG, "True")
        self.episode_data = []
        self.run_type = run_type
        self.agent_name = agent_name or "agent"
        self.environment_name = environment_name or "environment"

        self.set_tag(
            MLFLOW_RUN_NAME,
            (
                f"AgentOS {run_type} with Agent '{self.agent_name}' "
                f"and Env '{self.environment_name}'"
            ),
        )
        if self.parent_run:
            self.set_tag(MLFLOW_PARENT_RUN_ID, self.parent_run.info.run_id)

        self.log_run_type(self.run_type)
        self.log_agent_name(self.agent_name)
        self.log_environment_name(self.environment_name)

    def log_run_type(self, run_type: str) -> None:
        self.run_type = run_type
        self.set_tag(self.RUN_TYPE_TAG, self.run_type)

    def log_agent_name(self, agent_name: str) -> None:
        self.log_param(self.AGENT_NAME_KEY, agent_name)

    def log_environment_name(self, environment_name: str) -> None:
        self.log_param(self.ENV_NAME_KEY, environment_name)

    def log_run_metrics(self):
        assert self.episode_data, "No episode data!"
        run_stats = self._get_run_stats()
        for key in _RUN_STATS_MEMBERS:
            val = getattr(run_stats, key)
            self.log_metric(key, val)

    def get_training_info(self) -> (int, int):
        runs = self.get_all_runs()
        total_episodes = 0
        total_steps = 0
        for run in runs:
            if run.data.tags.get(self.RUN_TYPE_TAG) == self.LEARN_KEY:
                total_episodes += int(run.data.metrics.get(_EPISODE_KEY, 0))
                total_steps += int(run.data.metrics.get(_STEP_KEY, 0))
        return total_episodes, total_steps

    def print_results(self):
        if not self.episode_data:
            return
        run_stats = self._get_run_stats()
        if self.run_type == self.LEARN_KEY:
            print(
                "\nTraining results over "
                f"{run_stats.episode_count} episodes:"
            )
            print(
                "\tOverall agent was trained on "
                f"{run_stats.training_step_count} transitions over "
                f"{run_stats.training_episode_count} episodes"
            )
        else:
            print(
                "\nBenchmark results over "
                f"{run_stats.episode_count} episodes:"
            )
            print(
                "\tBenchmarked agent was trained on "
                f"{run_stats.training_step_count} transitions over "
                f"{run_stats.training_episode_count} episodes"
            )
        print(
            f"\tMax reward over {run_stats.episode_count} episodes: "
            f"{run_stats.max_reward}"
        )
        print(
            f"\tMean reward over {run_stats.episode_count} episodes: "
            f"{run_stats.mean_reward}"
        )
        print(
            f"\tMedian reward over {run_stats.episode_count} episodes: "
            f"{run_stats.median_reward}"
        )
        print(
            f"\tMin reward over {run_stats.episode_count} episodes: "
            f"{run_stats.min_reward}"
        )
        print()

    def _get_run_stats(self):
        episode_lengths = [d["steps"] for d in self.episode_data]
        episode_returns = [d["reward"] for d in self.episode_data]
        training_episodes, training_steps = self.get_training_info()
        return RunStats(
            episode_count=len(self.episode_data),
            step_count=sum(episode_lengths),
            max_reward=max(episode_returns),
            mean_reward=statistics.mean(episode_returns),
            median_reward=statistics.median(episode_returns),
            min_reward=min(episode_returns),
            training_episode_count=training_episodes,
            training_step_count=training_steps,
        )

    def add_episode_data(self, steps: int, reward: float):
        self.episode_data.append(
            {
                "steps": steps,
                "reward": reward,
            }
        )

    def end(
        self,
        status: str = RunStatus.to_string(RunStatus.FINISHED),
        print_results: bool = True,
    ) -> None:
        super().end(status)
        self.log_run_metrics()
        if print_results:
            self.print_results()

    def __enter__(self) -> "AgentRun":
        return self

    def __exit__(self, type, value, traceback) -> None:
        super().__exit__(type, value, traceback)
