"""
Centralized agent handoff configuration.

This file defines which agents can transfer to which other agents,
making it easy to modify the agent collaboration graph.
"""

from config.agent_names import RESEARCHER, PLANNER, WRITER, EDITOR, DIAGRAM_CREATOR, EIC, RESEARCH_STRATEGIST, RESEARCH_TECHNICAL


# Define handoff connections for each agent
# Format: "source_agent": [("target_agent", "description"), ...]
AGENT_HANDOFFS = {
    RESEARCHER: [
        (PLANNER, "Transfer to Content Planner to structure the research findings into a newsletter plan"),
        (WRITER, "Transfer to Writer when research is complete and content needs to be written"),
        (DIAGRAM_CREATOR, "Transfer to Diagram Creator to visualize complex concepts or architectures"),
    ],
    PLANNER: [
        (RESEARCHER, "Transfer to Researcher when more information is needed for planning"),
        (WRITER, "Transfer to Writer once the content plan is complete and ready for drafting"),
        (EDITOR, "Transfer to Editor to review and validate the content plan"),
    ],
    WRITER: [
        (RESEARCHER, "Transfer to Researcher when more information or research is needed for the content"),
        (EDITOR, "Transfer to Editor once the draft is complete for review and refinement"),
        (DIAGRAM_CREATOR, "Transfer to Diagram Creator to create visual diagrams that enhance the newsletter"),
        (PLANNER, "Transfer to Planner if the content structure needs to be revised"),
    ],
    EDITOR: [
        (WRITER, "Transfer back to Writer for revisions based on editorial feedback"),
        (RESEARCHER, "Transfer to Researcher to gather more information or verify facts"),
        (PLANNER, "Transfer to Planner if the content structure needs significant restructuring"),
    ],
    DIAGRAM_CREATOR: [
        (WRITER, "Transfer back to Writer once the diagram is created so it can be referenced in the newsletter"),
    ],
    EIC: [
        (PLANNER, "Transfer to Planner for content structure and organization"),
        (RESEARCHER, "Transfer to Researcher when more information is needed"),
        (WRITER, "Transfer to Writer for content creation or revisions"),
        (EDITOR, "Transfer to Editor for detailed review and refinement"),
    ],
    RESEARCH_STRATEGIST: [
        (RESEARCH_TECHNICAL, "Transfer to Technical Researcher to execute detailed research based on the content brief"),
    ],
    RESEARCH_TECHNICAL: [
        (RESEARCH_STRATEGIST, "Transfer back to Research Strategist if the brief needs refinement or clarification"),
    ],
}


def get_agent_handoffs(agent_name: str) -> list:
    """
    Get the list of handoff configurations for a specific agent.

    Args:
        agent_name: Name of the agent (from agent_names.py)

    Returns:
        List of tuples: [(target_agent, description), ...]

    Example:
        >>> get_agent_handoffs(RESEARCHER)
        [('Planner', 'Transfer to Content Planner...'), ...]
    """
    return AGENT_HANDOFFS.get(agent_name, [])


def get_all_handoffs() -> dict:
    """
    Get the complete handoff configuration.

    Returns:
        Dictionary mapping agent names to their handoff configurations
    """
    return AGENT_HANDOFFS.copy()


def visualize_handoff_graph() -> str:
    """
    Generate a text visualization of the agent handoff graph.

    Returns:
        String representation of the agent collaboration graph
    """
    graph = "\n" + "=" * 80 + "\n"
    graph += "AGENT HANDOFF GRAPH\n"
    graph += "=" * 80 + "\n\n"

    for agent, handoffs in AGENT_HANDOFFS.items():
        graph += f"📍 {agent}\n"
        for target, desc in handoffs:
            graph += f"   └─→ {target}\n"
            graph += f"       {desc[:70]}...\n" if len(desc) > 70 else f"       {desc}\n"
        graph += "\n"

    graph += "=" * 80 + "\n"
    return graph


# Optional: Define custom handoff configurations for specific use cases
CUSTOM_HANDOFF_PRESETS = {
    "simple": {
        # Simple linear workflow: Planner -> Researcher -> Writer -> Editor
        PLANNER: [(RESEARCHER, "Start research")],
        RESEARCHER: [(WRITER, "Begin writing")],
        WRITER: [(EDITOR, "Review content")],
        EDITOR: [],
        DIAGRAM_CREATOR: [(WRITER, "Return to writer")],
    },
    "full": AGENT_HANDOFFS,  # Full collaboration (default)
}


def get_handoff_preset(preset_name: str = "full") -> dict:
    """
    Get a predefined handoff configuration preset.

    Args:
        preset_name: Name of the preset ("simple", "full")

    Returns:
        Handoff configuration dictionary
    """
    return CUSTOM_HANDOFF_PRESETS.get(preset_name, AGENT_HANDOFFS)
