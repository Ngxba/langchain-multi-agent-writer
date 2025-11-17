"""
Class-based agent factory for creating agents with minimal boilerplate.

The AgentFactory class encapsulates agent creation logic and provides a clean,
object-oriented interface for building agents from configuration.
"""

import logging
import yaml  # type: ignore
from pathlib import Path
from typing import List, Optional, Union, Dict
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain.tools import BaseTool
from langchain.agents import create_agent
from langgraph_swarm import create_handoff_tool

from agents.models import AgentConfig, HandoffConfig, AgentSystemConfig
from utils.agent_prompts import get_agent_prompt

# Configure logger
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


class AgentFactory:
    """
    Factory class for creating agents from configuration.

    This class provides a clean, composable interface for building agents
    with automatic configuration loading, model selection, tool attachment,
    and prompt management.

    Usage:
        factory = AgentFactory()
        agent = factory.create("research_strategist", tools=[search_web])
    """

    # Class-level cache for config (shared across all instances)
    _config_cache: Dict[str, AgentSystemConfig] = {}

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the agent factory.

        Args:
            config_path: Optional path to agents.yaml (default: config/agents.yaml)
        """
        logger.info("Initializing AgentFactory")
        self._tool_registry = {
            "search_web": "tools.web_search.search_web",
            # Add more tools here as needed
        }
        self._config_path = config_path
        self._system_config: Optional[AgentSystemConfig] = None
        logger.debug(f"Tool registry initialized with {len(self._tool_registry)} tools")

    def load_config(self, config_path: Optional[str] = None) -> AgentSystemConfig:
        """
        Load and validate agent configuration from YAML.

        Args:
            config_path: Path to agents.yaml (default: config/agents.yaml)

        Returns:
            Validated AgentSystemConfig

        Raises:
            FileNotFoundError: If config file not found
            ValueError: If config validation fails
        """
        # Resolve config path to Path object
        resolved_path: Path
        if config_path is None:
            if self._config_path is not None:
                resolved_path = Path(self._config_path)
            else:
                # Default to config/agents.yaml
                project_root = Path(__file__).parent.parent
                resolved_path = project_root / "config" / "agents.yaml"
        else:
            resolved_path = Path(config_path)

        # Check cache
        cache_key = str(resolved_path.absolute())
        if cache_key in AgentFactory._config_cache:
            logger.debug(f"Using cached config from: {resolved_path}")
            return AgentFactory._config_cache[cache_key]

        # Load YAML
        if not resolved_path.exists():
            logger.error(f"Config file not found: {resolved_path}")
            raise FileNotFoundError(f"Config not found: {resolved_path}")

        logger.info(f"Loading agent configuration from: {resolved_path}")
        with open(resolved_path, "r", encoding="utf-8") as f:
            raw_config = yaml.safe_load(f)

        # Validate with Pydantic
        logger.debug("Validating configuration with Pydantic")
        validated_config = AgentSystemConfig(**raw_config)
        logger.info(f"Configuration validated successfully: {len(validated_config.agents)} agents loaded")

        # Cache it
        AgentFactory._config_cache[cache_key] = validated_config
        return validated_config

    def get_system_config(self) -> AgentSystemConfig:
        """
        Get the agent system configuration (cached).

        Returns:
            AgentSystemConfig instance
        """
        if self._system_config is None:
            self._system_config = self.load_config(self._config_path)
        return self._system_config

    def reload_config(self) -> AgentSystemConfig:
        """
        Force reload of configuration (clears cache).

        Returns:
            Freshly loaded AgentSystemConfig
        """
        logger.info("Reloading configuration (clearing cache)")
        AgentFactory._config_cache.clear()
        self._system_config = None
        return self.get_system_config()

    def get_all_agent_names(self) -> List[str]:
        """
        Get list of all configured agent names.

        Returns:
            List of agent name strings
        """
        config = self.get_system_config()
        return list(config.agents.keys())

    def get_default_agent(self) -> str:
        """
        Get the default agent name.

        Returns:
            Default agent name string
        """
        config = self.get_system_config()
        return config.default_agent

    def _get_agent_config(self, name: str) -> AgentConfig:
        """
        Get agent configuration as Pydantic model.

        Args:
            name: Agent name

        Returns:
            AgentConfig Pydantic model with validation

        Raises:
            KeyError: If agent not found
        """
        config = self.get_system_config()
        return config.get_agent_config(name)

    def _get_agent_handoffs(self, agent_name: str) -> List[HandoffConfig]:
        """
        Get agent handoffs as Pydantic models.

        Args:
            agent_name: Agent name

        Returns:
            List of HandoffConfig Pydantic models

        Raises:
            KeyError: If agent not found
        """
        config = self.get_system_config()
        return config.get_handoff_targets(agent_name)

    def create(
        self,
        name: str,
        tools: Optional[List[BaseTool]] = None,
        include_handoffs: bool = True,
        allowed_handoffs: Optional[List[str]] = None,
        custom_prompt: Optional[str] = None,
    ):
        """
        Create an agent from configuration.

        Args:
            name: Agent name (must exist in agents.yaml)
            tools: Optional list of base tools for this agent
            include_handoffs: Whether to automatically add handoff tools
            allowed_handoffs: Optional list of agent names to filter handoffs (only these agents will be included)
            custom_prompt: Optional custom prompt (overrides loaded prompt)

        Returns:
            Configured ReAct agent ready to use

        Example:
            >>> factory = AgentFactory()
            >>> from tools.web_search import search_web
            >>> agent = factory.create("research_strategist", tools=[search_web])
            >>> # Create with filtered handoffs (only to agents in swarm)
            >>> agent = factory.create("research_strategist", tools=[search_web],
            ...                       allowed_handoffs=["research_technical"])

        Raises:
            KeyError: If agent name not found in configuration
            ValueError: If configuration is invalid
        """
        logger.info(f"Creating agent: {name}")

        # Load agent configuration (Pydantic model)
        config = self._get_agent_config(name)
        logger.debug(f"Agent config loaded: model={config.model}, temp={config.temperature}")

        # Create model
        model = self._create_model(config)

        # Build tool list
        agent_tools = self._build_tools(name, tools, include_handoffs, allowed_handoffs)
        logger.info(f"Agent '{name}' configured with {len(agent_tools)} tools")

        # Load or use prompt
        prompt = custom_prompt or self._load_prompt(config)
        logger.debug(f"Prompt loaded for agent '{name}': {len(prompt)} chars")

        # Create the agent using langchain.agents.create_agent
        agent = create_agent(model=model, tools=agent_tools, system_prompt=prompt, name=name)
        logger.info(f"Agent '{name}' created successfully")
        return agent

    def create_from_config_only(self, name: str):
        """
        Create an agent using ONLY configuration (tools specified in YAML).

        This is useful when all tools are defined in the config file.

        Args:
            name: Agent name

        Returns:
            Configured agent

        Example:
            >>> factory = AgentFactory()
            >>> agent = factory.create_from_config_only("eic")
        """
        config = self._get_agent_config(name)
        tools = self._import_tools(config.tools)
        return self.create(name, tools=tools)

    def _create_model(self, config: AgentConfig) -> Union[ChatOpenAI, ChatAnthropic]:
        """
        Create an LLM model instance based on agent configuration.

        Automatically selects the right model class (OpenAI vs Anthropic)
        based on the model name.

        Args:
            config: Agent configuration (Pydantic model)

        Returns:
            Configured LLM model instance
        """
        # Determine model provider from model name
        if config.model.startswith("claude"):
            logger.debug(f"Creating Anthropic model: {config.model}")
            return ChatAnthropic(model=config.model, temperature=config.temperature, tags=config.tags)
        else:
            logger.debug(f"Creating OpenAI model: {config.model}")
            return ChatOpenAI(model=config.model, temperature=config.temperature, tags=config.tags)

    def _build_tools(
        self, agent_name: str, base_tools: Optional[List[BaseTool]], include_handoffs: bool, allowed_handoffs: Optional[List[str]] = None
    ) -> List[BaseTool]:
        """
        Build the complete tool list for an agent.

        Combines base tools with handoff tools automatically.

        Args:
            agent_name: Name of the agent
            base_tools: List of base tools specific to this agent
            include_handoffs: Whether to include handoff tools
            allowed_handoffs: Optional list of agent names to filter handoffs

        Returns:
            Complete list of tools including handoffs
        """
        tools = list(base_tools) if base_tools else []

        if include_handoffs:
            # Get handoff configuration as Pydantic models
            handoffs = self._get_agent_handoffs(agent_name)
            logger.debug(f"Agent '{agent_name}' has {len(handoffs)} handoff targets")

            for handoff in handoffs:
                # Filter handoffs if allowed_handoffs is specified
                if allowed_handoffs is not None and handoff.to not in allowed_handoffs:
                    logger.debug(f"Skipping handoff to '{handoff.to}' (not in allowed list)")
                    continue

                logger.debug(f"Adding handoff from '{agent_name}' to '{handoff.to}'")
                handoff_tool = create_handoff_tool(agent_name=handoff.to, description=handoff.when)
                tools.append(handoff_tool)

        logger.debug(f"Built {len(tools)} total tools for agent '{agent_name}'")
        return tools

    def _load_prompt(self, config: AgentConfig) -> str:
        """
        Load prompt for an agent.

        Args:
            config: Agent configuration (Pydantic model)

        Returns:
            Prompt string

        Raises:
            ValueError: If prompt cannot be loaded
        """
        # Pass prompt_file from config to the prompt loader
        logger.debug(f"Loading prompt for agent '{config.name}' using prompt_file: {config.prompt_file}")
        prompt = get_agent_prompt(config.name, prompt_file=config.prompt_file)
        if not prompt:
            raise ValueError(f"No prompt found for agent '{config.name}'. Expected file: prompts/{config.prompt_file}")
        return prompt

    def _import_tools(self, tool_names: List[str]) -> List[BaseTool]:
        """
        Import tool instances by their string names.

        This allows tools to be specified in YAML config.

        Args:
            tool_names: List of tool names (e.g., ["search_web"])

        Returns:
            List of tool instances
        """
        tools = []

        for tool_name in tool_names:
            if tool_name not in self._tool_registry:
                logger.warning(f"Unknown tool '{tool_name}' - skipping")
                continue

            # Dynamic import
            module_path, attr_name = self._tool_registry[tool_name].rsplit(".", 1)
            try:
                logger.debug(f"Importing tool '{tool_name}' from {module_path}")
                module = __import__(module_path, fromlist=[attr_name])
                tool = getattr(module, attr_name)
                tools.append(tool)
                logger.debug(f"Tool '{tool_name}' imported successfully")
            except (ImportError, AttributeError) as e:
                logger.error(f"Could not import tool '{tool_name}': {e}")

        logger.info(f"Imported {len(tools)} tools from config")
        return tools

    def register_tool(self, name: str, import_path: str):
        """
        Register a new tool in the factory's tool registry.

        Args:
            name: Tool name (e.g., "search_web")
            import_path: Full import path (e.g., "tools.web_search.search_web")

        Example:
            >>> factory = AgentFactory()
            >>> factory.register_tool("my_tool", "tools.my_module.my_tool")
        """
        logger.info(f"Registering tool '{name}' with path: {import_path}")
        self._tool_registry[name] = import_path


__all__ = [
    "AgentFactory",
]
