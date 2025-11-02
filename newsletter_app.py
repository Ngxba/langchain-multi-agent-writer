"""
BigData Newsletter Generator - Main Application Interface

This is the main entry point for generating BigData newsletters using
the multi-agent swarm system.
"""

from dotenv import load_dotenv
from workflows.newsletter_swarm import create_newsletter_swarm
from utils.agent_utils import pretty_print_messages
from utils.newsletter_utils import extract_final_newsletter


def main():
    """Main application entry point."""
    # Load environment variables
    load_dotenv()

    print("\n" + "=" * 80)
    print("📰 BIGDATA NEWSLETTER GENERATOR 📰")
    print("=" * 80)
    print("\nA multi-agent AI system for creating detailed, engaging BigData newsletters")
    print("\nAgents:")
    print("  🔍 Researcher - Gathers latest information")
    print("  📋 Planner - Structures content")
    print("  ✍️  Writer - Crafts engaging content")
    print("  📝 Editor - Reviews and refines")
    print("  📊 Diagram Creator - Visualizes concepts")
    print("=" * 80 + "\n")

    # Create the swarm
    swarm = create_newsletter_swarm(enable_token_tracking=True)

    # Example topic
    topic = "Apache Kafka in 2025: Stream Processing Evolution"

    print(f"\n🎯 Topic: {topic}\n")

    # Generate newsletter
    result = swarm.generate_newsletter(
        topic=topic,
        additional_instructions="Focus on latest features, real-world use cases, and best practices. Include a diagram if helpful."
    )

    # Print interactions
    print("\n📋 AGENT INTERACTIONS:")
    pretty_print_messages(result)

    # Extract and display final newsletter
    print("\n" + "=" * 80)
    print("📰 FINAL NEWSLETTER")
    print("=" * 80 + "\n")

    final_content = extract_final_newsletter(result)
    print(final_content)

    print("\n" + "=" * 80 + "\n")

    # Print token usage
    print("\n💰 TOKEN USAGE:")
    print(swarm.get_compact_summary())

    print("\n📊 DETAILED REPORT:")
    print(swarm.get_token_report())


if __name__ == "__main__":
    main()
