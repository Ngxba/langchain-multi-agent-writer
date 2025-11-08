"""
Editor-in-Chief Agent for BigData Newsletter System.
"""

from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph_swarm import create_handoff_tool

from config.settings import get_agent_config
from config.agent_names import EIC
from config.agent_handoffs import get_agent_handoffs
from prompts.agent_prompts import get_agent_prompt


def create_eic_agent():
    """
    Create the Editor-in-Chief agent.

    The EIC oversees the entire newsletter creation process:
    - Reviews and approves content plans and drafts
    - Ensures technical accuracy and quality standards
    - Coordinates between different agents
    - Makes strategic decisions about content direction
    - Maintains consistency across newsletters

    Handoff connections are defined in config/agent_handoffs.py
    """
    config = get_agent_config("eic")

    # Create model with agent tag
    model = ChatOpenAI(model=config.get("model", "gpt-4o"), temperature=config.get("temperature", 0.5), tags=["eic"])

    # Define tools (only handoffs for EIC)
    tools = []

    # Add handoff tools from centralized configuration
    for target_agent, description in get_agent_handoffs(EIC):
        tools.append(create_handoff_tool(agent_name=target_agent, description=description))

    # Create agent
    agent = create_react_agent(model, tools, prompt=get_agent_prompt("eic"), name=EIC)

    return agent
