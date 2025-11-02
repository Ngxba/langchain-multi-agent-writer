"""
Content Planner Agent for BigData Newsletter System.
"""

from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph_swarm import create_handoff_tool

from config.settings import get_agent_config
from config.agent_names import PLANNER, RESEARCHER, WRITER, EDITOR
from prompts.agent_prompts import get_agent_prompt


def create_planner_agent():
    """
    Create the Content Planner agent.

    The Planner structures newsletters with:
    - Clear section organization
    - Appropriate word count allocation
    - Audience targeting
    - Hook and engagement planning

    Can transfer to: Researcher, Writer, Editor
    """
    config = get_agent_config("planner")

    # Create model with agent tag
    model = ChatOpenAI(
        model=config.get("model", "gpt-4o"),
        temperature=config.get("temperature", 0.5),
        tags=["planner"]
    )

    # Define tools
    tools = [
        # Handoff tools
        create_handoff_tool(
            agent_name=RESEARCHER,
            description="Transfer to Researcher when more information is needed for planning"
        ),
        create_handoff_tool(
            agent_name=WRITER,
            description="Transfer to Writer once the content plan is complete and ready for drafting"
        ),
        create_handoff_tool(
            agent_name=EDITOR,
            description="Transfer to Editor to review and validate the content plan"
        )
    ]

    # Create agent
    agent = create_react_agent(
        model,
        tools,
        prompt=get_agent_prompt("planner"),
        name=PLANNER
    )

    return agent
