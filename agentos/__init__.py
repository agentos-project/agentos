"""
The ``agentos`` module provides a simplistic API for building
learning agents and their behaviors.
"""
from agentos.version import VERSION as __version__
from agentos.agent import Agent
from agentos.behavior import Behavior

__all__ = ["Agent", "Behavior"]

