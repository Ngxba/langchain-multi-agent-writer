"""
Simple Multi-Agent Example (Alice and Bob)

This is a basic demo of the agent swarm pattern with token tracking.

For the full BigData Newsletter Generator system, run:
    python newsletter_app.py

The newsletter system includes:
- 5 specialized agents (Researcher, Planner, Writer, Editor, Diagram Creator)
- Web search and knowledge base tools
- DrawIO diagram generation
- Comprehensive token tracking
"""

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore

from langgraph.prebuilt import create_react_agent
from langgraph_swarm import create_handoff_tool, create_swarm

from token_tracker import AgentTokenTracker

# Load environment variables from .env file
load_dotenv()


print("\n" + "=" * 80)
print("SIMPLE AGENT SWARM DEMO (Alice & Bob)")
print("=" * 80)
print("\nFor the full BigData Newsletter Generator, run: python newsletter_app.py")
print("=" * 80 + "\n")


def pretty_print_messages(result):
    """Pretty print agent interactions in a readable format."""
    print("\n" + "=" * 80)
    print(f"ACTIVE AGENT: {result['active_agent']}")
    print("=" * 80)

    for msg in result['messages']:
        msg_type = type(msg).__name__

        if msg_type == 'HumanMessage':
            print(f"\n👤 USER:")
            print(f"   {msg.content}")

        elif msg_type == 'AIMessage':
            agent_name = getattr(msg, 'name', 'Unknown')
            print(f"\n🤖 {agent_name.upper()}:")

            # Check for tool calls
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                for tool_call in msg.tool_calls:
                    tool_name = tool_call['name']
                    tool_args = tool_call.get('args', {})

                    if 'transfer' in tool_name:
                        target_agent = tool_name.replace('transfer_to_', '').title()
                        print(f"   🔄 Transferring to {target_agent}...")
                    else:
                        print(f"   🔧 Calling tool: {tool_name}")
                        if tool_args:
                            print(f"      Args: {tool_args}")

            # Print response content if available
            if msg.content:
                print(f"   {msg.content}")

        elif msg_type == 'ToolMessage':
            tool_name = getattr(msg, 'name', 'unknown')
            print(f"\n⚙️  TOOL RESULT ({tool_name}):")
            print(f"   {msg.content}")

    print("\n" + "=" * 80 + "\n")

# Create separate models for each agent with tags for tracking
model_alice = ChatOpenAI(model="gpt-4o", tags=["alice"])
model_bob = ChatOpenAI(model="gpt-4o", tags=["bob"])

def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b

alice = create_react_agent(
    model_alice,
    [add, create_handoff_tool(agent_name="Bob")],
    prompt="You are Alice, an addition expert.",
    name="Alice",
)

bob = create_react_agent(
    model_bob,
    [create_handoff_tool(agent_name="Alice", description="Transfer to Alice, she can help with math")],
    prompt="You are Bob, you speak like a pirate.",
    name="Bob",
)

# short-term memory
checkpointer = InMemorySaver()
# long-term memory
store = InMemoryStore()
workflow = create_swarm(
    [alice, bob],
    default_active_agent=alice.name
)
app = workflow.compile(checkpointer=checkpointer, store=store)

# Initialize token tracker
tracker = AgentTokenTracker(model_name="gpt-4o")

# Add tracker to config
config = {
    "configurable": {"thread_id": "1"},
    "callbacks": [tracker]
}

print("\n🎬 TURN 1: User asks to speak to Bob")
turn_1 = app.invoke(
    {"messages": [{"role": "user", "content": "i'd like to speak to Bob"}]},
    config,
)
pretty_print_messages(turn_1)
print(tracker.get_compact_summary())

print("\n🎬 TURN 2: User asks a math question")
turn_2 = app.invoke(
    {"messages": [{"role": "user", "content": "what's 5 + 7?"}]},
    config,
)
pretty_print_messages(turn_2)
print(tracker.get_compact_summary())

# Print final detailed report
print("\n" + "🎯 FINAL SESSION REPORT 🎯")
print(tracker.get_formatted_report(detailed=True))