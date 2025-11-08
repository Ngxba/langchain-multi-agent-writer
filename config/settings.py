"""
Configuration settings for the BigData Newsletter Agent Swarm.
"""

import os
from typing import Dict, Any
from config.agent_names import (
    RESEARCH_STRATEGIST,
    RESEARCH_TECHNICAL,
    RESEARCHER,
    PLANNER,
    WRITER,
    EDITOR,
    DIAGRAM_CREATOR,
    EIC,
)

# Model Configuration
DEFAULT_MODEL = "gpt-4o"
DEFAULT_MODEL_MINI = "gpt-4o-mini"  # For less critical tasks
CLAUDE_MODEL_4_DOT_5 = "claude-sonnet-4-5-20250929"

# Agent Configuration
AGENT_CONFIG = {
    RESEARCHER: {
        "model": DEFAULT_MODEL,
        "temperature": 0.7,
        "description": "BigData research specialist who gathers information from web search",
    },
    PLANNER: {
        "model": DEFAULT_MODEL,
        "temperature": 0.5,
        "description": "Content planning expert who structures newsletters for maximum engagement",
    },
    WRITER: {
        "model": DEFAULT_MODEL,
        "temperature": 0.8,
        "description": "BigData technical writer who creates detailed, appealing content",
    },
    EDITOR: {
        "model": DEFAULT_MODEL,
        "temperature": 0.3,
        "description": "Quality review specialist who refines and improves content",
    },
    DIAGRAM_CREATOR: {
        "model": "claude-sonnet-4-20250514",  # Claude Sonnet 4.5 for superior diagram planning
        "temperature": 0.2,
        "description": "Technical diagram creator using Claude Sonnet 4.5 for DrawIO visualizations",
    },
    EIC: {
        "model": DEFAULT_MODEL,
        "temperature": 0.5,
        "description": "Content planning expert who structures newsletters for maximum engagement",
    },
    RESEARCH_TECHNICAL: {
        "model": DEFAULT_MODEL,
        "temperature": 0.5,
        "description": """Gather deep, accurate technical information, real-world examples,
        and authoritative sources that enable other agents to create an excellent Vietnamese technical newsletter.
        The fact-finding specialist who ensures technical credibility.""",
    },
    RESEARCH_STRATEGIST: {
        "model": DEFAULT_MODEL,
        "temperature": 0.5,
        "description": """Transform a raw topic request into a detailed, actionable content brief that
        ensures the final newsletter will be engaging, technically accurate, and match the target Vietnamese audience's needs.""",
    },
}

# Web Search Configuration
SEARCH_MAX_RESULTS = 5

# Output Configuration
OUTPUT_DIR = "outputs"
DIAGRAMS_DIR = os.path.join(OUTPUT_DIR, "diagrams")

# Token Tracking
ENABLE_TOKEN_TRACKING = True
TOKEN_BUDGET_WARNING_THRESHOLD = 0.05  # Warn at $0.05

# Newsletter Configuration
NEWSLETTER_CONFIG = {
    "default_sections": [
        "Introduction",
        "Key Highlights",
        "Deep Dive",
        "Industry Trends",
        "Best Practices",
        "Conclusion",
    ],
    "target_word_count": 800,
    "tone": "professional yet engaging",
    "audience": "data engineers and architects",
}


def get_agent_config(agent_name: str) -> Dict[str, Any]:
    """Get configuration for a specific agent."""
    return AGENT_CONFIG.get(agent_name, {})


def ensure_output_dirs():
    """Ensure output directories exist."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(DIAGRAMS_DIR, exist_ok=True)
