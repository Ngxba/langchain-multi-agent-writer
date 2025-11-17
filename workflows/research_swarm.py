"""
Research Swarm Workflow

Creates a swarm with Research Strategist and Technical Researcher agents.
This swarm analyzes topics and creates content briefs, then gathers technical information.
"""

import json
from pathlib import Path
from langgraph.checkpoint.memory import MemorySaver
from langgraph_swarm import create_swarm

from agents import AgentFactory


def load_style_reference():
    """Load the Vietnamese technical newsletter style reference."""
    style_path = Path(__file__).parent.parent / "config" / "prompts" / "style_reference.json"
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
    # Create agents using factory
    # Filter handoffs to only include agents in this swarm
    factory = AgentFactory()
    strategist_agent = factory.create("research_strategist")
    technical_agent = factory.create("research_technical")

    # Create the swarm
    swarm = create_swarm(
        agents=[strategist_agent, technical_agent],
        default_active_agent="research_strategist",
    )

    # Compile with checkpointer for conversation memory
    checkpointer = MemorySaver()
    app = swarm.compile(checkpointer=checkpointer)

    return app


def get_swarm_info():
    """
    Get information about the Research Swarm dynamically from config.

    Returns:
        Dict with swarm metadata including agents, capabilities, and workflow
    """
    factory = AgentFactory()
    system_config = factory.get_system_config()

    # Build agent info from config - dynamically get all agents
    agents_info = []
    for agent_name, agent_config in system_config.agents.items():
        # Build capabilities from tools and handoffs
        capabilities = []

        # Add tool capabilities
        if agent_config.tools:
            capabilities.append(f"Has access to: {', '.join(agent_config.tools)}")

        # Add handoff capabilities
        for handoff in agent_config.handoffs:
            capabilities.append(f"Can transfer to {handoff.to}")

        agents_info.append(
            {
                "name": agent_config.name,
                "role": agent_config.description,
                "capabilities": capabilities,
            }
        )

    return {
        "name": "Research Swarm",
        "description": "Multi-agent system for Vietnamese technical newsletter research",
        "agents": agents_info,
        "default_agent": system_config.default_agent,
    }
