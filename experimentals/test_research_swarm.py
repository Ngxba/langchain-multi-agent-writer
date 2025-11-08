"""
Test the interaction between Research Strategist and Technical Researcher agents.

This test demonstrates the two-agent workflow:
1. Research Strategist creates a comprehensive content brief
2. Technical Researcher gathers detailed technical information based on the brief
"""

import json
from dotenv import load_dotenv
from langgraph.checkpoint.memory import MemorySaver
from langgraph_swarm import create_swarm

from agents.research_strategist import create_research_strategist_agent
from agents.research_technical import create_research_technical_agent
from utils.agent_utils import pretty_print_messages, write_result_to_file
from utils.token_tracker import AgentTokenTracker
from config.agent_names import RESEARCH_STRATEGIST

# Load environment variables
load_dotenv()

# Load style reference
with open("prompts/style_reference.json", "r", encoding="utf-8") as f:
    style_reference = json.load(f)

print("\n" + "=" * 80)
print("RESEARCH SWARM TEST: Strategist → Technical Researcher")
print("=" * 80 + "\n")

# Create both research agents
print("Creating Research Strategist agent...")
strategist_agent = create_research_strategist_agent()

print("Creating Technical Researcher agent...")
technical_agent = create_research_technical_agent()

# Create the swarm with both agents
print("Creating research swarm...\n")
swarm = create_swarm(
    agents=[strategist_agent, technical_agent],
    default_active_agent=RESEARCH_STRATEGIST,  # Start with Strategist
)

# Compile the swarm with checkpointer
checkpointer = MemorySaver()
swarm = swarm.compile(checkpointer=checkpointer)

# Initialize token tracker
tracker = AgentTokenTracker(model_name="gpt-4o")
config = {"configurable": {"thread_id": "research-swarm-test-1"}, "callbacks": [tracker]}

# Test message for the Research Strategist
test_message = f"""Create a comprehensive content brief for a Vietnamese technical newsletter on the following topic:

**Topic:** Apache Flink - Real-Time Stream Processing Framework

**Context:**
- Our audience has already read our Kafka article and understands distributed systems basics
- They are Vietnamese developers/data engineers (intermediate to advanced level)
- Previous article maintained casual Vietnamese tone with technical English terms

**Style Reference:**
{json.dumps(style_reference, ensure_ascii=False, indent=2)}
"""

# Run the swarm
result = swarm.invoke({"messages": [{"role": "user", "content": test_message}]}, config=config)
# Print all messages with agent transitions
pretty_print_messages(result, limit_content=True, content_limit=300)

print(tracker.get_formatted_report())

# Count agent transitions
messages = result.get("messages", [])
agent_sequence = []  # type: ignore
for msg in messages:
    if hasattr(msg, "name") and msg.name:
        if not agent_sequence or agent_sequence[-1] != msg.name:
            agent_sequence.append(msg.name)

print(f"Agent execution sequence: {' → '.join(agent_sequence)}")
print(f"Total messages: {len(messages)}")
print(f"Active agent at end: {result.get('active_agent', 'unknown')}")

# Write result to file
print("\n" + "=" * 80)
output_file = write_result_to_file(result)
print(f"✅ Results written to: {output_file}")
print("=" * 80 + "\n")
