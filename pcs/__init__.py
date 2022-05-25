"""The ``pcs`` package provides an API for Module Programming."""

from pcs.argument_set import ArgumentSet
from instance_manager import Instance
from class_manager import Class
from module_manager import Module
from pcs.output import Output, active_output
from pcs.registry import Registry
from pcs.repo import GitHubRepo, LocalRepo, Repo
from pcs.run import MLflowRun
from pcs.command import Command
from pcs.specs import Spec, flatten_spec, unflatten_spec
from pcs.version import VERSION as __version__  # noqa: F401

__all__ = [
    "ArgumentSet",
    "Class",
    "Command",
    "GitHubRepo",
    "Instance",
    "LocalRepo",
    "MLflowRun",
    "Module",
    "Output",
    "Registry",
    "Repo",
    "Spec",
    "active_output",
    "flatten_spec",
    "unflatten_spec",
]
