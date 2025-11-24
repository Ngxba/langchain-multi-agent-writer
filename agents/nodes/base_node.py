"""
Base Agent Node - Foundation for all agent nodes.

Provides common functionality for agent execution in LangGraph.

Phase 2 Implementation.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from agents.tool_binder import ToolBinder, get_tool_binder

logger = logging.getLogger(__name__)


@dataclass
class NodeResult:
    """Result from agent node execution."""

    success: bool
    agent_name: str
    output: dict[str, Any] = field(default_factory=dict)
    next_agent: Optional[str] = None
    error: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseAgentNode(ABC):
    """
    Base class for all agent nodes.

    Provides common functionality:
    - Tool binding and execution
    - State management
    - Handoff logic
    - Error handling
    """

    def __init__(
        self,
        agent_name: str,
        tool_binder: Optional[ToolBinder] = None,
    ):
        self.agent_name = agent_name
        self.tool_binder = tool_binder or get_tool_binder()
        self.tools = self.tool_binder.get_tools_for_agent(agent_name)

        logger.info(f"Initialized {agent_name} node with {len(self.tools)} tools")

    @abstractmethod
    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """
        Execute the agent node.

        Args:
            state: Current workflow state

        Returns:
            Updated state dict
        """
        pass

    def get_context_slice(self, state: dict[str, Any]) -> dict[str, Any]:
        """
        Extract the context slice for this agent.

        Override in subclasses to define what state each agent sees.
        """
        return state

    def call_tool(self, tool_name: str, **kwargs) -> Any:
        """
        Call a tool with access control.

        Args:
            tool_name: Name of the tool
            **kwargs: Tool arguments

        Returns:
            Tool result
        """
        if tool_name not in self.tools:
            logger.warning(f"Tool {tool_name} not available for {self.agent_name}")
            raise ValueError(f"Tool {tool_name} not available")

        tool_func = self.tools[tool_name]
        return tool_func(**kwargs)

    def handoff_to(self, next_agent: str, state: dict[str, Any], message: str = "") -> dict[str, Any]:
        """
        Prepare state for handoff to another agent.

        Args:
            next_agent: Name of the next agent
            state: Current state
            message: Optional handoff message

        Returns:
            Updated state
        """
        state["current_agent"] = next_agent
        state["previous_agent"] = self.agent_name

        if message:
            handoff_record = {
                "from": self.agent_name,
                "to": next_agent,
                "message": message,
                "timestamp": datetime.now().isoformat(),
            }
            if "handoffs" not in state:
                state["handoffs"] = []
            state["handoffs"].append(handoff_record)

        logger.info(f"Handoff: {self.agent_name} -> {next_agent}")
        return state

    def add_to_messages(self, state: dict[str, Any], role: str, content: str) -> dict[str, Any]:
        """Add a message to the conversation history."""
        if "messages" not in state:
            state["messages"] = []

        state["messages"].append(
            {
                "role": role,
                "content": content,
                "agent": self.agent_name,
                "timestamp": datetime.now().isoformat(),
            }
        )

        return state

    def get_style_profile(self, state: dict[str, Any]) -> dict[str, Any]:
        """Get the active style profile from state."""
        return state.get("style_profile", {})

    def increment_iteration(self, state: dict[str, Any]) -> dict[str, Any]:
        """Increment the iteration counter."""
        state["iteration_count"] = state.get("iteration_count", 0) + 1
        return state
