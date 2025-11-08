"""
Technical Researcher Agent for Vietnamese Technical Newsletter System.

This agent executes deep technical research based on content briefs from the
Research Strategist, gathering facts, examples, and documentation.
"""

from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph_swarm import create_handoff_tool

from config.settings import get_agent_config
from config.agent_names import RESEARCH_TECHNICAL
from config.agent_handoffs import get_agent_handoffs
from prompts.agent_prompts import get_agent_prompt
from tools.web_search import search_web


def create_research_technical_agent():
    """
    Create the Technical Researcher agent.

    The Technical Researcher is the information gatherer who:
    - Executes research based on the content brief from Research Strategist
    - Searches for official documentation and technical specifications
    - Finds real-world examples and use cases (especially Asian/Vietnamese companies)
    - Gathers performance data, benchmarks, and statistics
    - Locates comparison information with related technologies
    - Identifies expert blog posts and authoritative sources
    - Collects Vietnamese community discussions and perspectives

    Research outputs include:
    - Technical facts with sources (official docs, Apache websites, etc.)
    - Real-world case studies with specific numbers/metrics
    - Architecture patterns and best practices
    - Performance characteristics (throughput, latency, scalability)
    - Technology comparisons (e.g., Flink vs Spark Streaming)
    - Vietnamese/SEA region examples when available
    - References and documentation links

    The gathered research is formatted as structured notes that will be used by
    downstream agents (Storyteller, Technical Writer) to create the newsletter.

    Handoff connections are defined in config/agent_handoffs.py
    """
    config = get_agent_config(RESEARCH_TECHNICAL)

    # Create model with agent tag
    model = ChatOpenAI(model=config.get("model", "gpt-4o"), temperature=config.get("temperature", 0.2), tags=[RESEARCH_TECHNICAL])

    # Define tools
    tools = [
        search_web,
    ]

    # Add handoff tools from centralized configuration
    for target_agent, description in get_agent_handoffs(RESEARCH_TECHNICAL):
        tools.append(create_handoff_tool(agent_name=target_agent, description=description))

    # Create agent
    agent = create_react_agent(model, tools, prompt=get_agent_prompt(RESEARCH_TECHNICAL), name=RESEARCH_TECHNICAL)

    return agent
