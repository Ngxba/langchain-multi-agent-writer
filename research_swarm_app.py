"""
Research Swarm Streamlit Application

Interactive chat interface for the Research Strategist and Technical Researcher swarm.
"""

import streamlit as st
import uuid
import json
from datetime import datetime
from dotenv import load_dotenv

from workflows.research_swarm import create_research_swarm, get_swarm_info, load_style_reference

load_dotenv()
# Page configuration
st.set_page_config(page_title="Research Swarm - Vietnamese Tech Newsletter", page_icon="🔬", layout="wide", initial_sidebar_state="expanded")

# Custom CSS
st.markdown(
    """
<style>
    .agent-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: bold;
        margin: 4px 0;
    }
    .strategist-badge {
        background-color: #4CAF50;
        color: white;
    }
    .researcher-badge {
        background-color: #2196F3;
        color: white;
    }
    .tool-call {
        background-color: #FFF3CD;
        border-left: 4px solid #FFC107;
        padding: 8px;
        margin: 8px 0;
        font-family: monospace;
        font-size: 12px;
    }
    .transfer-indicator {
        background-color: #E8F5E9;
        border-left: 4px solid #4CAF50;
        padding: 12px;
        margin: 12px 0;
        font-weight: bold;
    }
    .stChatMessage {
        padding: 1rem;
    }
</style>
""",
    unsafe_allow_html=True,
)


# Initialize session state
if "app" not in st.session_state:
    st.session_state.app = create_research_swarm()
    st.session_state.swarm_info = get_swarm_info()
    st.session_state.style_reference = load_style_reference()

if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []

if "active_agent" not in st.session_state:
    st.session_state.active_agent = "research_strategist"


def get_config():
    """Get the configuration for the swarm."""
    return {
        "configurable": {
            "thread_id": st.session_state.thread_id,
        }
    }


def format_agent_name(agent_name):
    """Format agent name for display."""
    if agent_name == "research_strategist":
        return "🎯 Research Strategist"
    elif agent_name == "research_technical":
        return "🔬 Technical Researcher"
    else:
        return f"🤖 {agent_name}"


def get_agent_badge_class(agent_name):
    """Get CSS class for agent badge."""
    if agent_name == "research_strategist":
        return "strategist-badge"
    elif agent_name == "research_technical":
        return "researcher-badge"
    else:
        return "agent-badge"


def display_message(msg, index):
    """Display a single message in the chat."""
    msg_type = type(msg).__name__

    if msg_type == "HumanMessage":
        with st.chat_message("user", avatar="👤"):
            st.markdown(msg.content)

    elif msg_type == "AIMessage":
        agent_name = getattr(msg, "name", "unknown")
        avatar = "🎯" if agent_name == "research_strategist" else "🔬"

        with st.chat_message("assistant", avatar=avatar):
            # Agent header
            badge_class = get_agent_badge_class(agent_name)
            st.markdown(f'<div class="agent-badge {badge_class}">{format_agent_name(agent_name)}</div>', unsafe_allow_html=True)

            # Tool calls
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tool_call in msg.tool_calls:
                    tool_name = tool_call.get("name", "unknown")

                    if "transfer" in tool_name:
                        target = tool_name.replace("transfer_to_", "").replace("_", " ").title()
                        st.markdown(f'<div class="transfer-indicator">🔄 Transferring to {target}...</div>', unsafe_allow_html=True)
                    else:
                        st.markdown(f'<div class="tool-call">🔧 Using tool: {tool_name}</div>', unsafe_allow_html=True)

            # Message content
            if msg.content:
                # Limit display length for very long content
                content = msg.content
                if len(content) > 5000:
                    with st.expander(f"📄 Show full response ({len(content)} characters)", expanded=False):
                        st.markdown(content)
                    st.markdown(content[:500] + "\n\n*[Content truncated - click above to see full response]*")
                else:
                    st.markdown(content)

    elif msg_type == "ToolMessage":
        tool_name = getattr(msg, "name", "unknown")
        with st.chat_message("assistant", avatar="⚙️"):
            st.markdown(f"**Tool Result:** `{tool_name}`")

            # Show tool result in expander if long
            if len(msg.content) > 200:
                with st.expander("Show result"):
                    st.text(msg.content)
            else:
                st.text(msg.content)


