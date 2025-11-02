
def pretty_print_messages(result):
    """Pretty print agent interactions in a readable format."""
    print("\n" + "=" * 80)
    print(f"ACTIVE AGENT: {result.get('active_agent', 'Unknown').upper()}")
    print("=" * 80)

    messages = result.get('messages', [])

    for msg in messages:
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

                    if 'transfer' in tool_name or 'handoff' in tool_name:
                        target_agent = tool_name.replace('transfer_to_', '').replace('handoff_to_', '').title()
                        print(f"   🔄 Transferring to {target_agent}...")
                    else:
                        print(f"   🔧 Using tool: {tool_name}")
                        if tool_args:
                            args_str = str(tool_args)[:100]  # Limit length
                            print(f"      {args_str}...")

            # Print response content if available
            if msg.content:
                # Limit very long responses
                content = msg.content
                if len(content) > 500:
                    print(f"   {content[:500]}...")
                    print(f"   [... {len(content) - 500} more characters]")
                else:
                    print(f"   {content}")

        elif msg_type == 'ToolMessage':
            tool_name = getattr(msg, 'name', 'unknown')
            print(f"\n⚙️  TOOL RESULT ({tool_name}):")

            content = msg.content
            if len(content) > 300:
                print(f"   {content[:300]}...")
                print(f"   [... {len(content) - 300} more characters]")
            else:
                print(f"   {content}")

    print("\n" + "=" * 80 + "\n")
