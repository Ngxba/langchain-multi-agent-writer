"""
Simple test for the EIC (Editor-in-Chief) Agent.
"""

from dotenv import load_dotenv
from langgraph.errors import ParentCommand

from agents.eic import create_eic_agent
from utils.agent_utils import pretty_print_messages
from utils.token_tracker import AgentTokenTracker

# Load environment variables
load_dotenv()

# Create EIC agent
eic = create_eic_agent()

# Initialize token tracker
tracker = AgentTokenTracker(model_name="gpt-4o")
config = {"configurable": {"thread_id": "eic-test-1"}, "callbacks": [tracker]}

# Test message
test_message = """Please review this newsletter plan for Apache Kafka:

Topic: Apache Kafka - Distributed Streaming Platform
Audience: Data engineers and architects
Word count: 800-1000 words

Proposed Structure:
1. Introduction - Why Kafka matters in modern data architecture
2. Core Concepts - Messages, Topics, Partitions
3. Architecture - Brokers, Producers, Consumers
4. Use Cases - Real-time analytics, Event sourcing
5. Best Practices - Configuration, monitoring, scaling

Is this plan ready for the team to execute?"""

test_message2 = "Please write newsletter for how Data Quality works in AirBnb"

print("\n" + "=" * 80)
print("Testing EIC Agent")
print("=" * 80 + "\n")

try:
    result = eic.invoke({"messages": [{"role": "user", "content": test_message2}]}, config=config)
    pretty_print_messages(result, limit_content=False)
except ParentCommand as cmd:
    # Expected - agent tried to hand off to another agent
    print("Note: Agent attempted handoff (expected when running in isolation)\n")

    if hasattr(cmd, "update") and "messages" in cmd.update:
        result = {"messages": cmd.update["messages"], "active_agent": cmd.update.get("active_agent", "eic")}
        pretty_print_messages(result, limit_content=True, content_limit=1000)

# Print token usage
print(tracker.get_formatted_report())
