"""
Tool Binder - Binds tools to agent departments with enforcement.

Ensures each agent only has access to its allowed tools as defined
in the policy configuration.

Phase 2 Implementation.
"""

import logging
import yaml  # type: ignore
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class ToolAccessError(Exception):
    """Raised when an agent tries to access a denied tool."""

    pass


class ToolBinder:
    """
    Binds tools to agent departments with strict access control.

    Enforces tool access policies:
    - Researcher: web.search, web.fetch, local.search, citation.builder
    - Writer: seo.readability (optional)
    - Editor: seo.readability, plagiarism.scan, citation.builder
    - Diagrammer: drawio.generate, drawio.export, web.search
    """

    def __init__(self, policy_path: Optional[str] = None):
        """
        Initialize tool binder with policy.

        Args:
            policy_path: Path to policy.yaml (optional)
        """
        self.policy = self._load_policy(policy_path)
        self.tool_binding = self.policy.get("tool_binding", {})
        self._tool_registry: dict[str, Callable] = {}

        logger.info(f"ToolBinder initialized with {len(self.tool_binding)} departments")

    def _load_policy(self, policy_path: Optional[str]) -> dict[str, Any]:
        """Load policy configuration."""
        if policy_path is None:
            default_path = Path(__file__).parent.parent / "config" / "policy.yaml"
            if default_path.exists():
                policy_path = str(default_path)
            else:
                return self._default_policy()

        try:
            with open(policy_path) as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.error(f"Failed to load policy: {e}")
            return self._default_policy()

    def _default_policy(self) -> dict[str, Any]:
        """Return default tool binding policy."""
        return {
            "tool_binding": {
                "researcher": {
                    "allowed": ["web.search", "web.fetch", "local.search", "citation.builder"],
                    "denied": [],
                },
                "writer": {
                    "allowed": ["seo.readability"],
                    "denied": ["web.fetch", "web.search"],
                },
                "editor": {
                    "allowed": ["seo.readability", "plagiarism.scan", "citation.builder"],
                    "denied": ["web.fetch"],
                },
                "diagrammer": {
                    "allowed": ["drawio.generate", "drawio.export", "web.search"],
                    "denied": ["web.fetch"],
                },
            }
        }

    def register_tool(self, tool_name: str, tool_func: Callable) -> None:
        """
        Register a tool implementation.

        Args:
            tool_name: Tool identifier (e.g., "web.search")
            tool_func: Tool function to call
        """
        self._tool_registry[tool_name] = tool_func
        logger.debug(f"Registered tool: {tool_name}")

    def register_tools(self, tools: dict[str, Callable]) -> None:
        """
        Register multiple tools at once.

        Args:
            tools: Dict mapping tool names to functions
        """
        for name, func in tools.items():
            self.register_tool(name, func)

    def get_tools_for_agent(self, agent_name: str) -> dict[str, Callable]:
        """
        Get all allowed tools for an agent.

        Args:
            agent_name: Name of the agent (researcher, writer, etc.)

        Returns:
            Dict mapping tool names to wrapped functions
        """
        agent_name = agent_name.lower()
        binding = self.tool_binding.get(agent_name, {})
        allowed = set(binding.get("allowed", []))

        tools = {}
        for tool_name in allowed:
            if tool_name in self._tool_registry:
                # Wrap tool with access check
                tools[tool_name] = self._wrap_tool(agent_name, tool_name)
            else:
                logger.warning(f"Tool {tool_name} not registered")

        return tools

    def is_tool_allowed(self, agent_name: str, tool_name: str) -> bool:
        """
        Check if a tool is allowed for an agent.

        Args:
            agent_name: Name of the agent
            tool_name: Name of the tool

        Returns:
            True if allowed, False otherwise
        """
        agent_name = agent_name.lower()
        binding = self.tool_binding.get(agent_name, {})

        # Check deny list first
        denied = set(binding.get("denied", []))
        if tool_name in denied:
            return False

        # Check allow list
        allowed = set(binding.get("allowed", []))
        return tool_name in allowed

    def call_tool(self, agent_name: str, tool_name: str, *args, **kwargs) -> Any:
        """
        Call a tool with access control.

        Args:
            agent_name: Name of the calling agent
            tool_name: Name of the tool to call
            *args: Tool arguments
            **kwargs: Tool keyword arguments

        Returns:
            Tool result

        Raises:
            ToolAccessError: If agent is not allowed to use tool
            ValueError: If tool is not registered
        """
        # Check access
        if not self.is_tool_allowed(agent_name, tool_name):
            raise ToolAccessError(f"Agent '{agent_name}' is not allowed to use tool '{tool_name}'")

        # Get tool
        if tool_name not in self._tool_registry:
            raise ValueError(f"Tool '{tool_name}' is not registered")

        tool_func = self._tool_registry[tool_name]

        # Call tool
        logger.info(f"Agent '{agent_name}' calling tool '{tool_name}'")
        return tool_func(*args, **kwargs)

    def _wrap_tool(self, agent_name: str, tool_name: str) -> Callable:
        """Wrap a tool with access logging."""
        tool_func = self._tool_registry[tool_name]

        def wrapped(*args, **kwargs):
            logger.debug(f"[{agent_name}] Calling {tool_name}")
            return tool_func(*args, **kwargs)

        wrapped.__name__ = tool_name
        wrapped.__doc__ = tool_func.__doc__
        return wrapped

    def get_allowed_tools(self, agent_name: str) -> list[str]:
        """Get list of allowed tool names for an agent."""
        agent_name = agent_name.lower()
        binding = self.tool_binding.get(agent_name, {})
        return binding.get("allowed", [])

    def get_denied_tools(self, agent_name: str) -> list[str]:
        """Get list of denied tool names for an agent."""
        agent_name = agent_name.lower()
        binding = self.tool_binding.get(agent_name, {})
        return binding.get("denied", [])


def create_tool_binder_with_adapters(policy_path: Optional[str] = None) -> ToolBinder:
    """
    Create a ToolBinder with all tool adapters registered.

    Args:
        policy_path: Optional path to policy.yaml

    Returns:
        Configured ToolBinder instance
    """
    from tools.adapters import (
        search_web,
        fetch_url,
        build_citations,
        generate_diagram,
        export_diagram,
        check_readability,
    )

    binder = ToolBinder(policy_path)

    # Register all tools
    binder.register_tools(
        {
            "web.search": search_web,
            "web.fetch": fetch_url,
            "citation.builder": build_citations,
            "drawio.generate": generate_diagram,
            "drawio.export": export_diagram,
            "seo.readability": check_readability,
            # local.search and plagiarism.scan would be added here
        }
    )

    return binder


# Global instance
_binder: Optional[ToolBinder] = None


def get_tool_binder() -> ToolBinder:
    """Get the global tool binder instance."""
    global _binder
    if _binder is None:
        _binder = create_tool_binder_with_adapters()
    return _binder


def bind_tools_for_agent(agent_name: str) -> dict[str, Callable]:
    """
    Get bound tools for an agent.

    Convenience function for getting agent's tools.

    Args:
        agent_name: Name of the agent

    Returns:
        Dict of tool name -> function
    """
    return get_tool_binder().get_tools_for_agent(agent_name)
