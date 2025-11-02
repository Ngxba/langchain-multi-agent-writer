"""
Writer Agent for BigData Newsletter System.
"""

from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph_swarm import create_handoff_tool

from config.settings import get_agent_config
from config.agent_names import WRITER, RESEARCHER, EDITOR, DIAGRAM_CREATOR, PLANNER
from prompts.agent_prompts import get_agent_prompt


def create_writer_agent():
    """
    Create the Writer agent.

    The Writer crafts newsletter content with:
    - BigData technical expertise
    - Engaging and detailed writing
    - Clear explanations of complex topics
    - Practical examples and use cases

    Can transfer to: Researcher, Editor, Diagram Creator
    """
    config = get_agent_config("writer")

    # Create model with agent tag
    model = ChatOpenAI(
        model=config.get("model", "gpt-4o"),
        temperature=config.get("temperature", 0.8),
        tags=["writer"]
    )

    # Define tools
    tools = [
        # Handoff tools
        create_handoff_tool(
            agent_name=RESEARCHER,
            description="Transfer to Researcher when more information or research is needed for the content"
        ),
        create_handoff_tool(
            agent_name=EDITOR,
            description="Transfer to Editor once the draft is complete for review and refinement"
        ),
        create_handoff_tool(
            agent_name=DIAGRAM_CREATOR,
            description="Transfer to Diagram Creator to create visual diagrams that enhance the newsletter"
        ),
        create_handoff_tool(
            agent_name=PLANNER,
            description="Transfer to Planner if the content structure needs to be revised"
        )
    ]

    # Create agent
    agent = create_react_agent(
        model,
        tools,
        prompt=get_agent_prompt("writer"),
        name=WRITER
    )

    return agent
