"""
Researcher Agent for BigData Newsletter System.
"""

from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph_swarm import create_handoff_tool

from config.settings import get_agent_config
from config.agent_names import RESEARCHER, PLANNER, WRITER, DIAGRAM_CREATOR
from prompts.agent_prompts import get_agent_prompt
from tools.web_search import search_web
from tools.knowledge_base import search_bigdata_knowledge, get_industry_trends, get_industry_statistics


def create_researcher_agent():
    """
    Create the Researcher agent.

    The Researcher gathers information about BigData topics from:
    - Web search for latest news and trends
    - Knowledge base for technical details
    - Industry statistics and trends

    Can transfer to: Planner, Writer, Diagram Creator
    """
    config = get_agent_config("researcher")

    # Create model with agent tag
    model = ChatOpenAI(
        model=config.get("model", "gpt-4o"),
        temperature=config.get("temperature", 0.7),
        tags=["researcher"]
    )

    # Define tools
    tools = [
        search_web,
        search_bigdata_knowledge,
        get_industry_trends,
        get_industry_statistics,
        # Handoff tools
        create_handoff_tool(
            agent_name=PLANNER,
            description="Transfer to Content Planner to structure the research findings into a newsletter plan"
        ),
        create_handoff_tool(
            agent_name=WRITER,
            description="Transfer to Writer when research is complete and content needs to be written"
        ),
        create_handoff_tool(
            agent_name=DIAGRAM_CREATOR,
            description="Transfer to Diagram Creator to visualize complex concepts or architectures"
        )
    ]

    # Create agent
    agent = create_react_agent(
        model,
        tools,
        prompt=get_agent_prompt("researcher"),
        name=RESEARCHER
    )

    return agent
