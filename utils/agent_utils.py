import os
import sys
from datetime import datetime
from io import StringIO


def pretty_print_messages(result, limit_content: bool = True, content_limit: int = 500):
    """Pretty print agent interactions in a readable format.

    Args:
        result (dict): The agent result containing messages.
        limit_content (bool): Whether to limit printed content length.
        content_limit (int): Maximum number of characters to display if limiting.
    """
    print("\n" + "=" * 80)
    print(f"ACTIVE AGENT: {result.get('active_agent', 'Unknown').upper()}")
    print("=" * 80)

    messages = result.get("messages", [])

    for msg in messages:
        msg_type = type(msg).__name__

        if msg_type == "HumanMessage":
            print("\n👤 USER:")
            content = msg.content
            if limit_content and len(content) > content_limit:
                print(f"   {content[:content_limit]}...")
                print(f"   [... {len(content) - content_limit} more characters]")
            else:
                print(f"   {content}")

        elif msg_type == "AIMessage":
            agent_name = getattr(msg, "name", "Unknown")
            print(f"\n🤖 {agent_name.upper()}:")

            # Check for tool calls
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tool_call in msg.tool_calls:
                    tool_name = tool_call["name"]
                    tool_args = tool_call.get("args", {})

                    if "transfer" in tool_name or "handoff" in tool_name:
                        target_agent = tool_name.replace("transfer_to_", "").replace("handoff_to_", "").title()
                        print(f"   🔄 Transferring to {target_agent}...")
                    else:
                        print(f"   🔧 Using tool: {tool_name}")
                        if tool_args:
                            args_str = str(tool_args)
                            if limit_content and len(args_str) > content_limit:
                                print(f"      {args_str[:content_limit]}...")
                                print(f"      [... {len(args_str) - content_limit} more characters]")
                            else:
                                print(f"      {args_str}")

            # Print response content
            if msg.content:
                content = msg.content
                if limit_content and len(content) > content_limit:
                    print(f"   {content[:content_limit]}...")
                    print(f"   [... {len(content) - content_limit} more characters]")
                else:
                    print(f"   {content}")

        elif msg_type == "ToolMessage":
            tool_name = getattr(msg, "name", "unknown")
            print(f"\n⚙️  TOOL RESULT ({tool_name}):")
            content = msg.content
            if limit_content and len(content) > content_limit:
                print(f"   {content[:content_limit]}...")
                print(f"   [... {len(content) - content_limit} more characters]")
            else:
                print(f"   {content}")

    print("\n" + "=" * 80 + "\n")


def write_result_to_file(result, output_dir="outputs", filename_prefix="research_swarm"):
    """
    Write swarm result to a formatted text file using pretty_print_messages.

    Args:
        result: The result dictionary from swarm.invoke()
        output_dir: Directory to save output files (default: "outputs")
        filename_prefix: Prefix for the output filename

    Returns:
        str: Path to the created file
    """
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Create filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{filename_prefix}_{timestamp}.txt"
    filepath = os.path.join(output_dir, filename)

    # Capture output from pretty_print_messages
    old_stdout = sys.stdout
    sys.stdout = buffer = StringIO()

    try:
        # Use existing pretty_print_messages function
        pretty_print_messages(result, limit_content=False)

        # Add summary section
        messages = result.get("messages", [])
        agent_sequence = []
        agent_messages = {}

        for msg in messages:
            if hasattr(msg, "name") and msg.name and type(msg).__name__ == "AIMessage":
                agent_messages[msg.name] = agent_messages.get(msg.name, 0) + 1
                if not agent_sequence or agent_sequence[-1] != msg.name:
                    agent_sequence.append(msg.name)

        print("=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"\nAgent execution sequence: {' → '.join(agent_sequence)}")
        print("\nAgent activity:")
        for agent, count in agent_messages.items():
            print(f"   {agent}: {count} message(s)")
        print(f"\nTotal messages: {len(messages)}")
        print(f"Final active agent: {result.get('active_agent', 'unknown')}")
        print("\n" + "=" * 80 + "\n")

        # Get captured output
        output = buffer.getvalue()
    finally:
        # Restore stdout
        sys.stdout = old_stdout

    # Write to file with header
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("=" * 80 + "\n")
        f.write("RESEARCH SWARM EXECUTION RESULTS\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")
        f.write(output)

    return filepath
