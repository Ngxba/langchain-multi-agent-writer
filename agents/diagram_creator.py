"""
Diagram Creator Agent for BigData Newsletter System.
"""

from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph_swarm import create_handoff_tool

from config.settings import get_agent_config
from config.agent_names import DIAGRAM_CREATOR, WRITER
from prompts.agent_prompts import get_agent_prompt
from tools.diagram_tools import create_data_flow_diagram, create_architecture_diagram


def create_diagram_creator_agent():
    """
    Create the Diagram Creator agent.

    The Diagram Creator generates visualizations:
    - Data flow diagrams
    - Architecture diagrams
    - System component diagrams
    - DrawIO-compatible XML format

    Can transfer to: Writer
    """
    config = get_agent_config("diagram_creator")

    # Create model with agent tag
    model = ChatOpenAI(
        model=config.get("model", "gpt-4o-mini"),
        temperature=config.get("temperature", 0.2),
        tags=["diagram_creator"]
    )

    # Define tools
    tools = [
        create_data_flow_diagram,
        create_architecture_diagram,
        # Handoff tools
        create_handoff_tool(
            agent_name=WRITER,
            description="Transfer back to Writer once the diagram is created so it can be referenced in the newsletter"
        )
    ]

    # Create agent
    agent = create_react_agent(
        model,
        tools,
        prompt=get_agent_prompt("diagram_creator"),
        name=DIAGRAM_CREATOR
    )

    return agent
