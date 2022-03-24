"""The ``pcs`` package provides an API for Component Programming."""

from pcs.argument_set import ArgumentSet
from pcs.component import Component
from pcs.component_run import ComponentRun, active_component_run
from pcs.registry import Registry
from pcs.repo import GitHubRepo, LocalRepo, Repo
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

__all__ = [
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
