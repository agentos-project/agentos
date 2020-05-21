"""
The ``agentos`` module provides a simplistic API for building
learning agents and their behaviors.
"""
from agentos.version import VERSION as __version__
from agentos.core import AgentManager, Agent, DEFAULT_AGENT_CONFIG

__all__ = ["AgentManager", "Agent", "DEFAULT_AGENT_CONFIG"]

