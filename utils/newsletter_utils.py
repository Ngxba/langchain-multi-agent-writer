def extract_final_newsletter(result) -> str:
    """Extract the final newsletter content from the result."""
    messages = result.get("messages", [])

    # Look for the last substantial AI message
    for msg in reversed(messages):
        if type(msg).__name__ == "AIMessage" and msg.content:
            # Skip transfer-only messages
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                has_content = bool(msg.content.strip())
                has_only_transfers = all("transfer" in tc["name"] or "handoff" in tc["name"] for tc in msg.tool_calls)
                if has_only_transfers and not has_content:
                    continue

            return msg.content

    return "No newsletter content generated."
