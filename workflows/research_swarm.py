"""
Research Swarm Workflow

Creates a swarm with Research Strategist and Technical Researcher agents.
This swarm analyzes topics and creates content briefs, then gathers technical information.
"""

import json
from pathlib import Path
from langgraph.checkpoint.memory import MemorySaver
from langgraph_swarm import create_swarm

from agents.research_strategist import create_research_strategist_agent
from agents.research_technical import create_research_technical_agent
from config.agent_names import RESEARCH_STRATEGIST, RESEARCH_TECHNICAL


def load_style_reference():
    """Load the Vietnamese technical newsletter style reference."""
    style_path = Path(__file__).parent.parent / "prompts" / "style_reference.json"
    with open(style_path, "r", encoding="utf-8") as f:
        return json.load(f)


def create_research_swarm():
    """
    Create and compile the Research Swarm.

    Returns:
        Compiled LangGraph application with two agents:
        - Research Strategist: Creates content briefs
        - Technical Researcher: Gathers detailed information
    """
    # Create both research agents
    strategist_agent = create_research_strategist_agent()
    technical_agent = create_research_technical_agent()

    # Create the swarm
    swarm = create_swarm(
        agents=[strategist_agent, technical_agent],
        default_active_agent=RESEARCH_STRATEGIST,
    )

    # Compile with checkpointer for conversation memory
    checkpointer = MemorySaver()
    app = swarm.compile(checkpointer=checkpointer)

    return app


def get_swarm_info():
    """Get information about the Research Swarm."""
    return {
        "name": "Research Swarm",
        "description": "Multi-agent system for Vietnamese technical newsletter research",
        "agents": [
            {
                "name": RESEARCH_STRATEGIST,
                "role": "Strategic content planning and brief creation",
                "capabilities": [
                    "Analyzes topic requests",
                    "Creates comprehensive content briefs",
                    "Plans narrative structure",
                    "Identifies research needs",
                    "Transfers to Technical Researcher",
                ],
            },
            {
                "name": RESEARCH_TECHNICAL,
                "role": "Technical information gathering and research",
                "capabilities": [
                    "Searches for official documentation",
                    "Finds real-world use cases",
                    "Gathers performance data",
                    "Locates Vietnamese/Asian examples",
                    "Compiles research reports",
                ],
            },
        ],
        "default_agent": RESEARCH_STRATEGIST,
        "workflow": [
            "1. User provides topic request",
            "2. Research Strategist analyzes and creates content brief",
            "3. Research Strategist transfers to Technical Researcher",
            "4. Technical Researcher executes web searches",
            "5. Technical Researcher compiles findings",
            "6. Final research output delivered",
        ],
    }
