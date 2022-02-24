"""The ``agentos`` module provides an API for building learning agents."""

from agentos.version import VERSION as __version__  # noqa: F401
from agentos.core import (
    Agent,
    Dataset,
    Environment,
    EnvironmentSpec,
    Policy,
    Runnable,
    Trainer,
)

from agentos.registry import Registry
from agentos.component import Component
from agentos.component_run import ComponentRun, active_component_run
from agentos.repo import Repo, GitHubRepo
from agentos.parameter_set import ParameterSet
from agentos.run import Run
from agentos.run_command import RunCommand
from agentos.specs import (
    ComponentSpec,
    RepoSpec,
    ParameterSetSpec,
    RunSpec,
    flatten_spec,
    unflatten_spec,
)
from agentos.agent_run import AgentRun

__all__ = [
    "Agent",
    "AgentRun",
    "Dataset",
    "Environment",
    "EnvironmentSpec",
    "Policy",
    "Runnable",
    "Trainer",
    "Registry",
    "Repo",
    "GitHubRepo",
    "Component",
    "ParameterSet",
    "RunCommand",
    "Run",
    "ComponentRun",
    "active_component_run",
    "flatten_spec",
    "unflatten_spec",
    "ComponentSpec",
    "RepoSpec",
    "ParameterSetSpec",
    "RunSpec",
]
