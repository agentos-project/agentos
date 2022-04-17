import statistics
from collections import namedtuple
from typing import Optional

from mlflow.entities import RunStatus
from mlflow.utils.mlflow_tags import MLFLOW_PARENT_RUN_ID, MLFLOW_RUN_NAME

from pcs.component_run import ComponentRun
from pcs.registry import InMemoryRegistry, Registry
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
                       outer_run=self.__component__.active_run) as run:
              # run an episode
              run.log_episode(
                    # episode_data
                    ...
              )
    """

    IS_AGENT_RUN_TAG = "pcs.is_agent_run"
    LEARN_KEY = "learn"
    EVALUATE_KEY = "evaluate"
    RUN_TYPE_TAG = "run_type"
    AGENT_ID_KEY = "agent_identifier"
    ENV_ID_KEY = "environment_identifier"
    MODEL_INPUT_RUN_ID = "model_input_run_id"

    def __init__(
        self,
        run_type: str = None,
        outer_run: Run = None,
        model_input_run: Run = None,
        agent_identifier: Optional[str] = None,
        environment_identifier: Optional[str] = None,
        existing_run_id: str = None,
    ) -> None:
        """
        Create a new AgentRun.

        :param run_type: must be 'evaluate' or 'learn'
        :param outer_run: Optionally, specify another Run that this run is
            a sub-run of. Setting this will result in this AgentRun being
            visually nested under the outer_run in the MLflow UI.
        :param agent_identifier: Identifier of Agent component being evaluated
            or trained.
        :param environment_identifier: Identifier of Environment component
            being evaluated or trained.
        :param existing_run_id: Optional. If provided, load an existing run
            from the MLflow backing store. If provided, no other options can be
            provided.
        """
        if existing_run_id:
            assert not (
                run_type
                or outer_run
                or agent_identifier
                or environment_identifier
            ), (
                "If 'existing_run_id' is specified, then 'run_type', "
                "'outer_run', 'agent_identifier', and "
                "'environment_identifier' must be None."
            )

            super().__init__(existing_run_id=existing_run_id)
            if MLFLOW_PARENT_RUN_ID in self.data.tags:
                outer_run_id = self.data.tags[MLFLOW_PARENT_RUN_ID]
                self.outer_run = ComponentRun.from_existing_run_id(
                    outer_run_id
                )
            else:
                self.outer_run = None
            if self.MODEL_INPUT_RUN_ID in self.data.tags:
                model_input_run = self.data.tags[self.MODEL_INPUT_RUN_ID]
                self.model_input_run = self.__class__.from_existing_run_id(
                    model_input_run
                )
            else:
                self.model_input_run = None
            self.episode_data = []
            self.run_type = self.data.tags[self.RUN_TYPE_TAG]
            self.agent_identifier = self.data.tags[self.AGENT_ID_KEY]
            self.environment_identifier = self.data.tags[self.ENV_ID_KEY]
        else:
            assert agent_identifier and environment_identifier, (
                "If 'existing_run_id' is not provided, then "
                "'agent_identifier' and 'environment_identifier' must be."
            )
            super().__init__()
            self.outer_run = outer_run
            self.model_input_run = model_input_run
            self.set_tag(self.IS_AGENT_RUN_TAG, "True")
            self.episode_data = []
            self.run_type = run_type
            self.agent_identifier = agent_identifier
            self.environment_identifier = environment_identifier

            self.set_tag(
                MLFLOW_RUN_NAME,
                (
                    f"AgentOS {run_type} with Agent '{self.agent_identifier}' "
                    f"and Env '{self.environment_identifier}'"
                ),
            )
            if self.outer_run:
                self.set_tag(MLFLOW_PARENT_RUN_ID, self.outer_run.info.run_id)
            if self.model_input_run:
                self.set_tag(
                    self.MODEL_INPUT_RUN_ID, self.model_input_run.info.run_id
                )
            self.log_run_type(self.run_type)
            self.log_agent_identifier(self.agent_identifier)
            self.log_environment_identifier(self.environment_identifier)

    @classmethod
    def evaluate_run(
        cls,
        outer_run: Run = None,
        model_input_run: Run = None,
        agent_identifier: Optional[str] = None,
        environment_identifier: Optional[str] = None,
        existing_run_id: str = None,
    ) -> "AgentRun":
        return cls(
            run_type=cls.EVALUATE_KEY,
            outer_run=outer_run,
            model_input_run=model_input_run,
            agent_identifier=agent_identifier,
            environment_identifier=environment_identifier,
            existing_run_id=existing_run_id,
        )

    @classmethod
    def learn_run(
        cls,
        outer_run: Run = None,
        model_input_run: Run = None,
        agent_identifier: Optional[str] = None,
        environment_identifier: Optional[str] = None,
        existing_run_id: str = None,
    ) -> "AgentRun":
        return cls(
            run_type=cls.LEARN_KEY,
            outer_run=outer_run,
            model_input_run=model_input_run,
            agent_identifier=agent_identifier,
            environment_identifier=environment_identifier,
            existing_run_id=existing_run_id,
        )

    def log_run_type(self, run_type: str) -> None:
        self.run_type = run_type
        self.set_tag(self.RUN_TYPE_TAG, self.run_type)

    def log_agent_identifier(self, agent_identifier: str) -> None:
        self.set_tag(self.AGENT_ID_KEY, agent_identifier)

    def log_environment_identifier(self, environment_identifier: str) -> None:
        self.set_tag(self.ENV_ID_KEY, environment_identifier)

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
        print(f"Results for AgentRun {self.identifier}")
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

    def to_registry(
        self,
        registry: Registry = None,
        recurse: bool = True,
        force: bool = False,
        include_artifacts: bool = False,
    ) -> Registry:
        if not registry:
            registry = InMemoryRegistry()
        if recurse:
            if self.outer_run:
                self.outer_run.to_registry(
                    registry=registry,
                    recurse=recurse,
                    force=force,
                    include_artifacts=include_artifacts,
                )
            if self.model_input_run:
                self.model_input_run.to_registry(
                    registry=registry,
                    recurse=recurse,
                    force=force,
                    include_artifacts=include_artifacts,
                )
        return super().to_registry(
            registry=registry, force=force, include_artifacts=include_artifacts
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
