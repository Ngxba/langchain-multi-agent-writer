"""
Editor Agent for BigData Newsletter System.
"""

from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph_swarm import create_handoff_tool

from config.settings import get_agent_config
from config.agent_names import EDITOR, WRITER, RESEARCHER, PLANNER
from prompts.agent_prompts import get_agent_prompt


def create_editor_agent():
    """
    Create the Editor agent.

    The Editor reviews and refines content for:
    - Technical accuracy
    - Clarity and readability
    - Flow and structure
    - Grammar and style
    - Overall quality

    Can transfer to: Writer, Researcher, Planner
    """
    config = get_agent_config("editor")

    # Create model with agent tag
    model = ChatOpenAI(model=config.get("model", "gpt-4o"), temperature=config.get("temperature", 0.3), tags=["editor"])

    # Define tools
    tools = [
        # Handoff tools
        create_handoff_tool(agent_name=WRITER, description="Transfer to Writer to make revisions based on editorial feedback"),
        create_handoff_tool(agent_name=RESEARCHER, description="Transfer to Researcher when facts need verification or more information is needed"),
        create_handoff_tool(agent_name=PLANNER, description="Transfer to Planner if the overall structure needs significant revision"),
    ]

    # Create agent
    agent = create_react_agent(model, tools, prompt=get_agent_prompt("editor"), name=EDITOR)

    return agent
