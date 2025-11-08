"""
System prompts for all agents in the BigData Newsletter Swarm.
Prompts are loaded from individual YAML files for easy management.
"""

import yaml  # type: ignore
from pathlib import Path
from typing import Dict

# Cache for loaded prompts to avoid repeated file reads
_PROMPT_CACHE: Dict[str, str] = {}


def _load_prompt_from_yaml(agent_name: str) -> str:
    """
    Load prompt from YAML file for the given agent.

    Args:
        agent_name: Name of the agent (e.g., 'researcher', 'planner')

    Returns:
        The prompt string from the YAML file
    """
    # Get the directory where this file is located
    prompts_dir = Path(__file__).parent
    yaml_file = prompts_dir / f"{agent_name}.yaml"

    try:
        with open(yaml_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            return data.get("prompt", "")
    except FileNotFoundError:
        print(f"Warning: Prompt file not found: {yaml_file}")
        return ""
    except Exception as e:
        print(f"Error loading prompt from {yaml_file}: {e}")
        return ""


def get_agent_prompt(agent_name: str) -> str:
    """
    Get the system prompt for a specific agent.
    Prompts are loaded from YAML files and cached for performance.

    Args:
        agent_name: Name of the agent (e.g., 'researcher', 'planner', 'writer', 'editor', 'diagram_creator')

    Returns:
        The prompt string for the agent
    """
    # Return cached prompt if available
    if agent_name in _PROMPT_CACHE:
        return _PROMPT_CACHE[agent_name]

    # Load from YAML file
    prompt = _load_prompt_from_yaml(agent_name)

    # Cache the loaded prompt
    if prompt:
        _PROMPT_CACHE[agent_name] = prompt

    return prompt
