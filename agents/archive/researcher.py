"""
Researcher Agent for BigData Newsletter System.
"""

from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph_swarm import create_handoff_tool

from config.settings import get_agent_config
from config.agent_names import RESEARCHER
from config.agent_handoffs import get_agent_handoffs
from prompts.agent_prompts import get_agent_prompt
from tools.web_search import search_web


def create_researcher_agent():
    """
    Create the Researcher agent.

    The Researcher gathers information about BigData topics from:
    - Web search for latest news, trends, and technical details
    - Multiple search queries to gather comprehensive information

    Handoff connections are defined in config/agent_handoffs.py
    """
    config = get_agent_config("researcher")

    # Create model with agent tag
    model = ChatOpenAI(model=config.get("model", "gpt-4o"), temperature=config.get("temperature", 0.2), tags=["researcher"])

    # Define tools
    tools = [
        search_web,
    ]

    # Add handoff tools from centralized configuration
    for target_agent, description in get_agent_handoffs(RESEARCHER):
        tools.append(create_handoff_tool(agent_name=target_agent, description=description))

    # Create agent
    agent = create_react_agent(model, tools, prompt=get_agent_prompt("researcher"), name=RESEARCHER)

    return agent