def send_message(user_input):
    """Send a message to the swarm and get response."""
    if not user_input.strip():
        return

    # Add user message to history
    st.session_state.messages.append({"role": "user", "content": user_input})

    # Stream response from swarm
    config = get_config()

    with st.spinner("Agents are processing..."):
        try:
            # Collect all updates
            updates = []
            for ns, update in st.session_state.app.stream(
                {"messages": [{"role": "user", "content": user_input}]},
                config,
                subgraphs=True,
            ):
                updates.append((ns, update))

            # Get final state to extract messages
            state = st.session_state.app.get_state(config)

            # Update messages and active agent
            if hasattr(state, "values"):
                new_messages = state.values.get("messages", [])
                # Only add new messages (skip existing ones)
                st.session_state.messages = new_messages
                st.session_state.active_agent = state.values.get("active_agent", "unknown")

        except Exception as e:
            st.error(f"Error processing message: {str(e)}")
            st.exception(e)


# Sidebar
with st.sidebar:
    st.title("🔬 Research Swarm")
    st.markdown("---")

    # Swarm Info
    info = st.session_state.swarm_info
    st.subheader("About")
    st.write(info["description"])

    st.markdown("---")

    # Agent Info
    st.subheader("Agents")
    for agent in info["agents"]:
        with st.expander(f"🤖 {agent['name'].replace('_', ' ').title()}"):
            st.write(f"**Role:** {agent['role']}")
            st.write("**Capabilities:**")
            for cap in agent["capabilities"]:
                st.write(f"- {cap}")

    st.markdown("---")

    # Current Status
    st.subheader("Status")
    st.write(f"**Active Agent:** {format_agent_name(st.session_state.active_agent)}")
    st.write(f"**Messages:** {len(st.session_state.messages)}")
    st.write(f"**Thread ID:** `{st.session_state.thread_id[:8]}...`")

    st.markdown("---")

    # Actions
    st.subheader("Actions")

    if st.button("🔄 New Conversation", use_container_width=True):
        st.session_state.thread_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.session_state.active_agent = "research_strategist"
        st.rerun()

    if st.button("💾 Export Chat", use_container_width=True):
        export_data = {
            "thread_id": st.session_state.thread_id,
            "timestamp": datetime.now().isoformat(),
            "active_agent": st.session_state.active_agent,
            "messages": [
                {"type": type(msg).__name__, "content": msg.content if hasattr(msg, "content") else str(msg), "name": getattr(msg, "name", None)}
                for msg in st.session_state.messages
            ],
        }
        st.download_button(
            label="📥 Download JSON",
            data=json.dumps(export_data, indent=2, ensure_ascii=False),
            file_name=f"research_swarm_{st.session_state.thread_id[:8]}.json",
            mime="application/json",
            use_container_width=True,
        )

    # Style Reference
    with st.expander("📋 Style Reference"):
        st.json(st.session_state.style_reference)


# Main chat area
st.title("Vietnamese Technical Newsletter Research Swarm")
st.markdown("Interact with the Research Strategist and Technical Researcher to create content briefs and gather technical information.")

# Display example prompts
if len(st.session_state.messages) == 0:
    st.info("👋 **Welcome!** Start by requesting a content brief for a technical topic.")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Example Topics:**")
        example_topics = [
            "Apache Flink - Stream Processing",
            "Redis - In-Memory Database",
            "Kubernetes - Container Orchestration",
            "Apache Kafka - Message Broker",
        ]
        for topic in example_topics:
            if st.button(f"📝 {topic}", key=f"example_{topic}", use_container_width=True):
                example_prompt = f"""Create a comprehensive content brief for a Vietnamese technical newsletter on: {topic}

Context:
- Audience: Vietnamese developers/data engineers (intermediate level)
- Casual Vietnamese tone with technical English terms
- Focus on real-world applications
"""
                send_message(example_prompt)
                st.rerun()

    with col2:
        st.markdown("**Quick Actions:**")
        if st.button("🎯 Custom Topic Request", use_container_width=True):
            st.session_state.show_custom_input = True

# Display chat messages
chat_container = st.container()
with chat_container:
    for i, msg in enumerate(st.session_state.messages):
        display_message(msg, i)

# Chat input
user_input = st.chat_input("Type your message here...")
if user_input:
    send_message(user_input)
    st.rerun()

# Footer
st.markdown("---")
st.caption("🔬 Research Swarm | Vietnamese Technical Newsletter System | Powered by LangGraph")
