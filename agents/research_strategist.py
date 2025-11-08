"""
Research Strategist Agent for Vietnamese Technical Newsletter System.

This agent is the FIRST agent in the content creation pipeline, responsible for
analyzing topics and creating comprehensive content briefs that guide all other agents.
"""

from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph_swarm import create_handoff_tool

from config.settings import get_agent_config
from config.agent_names import RESEARCH_STRATEGIST
from config.agent_handoffs import get_agent_handoffs
from prompts.agent_prompts import get_agent_prompt
from tools.web_search import search_web


def create_research_strategist_agent():
    """
    Create the Research Strategist agent.

    The Research Strategist is the strategic architect who:
    - Analyzes raw topic requests and transforms them into detailed content briefs
    - Defines clear learning objectives and narrative structure
    - Plans audience engagement and identifies required research
    - Sets quality guidelines and success criteria for downstream agents
    - Uses web search to understand current market relevance and trends
    - Ensures content maintains the "Liam Tech Talk Explainer" style DNA

    This agent outputs comprehensive briefs that include:
    - Target audience profile and pain points
    - Narrative structure (hook, core concepts, closing)
    - Technical requirements and terminology handling
    - Visual/diagram specifications
    - Research needs and sources to consult
    - Style guidelines for Vietnamese audience

    Handoff connections are defined in config/agent_handoffs.py
    """
    config = get_agent_config(RESEARCH_STRATEGIST)

    # Create model with agent tag
    model = ChatOpenAI(model=config.get("model", "gpt-4o"), temperature=config.get("temperature", 0.2), tags=[RESEARCH_STRATEGIST])

    # Define tools
    tools = [
        search_web,
    ]

    # Add handoff tools from centralized configuration
    for target_agent, description in get_agent_handoffs(RESEARCH_STRATEGIST):
        tools.append(create_handoff_tool(agent_name=target_agent, description=description))

    # Create agent
    agent = create_react_agent(model, tools, prompt=get_agent_prompt(RESEARCH_STRATEGIST), name=RESEARCH_STRATEGIST)

    return agent
