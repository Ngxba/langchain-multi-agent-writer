"""
Content Planner Agent for BigData Newsletter System.
"""

from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph_swarm import create_handoff_tool

from config.settings import get_agent_config
from config.agent_names import PLANNER
from config.agent_handoffs import get_agent_handoffs
from prompts.agent_prompts import get_agent_prompt


def create_planner_agent():
    """
    Create the Content Planner agent.

    The Planner structures newsletters with:
    - Clear section organization
    - Appropriate word count allocation
    - Audience targeting
    - Hook and engagement planning

    Handoff connections are defined in config/agent_handoffs.py
    """
    config = get_agent_config("planner")

    # Create model with agent tag
    model = ChatOpenAI(model=config.get("model", "gpt-4o"), temperature=config.get("temperature", 0.5), tags=["planner"])

    # Define tools (only handoffs for Planner)
    tools = []

    # Add handoff tools from centralized configuration
    for target_agent, description in get_agent_handoffs(PLANNER):
        tools.append(create_handoff_tool(agent_name=target_agent, description=description))

    # Create agent
    agent = create_react_agent(model, tools, prompt=get_agent_prompt("planner"), name=PLANNER)

    return agent
