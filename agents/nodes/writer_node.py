"""
Writer Node - Transforms research into draft content.

Context: facts[], citations[], style_profile
Produces: draft.md, draft.html, diagram_intents
Tools: seo.readability (optional)

Phase 2 Implementation.
"""

import logging
from datetime import datetime
from typing import Any, Optional

from .base_node import BaseAgentNode

logger = logging.getLogger(__name__)


class WriterNode(BaseAgentNode):
    """
    Writer agent node.

    Transforms researched facts into fluent, engaging markdown content.
    All claims must be anchored to source claim_ids.
    """

    def __init__(self, **kwargs):
        super().__init__(agent_name="writer", **kwargs)

    def get_context_slice(self, state: dict[str, Any]) -> dict[str, Any]:
        """Extract writer's context slice."""
        return {
            "facts": state.get("facts", []),
            "citations": state.get("citations", []),
            "style_profile": state.get("style_profile", {}),
            "diagram_intents": state.get("diagram_intents", []),
            "previous_draft": state.get("artifacts", {}).get("draft.md", {}).get("content"),
            "issues_to_fix": [i for i in state.get("issues", []) if not i.get("resolved")],
        }

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """
        Execute writing phase.

        1. Get context slice
        2. Generate draft from facts
        3. Anchor claims to sources
        4. Check readability (optional)
        5. Update state and handoff
        """
        logger.info("Writer node executing")

        # Get context
        context = self.get_context_slice(state)
        facts = context.get("facts", [])
        citations = context.get("citations", [])
        style_profile = context.get("style_profile", {})

        # Get topic from task
        topic = ""
        if "tasks" in state and state["tasks"]:
            task = state["tasks"][0] if isinstance(state["tasks"], list) else state["tasks"]
            if isinstance(task, dict):
                topic = task.get("topic", "Unknown Topic")

        if not facts:
            logger.warning("No facts to write from")
            # Still produce a draft, but note the limitation
            draft = self._generate_minimal_draft(topic, style_profile)
        else:
            # Generate draft from facts
            draft = self._generate_draft(topic, facts, citations, style_profile)

        # Create diagram intents if needed
        diagram_intents = self._generate_diagram_intents(topic, facts)

        # Store artifacts
        if "artifacts" not in state:
            state["artifacts"] = {}

        state["artifacts"]["draft.md"] = {
            "name": "draft.md",
            "content": draft,
            "content_type": "text/markdown",
            "created_at": datetime.now().isoformat(),
            "created_by": "writer",
            "version": state["artifacts"].get("draft.md", {}).get("version", 0) + 1,
        }

        # Store diagram intents
        state["diagram_intents"] = diagram_intents

        # Optional readability check
        if "seo.readability" in self.tools:
            try:
                readability = self.call_tool("seo.readability", markdown=draft)
                state["readability_check"] = readability
            except Exception as e:
                logger.warning(f"Readability check failed: {e}")

        # Update state
        state["draft_completed"] = True
        state["draft_timestamp"] = datetime.now().isoformat()

        # Handoff to editor
        message = f"Draft complete: {len(draft)} chars, {len(facts)} facts anchored"
        return self.handoff_to("editor", state, message)

    def _generate_draft(
        self,
        topic: str,
        facts: list[dict],
        citations: list[dict],
        style_profile: dict,
    ) -> str:
        """Generate draft markdown from facts."""
        structure = style_profile.get("structure", {})
        if isinstance(structure, dict):
            _ = structure.get("sections", ["hook", "summary", "sections", "key-takeaways", "CTA"])
        else:
            _ = structure if isinstance(structure, list) else ["hook", "summary", "sections", "key-takeaways", "CTA"]

        # Build citation lookup
        citation_lookup = {c.get("source_id", ""): c for c in citations}

        # Start draft
        parts = [
            "---",
            f"title: {topic}",
            "version: 1",
            "created_by: writer",
            f"claim_count: {len(facts)}",
            "---",
            "",
            f"# {topic}",
            "",
        ]

        # Hook section
        if facts:
            hook_fact = facts[0]
            parts.append(f"{hook_fact.get('text', '')}")
            parts.append(f"<!-- claim_id: {hook_fact.get('claim_id', '')} -->")
            parts.append("")

        # Summary section
        parts.append("## Summary")
        parts.append("")
        parts.append(f"This article explores {topic.lower()}, covering key concepts, ")
        parts.append("best practices, and practical applications.")
        parts.append("")

        # Main content sections
        parts.append("## Key Concepts")
        parts.append("")

        for i, fact in enumerate(facts[1:6], 1):  # Use facts 1-5
            text = fact.get("text", "")
            claim_id = fact.get("claim_id", "")
            source_ids = fact.get("source_ids", [])

            parts.append(f"### Point {i}")
            parts.append("")
            parts.append(text)
            parts.append(f"<!-- claim_id: {claim_id} -->")
            parts.append("")

            # Add source references
            if source_ids:
                for sid in source_ids[:2]:
                    citation = citation_lookup.get(sid, {})
                    if citation:
                        title = citation.get("title", "Source")[:50]
                        url = citation.get("url", "")
                        if url:
                            parts.append(f"[{title}]({url})")
                parts.append("")

        # Key Takeaways
        parts.append("## Key Takeaways")
        parts.append("")

        for i, fact in enumerate(facts[:3], 1):
            text = fact.get("text", "")[:100]
            claim_id = fact.get("claim_id", "")
            parts.append(f"- {text}")
            parts.append(f"  <!-- claim_id: {claim_id} -->")

        parts.append("")

        # CTA
        parts.append("## What's Next?")
        parts.append("")
        parts.append(f"To learn more about {topic.lower()}, explore the official documentation ")
        parts.append("and try implementing these concepts in your projects.")
        parts.append("")

        # References
        parts.append("## References")
        parts.append("")
        for citation in citations[:5]:
            title = citation.get("title", "Source")
            url = citation.get("url", "")
            if url:
                parts.append(f"- [{title}]({url})")
        parts.append("")

        return "\n".join(parts)

    def _generate_minimal_draft(self, topic: str, style_profile: dict) -> str:
        """Generate a minimal draft when no facts are available."""
        return f"""---
title: {topic}
version: 1
created_by: writer
claim_count: 0
---

# {topic}

<!-- TODO: Research needed - no facts available -->

## Summary

This article will cover {topic.lower()}.

## Key Concepts

<!-- TODO: Add content based on research -->

## Key Takeaways

- Key point 1
- Key point 2
- Key point 3

## What's Next?

Explore more resources on {topic.lower()}.
"""

    def _generate_diagram_intents(
        self,
        topic: str,
        facts: list[dict],
    ) -> list[dict]:
        """Generate diagram intents based on topic."""
        intents = []

        # Architecture diagram for most topics
        intents.append(
            {
                "intent_id": "DIAG_001",
                "diagram_type": "architecture",
                "title": f"{topic} Architecture Overview",
                "description": f"High-level architecture diagram for {topic}",
                "placement_hint": "After Key Concepts section",
                "nodes": [],
                "edges": [],
            }
        )

        return intents


# Singleton instance
_node: Optional[WriterNode] = None


def get_writer_node() -> WriterNode:
    """Get the writer node instance."""
    global _node
    if _node is None:
        _node = WriterNode()
    return _node


def writer_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    LangGraph node function for writer.

    Args:
        state: Current workflow state

    Returns:
        Updated state
    """
    return get_writer_node().execute(state)
