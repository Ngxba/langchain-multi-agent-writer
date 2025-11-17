"""
System prompts for all agents in the BigData Newsletter Swarm.

Supports both simple prompts and template inheritance:
- Simple: Just a 'prompt' key with the full text
- Template inheritance: 'extends' key to inherit from base template
"""

import logging
import yaml  # type: ignore
from pathlib import Path
from typing import Dict, Any, Optional

# Configure logger
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# Cache for loaded prompts to avoid repeated file reads
_PROMPT_CACHE: Dict[str, str] = {}


def _load_base_template() -> Dict[str, Any]:
    """Load the base agent template."""
    # Prompts are in config/prompts directory
    project_root = Path(__file__).parent.parent
    base_file = project_root / "config" / "prompts" / "base" / "agent_base.yaml"

    try:
        logger.debug(f"Loading base template from: {base_file}")
        with open(base_file, "r", encoding="utf-8") as f:
            template = yaml.safe_load(f) or {}
            logger.debug("Base template loaded successfully")
            return template
    except FileNotFoundError:
        logger.warning(f"Base template not found: {base_file}")
        return {}


def _apply_template_inheritance(data: Dict[str, Any]) -> str:
    """
    Apply template inheritance if 'extends' is specified.

    Supports simple block-based inheritance where child templates
    can extend a base template and override specific blocks.

    Args:
        data: Parsed YAML data

    Returns:
        Fully composed prompt string
    """
    # If no 'extends' key, it's a simple prompt
    if "extends" not in data:
        return data.get("prompt", "")

    # Load base template
    base = _load_base_template()
    if not base:
        # Fallback to simple prompt if base not available
        return data.get("prompt", "")

    # Get base structure
    base_structure = base.get("base_structure", "")

    # Get blocks from child template
    blocks = data.get("blocks", {})

    # Substitute blocks into base structure
    # This is a simple implementation - just use format()
    try:
        prompt = base_structure.format(**blocks)
        logger.debug("Template inheritance applied successfully")
        return prompt
    except KeyError as e:
        logger.warning(f"Missing block {e} in template - using simple prompt")
        return data.get("prompt", "")


def _load_prompt_from_yaml(agent_name: str, prompt_file: Optional[str] = None) -> str:
    """
    Load prompt from YAML file for the given agent.

    Supports both simple prompts and template inheritance.

    Args:
        agent_name: Name of the agent (e.g., 'eic', 'research_strategist')
        prompt_file: Optional prompt filename from config (e.g., 'eic.yaml')
                    If not provided, defaults to '{agent_name}.yaml'

    Returns:
        The prompt string from the YAML file
    """
    # Use provided prompt_file or fallback to default
    prompt_filename = prompt_file if prompt_file else f"{agent_name}.yaml"

    # Prompts are in config/prompts directory
    project_root = Path(__file__).parent.parent
    prompts_dir = project_root / "config" / "prompts"
    yaml_file = prompts_dir / prompt_filename

    logger.debug(f"Loading prompt for agent '{agent_name}' from: {yaml_file}")

    try:
        with open(yaml_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

            if not data:
                logger.warning(f"Empty prompt file for agent: {agent_name}")
                return ""

            # Check if this uses template inheritance
            if "extends" in data:
                logger.debug(f"Agent '{agent_name}' uses template inheritance")
                return _apply_template_inheritance(data)
            else:
                # Simple prompt (backward compatible)
                logger.debug(f"Agent '{agent_name}' uses simple prompt")
                return data.get("prompt", "")

    except FileNotFoundError:
        logger.warning(f"Prompt file not found: {yaml_file}")
        return ""
    except Exception as e:
        logger.error(f"Error loading prompt from {yaml_file}: {e}")
        return ""


def get_agent_prompt(agent_name: str, prompt_file: Optional[str] = None) -> str:
    """
    Get the system prompt for a specific agent.

    Prompts are loaded from YAML files and cached for performance.
    Supports both simple prompts and template inheritance.

    Args:
        agent_name: Name of the agent (e.g., 'eic', 'research_strategist')
        prompt_file: Optional prompt filename from config (e.g., 'eic.yaml')
                    If not provided, defaults to '{agent_name}.yaml'

    Returns:
        The prompt string for the agent

    Example YAML formats:

    Simple prompt:
        prompt: |
          You are a helpful agent...

    Template inheritance:
        extends: base/agent_base
        blocks:
          mission: "Your mission here"
          responsibilities: "Your responsibilities here"
    """
    # Create cache key from agent name and prompt file
    cache_key = f"{agent_name}:{prompt_file if prompt_file else agent_name}"

    # Return cached prompt if available
    if cache_key in _PROMPT_CACHE:
        logger.debug(f"Returning cached prompt for agent: {agent_name}")
        return _PROMPT_CACHE[cache_key]

    # Load from YAML file (with optional inheritance)
    logger.info(f"Loading prompt for agent: {agent_name} (file: {prompt_file or 'default'})")
    prompt = _load_prompt_from_yaml(agent_name, prompt_file)

    # Cache the loaded prompt
    if prompt:
        _PROMPT_CACHE[cache_key] = prompt
        logger.info(f"Prompt cached for agent: {agent_name} ({len(prompt)} chars)")
    else:
        logger.warning(f"No prompt loaded for agent: {agent_name}")

    return prompt


def clear_prompt_cache():
    """Clear the prompt cache. Useful for development/testing."""
    logger.info(f"Clearing prompt cache ({len(_PROMPT_CACHE)} entries)")
    _PROMPT_CACHE.clear()
