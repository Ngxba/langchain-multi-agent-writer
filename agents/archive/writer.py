"""
Writer Agent for BigData Newsletter System.
"""

from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph_swarm import create_handoff_tool

from config.settings import get_agent_config
from config.agent_names import WRITER
from config.agent_handoffs import get_agent_handoffs
from prompts.agent_prompts import get_agent_prompt


def create_writer_agent():
    """
    Create the Writer agent.

    The Writer crafts newsletter content with:
    - BigData technical expertise
    - Engaging and detailed writing
    - Clear explanations of complex topics
    - Practical examples and use cases

    Handoff connections are defined in config/agent_handoffs.py
    """
    config = get_agent_config("writer")

    # Create model with agent tag
    model = ChatOpenAI(model=config.get("model", "gpt-4o"), temperature=config.get("temperature", 0.8), tags=["writer"])

    # Define tools (only handoffs for Writer)
    tools = []

    # Add handoff tools from centralized configuration
    for target_agent, description in get_agent_handoffs(WRITER):
        tools.append(create_handoff_tool(agent_name=target_agent, description=description))

    # Create agent
    agent = create_react_agent(model, tools, prompt=get_agent_prompt("writer"), name=WRITER)

    return agent
