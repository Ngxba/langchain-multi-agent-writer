"""
Agents package.

Provides the AgentFactory class for creating agents from configuration,
and Pydantic schemas for type-safe agent configuration.
"""

from agents.agent_factory import AgentFactory
from agents.models import (
    AgentConfig,
    AgentSystemConfig,
    HandoffConfig,
)

__all__ = [
    # Factory
    "AgentFactory",
    # Schemas
    "AgentConfig",
    "AgentSystemConfig",
    "HandoffConfig",
]
