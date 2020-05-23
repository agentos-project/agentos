"""The ``agentos`` module provides an API for building learning agents."""

from agentos.version import VERSION as __version__
from agentos.core import AgentManager, Agent, DEFAULT_AGENT_CONFIG
import agentos.server as server

__all__ = ["AgentManager", "Agent", "DEFAULT_AGENT_CONFIG", "server"]

