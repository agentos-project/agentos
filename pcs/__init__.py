"""The ``agentos`` module provides an API for building learning agents."""

from agentos.agent_run import AgentRun
from pcs.argument_set import ArgumentSet
from pcs.component_run import ComponentRun, active_component_run
from agentos.core import (
    Agent,
    Dataset,
    Environment,
    EnvironmentSpec,
    Policy,
    Runnable,
    Trainer,
)
from pcs.registry import Registry
from pcs.run import Run
from pcs.run_command import RunCommand
from pcs.specs import (
    ArgumentSetSpec,
    ComponentSpec,
    RepoSpec,
    RunSpec,
    flatten_spec,
    unflatten_spec,
)
from pcs.version import VERSION as __version__  # noqa: F401
from pcs.component import Component
from pcs.repo import GitHubRepo, LocalRepo, Repo

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
    "LocalRepo",
    "GitHubRepo",
    "Component",
    "ArgumentSet",
    "RunCommand",
    "Run",
    "ComponentRun",
    "active_component_run",
    "flatten_spec",
    "unflatten_spec",
    "ComponentSpec",
    "RepoSpec",
    "ArgumentSetSpec",
    "RunSpec",
]
