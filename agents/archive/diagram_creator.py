"""
Diagram Creator Agent for BigData Newsletter System.
"""

from langchain_anthropic import ChatAnthropic
from langgraph.prebuilt import create_react_agent
from langgraph_swarm import create_handoff_tool

from config.settings import get_agent_config
from config.agent_names import DIAGRAM_CREATOR
from config.agent_handoffs import get_agent_handoffs
from prompts.agent_prompts import get_agent_prompt
from tools.diagram_tools import create_data_flow_diagram, create_architecture_diagram
from tools.web_search import search_web


def create_diagram_creator_agent():
    """
    Create the Diagram Creator agent.

    The Diagram Creator generates visualizations:
    - Data flow diagrams
    - Architecture diagrams
    - System component diagrams
    - DrawIO-compatible XML format

    Uses Claude Sonnet 4.5 for superior diagram planning and component identification.

    Handoff connections are defined in config/agent_handoffs.py
    """
    config = get_agent_config("diagram_creator")

    # Use Claude Sonnet 4.5 for better diagram understanding
    model = ChatAnthropic(model="claude-sonnet-4-20250514", temperature=config.get("temperature", 0.2), tags=["diagram_creator"])

    # Define tools
    tools = [
        search_web,  # Can search for diagram examples and architecture patterns
        create_data_flow_diagram,
        create_architecture_diagram,
    ]

    # Add handoff tools from centralized configuration
    for target_agent, description in get_agent_handoffs(DIAGRAM_CREATOR):
        tools.append(create_handoff_tool(agent_name=target_agent, description=description))

    # Create agent
    agent = create_react_agent(model, tools, prompt=get_agent_prompt("diagram_creator"), name=DIAGRAM_CREATOR)

    return agent
