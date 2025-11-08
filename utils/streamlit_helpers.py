"""
Streamlit helper utilities for the Research Swarm application.
"""

import json
from datetime import datetime
from typing import Any, Dict, List


def format_message_for_display(msg: Any) -> Dict[str, Any]:
    """
    Format a message object for display in Streamlit.

    Args:
        msg: Message object (HumanMessage, AIMessage, ToolMessage)

    Returns:
        Dictionary with formatted message data
    """
    msg_type = type(msg).__name__

    result = {"type": msg_type, "content": getattr(msg, "content", ""), "timestamp": datetime.now().isoformat()}

    if msg_type == "AIMessage":
        result["agent_name"] = getattr(msg, "name", "unknown")
        tool_calls_list: List[Dict[str, Any]] = []

        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tool_call in msg.tool_calls:
                tool_calls_list.append({"name": tool_call.get("name", "unknown"), "args": tool_call.get("args", {})})
        result["tool_calls"] = tool_calls_list
    elif msg_type == "ToolMessage":
        result["tool_name"] = getattr(msg, "name", "unknown")

    return result


def get_conversation_stats(messages: List[Any]) -> Dict[str, Any]:
    """
    Get statistics about the conversation.

    Args:
        messages: List of message objects

    Returns:
        Dictionary with conversation statistics
    """
    stats: Dict[str, Any] = {
        "total_messages": len(messages),
        "user_messages": 0,
        "agent_messages": 0,
        "tool_messages": 0,
        "agents_involved": set(),
        "tools_used": set(),
        "transfers": 0,
        "total_characters": 0,
    }

    for msg in messages:
        msg_type = type(msg).__name__

        if msg_type == "HumanMessage":
            stats["user_messages"] += 1
            stats["total_characters"] += len(msg.content)

        elif msg_type == "AIMessage":
            stats["agent_messages"] += 1
            stats["total_characters"] += len(msg.content) if msg.content else 0

            agent_name = getattr(msg, "name", None)
            if agent_name:
                stats["agents_involved"].add(agent_name)

            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tool_call in msg.tool_calls:
                    tool_name = tool_call.get("name", "")
                    stats["tools_used"].add(tool_name)

                    if "transfer" in tool_name:
                        stats["transfers"] += 1

        elif msg_type == "ToolMessage":
            stats["tool_messages"] += 1
            tool_name = getattr(msg, "name", None)
            if tool_name:
                stats["tools_used"].add(tool_name)

    # Convert sets to lists for JSON serialization
    stats["agents_involved"] = list(stats["agents_involved"])
    stats["tools_used"] = list(stats["tools_used"])

    return stats


def export_conversation(messages: List[Any], thread_id: str, active_agent: str) -> str:
    """
    Export conversation to JSON format.

    Args:
        messages: List of message objects
        thread_id: Thread identifier
        active_agent: Currently active agent name

    Returns:
        JSON string of the conversation
    """
    export_data = {
        "thread_id": thread_id,
        "timestamp": datetime.now().isoformat(),
        "active_agent": active_agent,
        "statistics": get_conversation_stats(messages),
        "messages": [format_message_for_display(msg) for msg in messages],
    }

    return json.dumps(export_data, indent=2, ensure_ascii=False)


def create_topic_request_template(topic: str, context: str | None = None, audience_level: str = "intermediate") -> str:
    """
    Create a formatted topic request for the Research Swarm.

    Args:
        topic: The technical topic to research
        context: Additional context (optional)
        audience_level: beginner, intermediate, or advanced

    Returns:
        Formatted topic request string
    """
    template = f"""Create a comprehensive content brief for a Vietnamese technical newsletter on: {topic}

Context:
- Audience: Vietnamese developers/data engineers ({audience_level} level)
- Casual Vietnamese tone with technical English terms
- Focus on real-world applications and practical examples"""

    if context:
        template += f"\n- {context}"

    template += "\n\nPlease create the brief and transfer to Technical Researcher to gather information."

    return template


def get_agent_color(agent_name: str) -> str:
    """
    Get color code for an agent.

    Args:
        agent_name: Name of the agent

    Returns:
        Hex color code
    """
    colors = {
        "research_strategist": "#4CAF50",  # Green
        "research_technical": "#2196F3",  # Blue
        "researcher_technical": "#2196F3",  # Blue (alternative name)
        "planner": "#FF9800",  # Orange
        "writer": "#9C27B0",  # Purple
        "editor": "#F44336",  # Red
        "diagram_creator": "#00BCD4",  # Cyan
        "eic": "#795548",  # Brown
    }

    return colors.get(agent_name, "#757575")  # Default gray


def format_tool_name(tool_name: str) -> str:
    """
    Format a tool name for display.

    Args:
        tool_name: Raw tool name

    Returns:
        Formatted tool name
    """
    # Handle transfer tools
    if tool_name.startswith("transfer_to_"):
        target = tool_name.replace("transfer_to_", "").replace("_", " ").title()
        return f"🔄 Transfer to {target}"

    # Handle other tools
    tool_display_names = {
        "search_web": "🔍 Web Search",
        "search_flights": "✈️ Flight Search",
        "book_flight": "✈️ Book Flight",
        "search_hotels": "🏨 Hotel Search",
        "book_hotel": "🏨 Book Hotel",
    }

    return tool_display_names.get(tool_name, f"🔧 {tool_name.replace('_', ' ').title()}")


def truncate_content(content: str, max_length: int = 500, show_length: bool = True) -> str:
    """
    Truncate content with ellipsis if too long.

    Args:
        content: Content to truncate
        max_length: Maximum length before truncation
        show_length: Whether to show total length in truncation message

    Returns:
        Truncated content
    """
    if len(content) <= max_length:
        return content

    truncated = content[:max_length].rstrip()

    if show_length:
        return f"{truncated}\n\n*[Content truncated - {len(content)} total characters]*"
    else:
        return f"{truncated}..."


def get_message_summary(messages: List[Any]) -> str:
    """
    Get a brief summary of the conversation.

    Args:
        messages: List of message objects

    Returns:
        Summary string
    """
    stats = get_conversation_stats(messages)

    summary_parts = [
        f"{stats['total_messages']} messages",
        f"{stats['user_messages']} user",
        f"{stats['agent_messages']} agent",
    ]

    if stats["transfers"] > 0:
        summary_parts.append(f"{stats['transfers']} transfers")

    if stats["agents_involved"]:
        agents_str = ", ".join(stats["agents_involved"])
        summary_parts.append(f"Agents: {agents_str}")

    return " | ".join(summary_parts)
