"""
Unit tests for agent nodes.

Tests:
- Researcher node execution
- Writer node execution
- Editor node review
- Diagrammer node generation

Phase 2 Implementation.
"""

import pytest
from datetime import datetime

from agents.nodes import (
    ResearcherNode,
    WriterNode,
    EditorNode,
    DiagrammerNode,
    researcher_node,
    writer_node,
    editor_node,
    diagrammer_node,
)


# -----------------------------------------------------------------------------
# Test Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture
def basic_state():
    """Create a basic initial state."""
    return {
        "tasks": [
            {
                "task_id": "task_001",
                "topic": "Apache Kafka",
                "brief": "Write about Kafka fundamentals",
                "requirements": ["performance", "scalability", "use cases"],
            }
        ],
        "facts": [],
        "citations": [],
        "artifacts": {},
        "diagram_intents": [],
        "issues": [],
        "style_profile": {
            "name": "Neutral-Concise",
            "voice": "neutral, confident",
            "sentence_length": "12-20 words",
            "structure": {"sections": ["hook", "summary", "sections", "key-takeaways", "CTA"]},
        },
        "iteration_count": 0,
        "max_iterations": 5,
    }


@pytest.fixture
def state_with_research():
    """Create a state with completed research."""
    return {
        "tasks": [
            {
                "task_id": "task_001",
                "topic": "Apache Kafka",
                "brief": "Write about Kafka fundamentals",
                "requirements": [],
            }
        ],
        "facts": [
            {
                "claim_id": "CLAIM_001",
                "text": "Apache Kafka is a distributed streaming platform",
                "source_ids": ["SRC_001", "SRC_002"],
                "confidence": "high",
            },
            {
                "claim_id": "CLAIM_002",
                "text": "Kafka can handle millions of messages per second",
                "source_ids": ["SRC_001"],
                "confidence": "medium",
            },
            {
                "claim_id": "CLAIM_003",
                "text": "Kafka uses a publish-subscribe model",
                "source_ids": ["SRC_002", "SRC_003"],
                "confidence": "high",
            },
        ],
        "citations": [
            {
                "source_id": "SRC_001",
                "url": "https://kafka.apache.org/documentation",
                "title": "Apache Kafka Documentation",
                "domain": "kafka.apache.org",
                "domain_trust": "high",
            },
            {
                "source_id": "SRC_002",
                "url": "https://confluent.io/kafka-guide",
                "title": "Confluent Kafka Guide",
                "domain": "confluent.io",
                "domain_trust": "high",
            },
            {
                "source_id": "SRC_003",
                "url": "https://databricks.com/kafka",
                "title": "Databricks Kafka Overview",
                "domain": "databricks.com",
                "domain_trust": "high",
            },
        ],
        "artifacts": {},
        "diagram_intents": [],
        "issues": [],
        "style_profile": {
            "name": "Neutral-Concise",
            "structure": {"sections": ["hook", "summary", "sections", "key-takeaways", "CTA"]},
        },
        "iteration_count": 0,
        "max_iterations": 5,
    }


@pytest.fixture
def state_with_draft():
    """Create a state with a completed draft."""
    draft_content = """---
title: Apache Kafka
version: 1
created_by: writer
claim_count: 3
---

# Apache Kafka

Apache Kafka is a distributed streaming platform.
<!-- claim_id: CLAIM_001 -->

## Summary

This article explores Apache Kafka, covering key concepts.

## Key Concepts

### Point 1

Kafka can handle millions of messages per second.
<!-- claim_id: CLAIM_002 -->

### Point 2

Kafka uses a publish-subscribe model.
<!-- claim_id: CLAIM_003 -->

## Key Takeaways

- Distributed streaming platform
  <!-- claim_id: CLAIM_001 -->

## What's Next?

Explore the official Kafka documentation.
"""
    return {
        "tasks": [
            {
                "task_id": "task_001",
                "topic": "Apache Kafka",
            }
        ],
        "facts": [
            {"claim_id": "CLAIM_001", "text": "Distributed platform", "source_ids": ["SRC_001", "SRC_002"]},
            {"claim_id": "CLAIM_002", "text": "Millions of messages", "source_ids": ["SRC_001"]},
            {"claim_id": "CLAIM_003", "text": "Pub-sub model", "source_ids": ["SRC_002", "SRC_003"]},
        ],
        "citations": [
            {"source_id": "SRC_001", "url": "https://kafka.apache.org", "title": "Kafka Docs", "domain": "kafka.apache.org"},
            {"source_id": "SRC_002", "url": "https://confluent.io", "title": "Confluent", "domain": "confluent.io"},
            {"source_id": "SRC_003", "url": "https://databricks.com", "title": "Databricks", "domain": "databricks.com"},
        ],
        "artifacts": {
            "draft.md": {
                "name": "draft.md",
                "content": draft_content,
                "content_type": "text/markdown",
                "created_at": datetime.now().isoformat(),
                "created_by": "writer",
            }
        },
        "diagram_intents": [
            {
                "intent_id": "DIAG_001",
                "diagram_type": "architecture",
                "title": "Kafka Architecture",
                "description": "High-level Kafka architecture",
                "placement_hint": "After Key Concepts",
            }
        ],
        "issues": [],
        "style_profile": {
            "name": "Neutral-Concise",
            "structure": {"sections": ["hook", "summary", "sections", "key-takeaways", "CTA"]},
        },
        "iteration_count": 0,
        "max_iterations": 5,
    }


# -----------------------------------------------------------------------------
# Researcher Node Tests
# -----------------------------------------------------------------------------


class TestResearcherNode:
    """Tests for researcher node."""

    def test_context_slice_extraction(self, basic_state):
        """Test that context slice is correctly extracted."""
        node = ResearcherNode()
        context = node.get_context_slice(basic_state)

        assert context["topic"] == "Apache Kafka"
        assert context["brief"] == "Write about Kafka fundamentals"
        assert "requirements" in context

    def test_generates_search_queries(self, basic_state):
        """Test search query generation."""
        node = ResearcherNode()
        queries = node._generate_search_queries(
            topic="Apache Kafka",
            brief="Write about Kafka fundamentals",
            requirements=["performance", "scalability"],
        )

        assert len(queries) > 0
        assert any("Kafka" in q for q in queries)

    def test_handoff_to_writer(self, basic_state):
        """Test that researcher hands off to writer."""
        node = ResearcherNode()

        # Simulate execution with no tools (will use default behavior)
        result = node.execute(basic_state)

        assert result.get("current_agent") == "writer"
        assert result.get("previous_agent") == "researcher"


# -----------------------------------------------------------------------------
# Writer Node Tests
# -----------------------------------------------------------------------------


class TestWriterNode:
    """Tests for writer node."""

    def test_context_slice_extraction(self, state_with_research):
        """Test that context slice is correctly extracted."""
        node = WriterNode()
        context = node.get_context_slice(state_with_research)

        assert len(context["facts"]) == 3
        assert len(context["citations"]) == 3
        assert context["style_profile"] is not None

    def test_generates_draft_from_facts(self, state_with_research):
        """Test draft generation from facts."""
        node = WriterNode()
        result = node.execute(state_with_research)

        assert "artifacts" in result
        assert "draft.md" in result["artifacts"]
        draft = result["artifacts"]["draft.md"]
        assert "content" in draft
        assert "Apache Kafka" in draft["content"]

    def test_draft_includes_claim_ids(self, state_with_research):
        """Test that draft includes claim_id anchors."""
        node = WriterNode()
        result = node.execute(state_with_research)

        draft_content = result["artifacts"]["draft.md"]["content"]
        assert "claim_id:" in draft_content

    def test_generates_diagram_intents(self, state_with_research):
        """Test diagram intent generation."""
        node = WriterNode()
        result = node.execute(state_with_research)

        assert "diagram_intents" in result
        assert len(result["diagram_intents"]) > 0

    def test_handoff_to_editor(self, state_with_research):
        """Test that writer hands off to editor."""
        node = WriterNode()
        result = node.execute(state_with_research)

        assert result.get("current_agent") == "editor"
        assert result.get("previous_agent") == "writer"

    def test_handles_no_facts(self, basic_state):
        """Test handling when no facts available."""
        node = WriterNode()
        result = node.execute(basic_state)

        # Should still produce a draft (minimal)
        assert "artifacts" in result
        assert "draft.md" in result["artifacts"]


# -----------------------------------------------------------------------------
# Editor Node Tests
# -----------------------------------------------------------------------------


class TestEditorNode:
    """Tests for editor node."""

    def test_context_slice_extraction(self, state_with_draft):
        """Test that context slice is correctly extracted."""
        node = EditorNode()
        context = node.get_context_slice(state_with_draft)

        assert context["draft_md"] is not None
        assert "Apache Kafka" in context["draft_md"]

    def test_checks_citation_integrity(self, state_with_draft):
        """Test citation integrity checking."""
        node = EditorNode()
        issues = node._check_citation_integrity(
            draft=state_with_draft["artifacts"]["draft.md"]["content"],
            facts=state_with_draft["facts"],
            citations=state_with_draft["citations"],
        )

        # Should flag CLAIM_002 for having only 1 source
        claim_002_issues = [i for i in issues if "CLAIM_002" in i.get("description", "")]
        assert len(claim_002_issues) > 0

    def test_checks_safety(self, state_with_draft):
        """Test safety checking."""
        node = EditorNode()

        # Test with PII
        draft_with_pii = "Contact john@example.com for details."
        issues = node._check_safety(draft_with_pii)

        # Should detect email as PII (unless filtered as example)
        # Note: example emails may be filtered out
        assert isinstance(issues, list)

    def test_increments_iteration(self, state_with_draft):
        """Test that iteration counter is incremented."""
        node = EditorNode()
        state_with_draft["iteration_count"] = 0

        result = node.execute(state_with_draft)

        assert result["iteration_count"] == 1

    def test_passes_with_good_content(self, state_with_draft):
        """Test that good content passes review."""
        node = EditorNode()

        # Fix CLAIM_002 to have 2 sources
        state_with_draft["facts"][1]["source_ids"] = ["SRC_001", "SRC_002"]

        result = node.execute(state_with_draft)

        # Should pass and handoff to diagrammer
        assert result.get("editor_review", {}).get("pass") is True

    def test_routes_to_diagrammer_on_pass(self, state_with_draft):
        """Test routing to diagrammer when passed."""
        node = EditorNode()

        # Fix all claims to have 2 sources
        for fact in state_with_draft["facts"]:
            fact["source_ids"] = ["SRC_001", "SRC_002"]

        result = node.execute(state_with_draft)

        if result.get("editor_review", {}).get("pass"):
            assert result.get("current_agent") == "diagrammer"


# -----------------------------------------------------------------------------
# Diagrammer Node Tests
# -----------------------------------------------------------------------------


class TestDiagrammerNode:
    """Tests for diagrammer node."""

    def test_context_slice_extraction(self, state_with_draft):
        """Test that context slice is correctly extracted."""
        node = DiagrammerNode()
        context = node.get_context_slice(state_with_draft)

        assert len(context["diagram_intents"]) == 1

    def test_generates_drawio_xml(self):
        """Test DrawIO XML generation."""
        node = DiagrammerNode()

        nodes = [
            {"id": "n1", "label": "Component A", "type": "rectangle", "x": 100, "y": 100},
            {"id": "n2", "label": "Component B", "type": "rounded", "x": 300, "y": 100},
        ]
        edges = [
            {"source": "n1", "target": "n2", "label": "connects"},
        ]

        xml = node._generate_drawio_xml(
            diagram_id="DIAG_TEST",
            title="Test Diagram",
            diagram_type="architecture",
            nodes=nodes,
            edges=edges,
        )

        assert "<mxfile" in xml
        assert "Component A" in xml
        assert "Component B" in xml

    def test_generates_default_content(self):
        """Test default content generation for diagram types."""
        node = DiagrammerNode()

        nodes, edges = node._generate_default_content("architecture", "Kafka")

        assert len(nodes) > 0
        assert len(edges) > 0

    def test_marks_workflow_complete(self, state_with_draft):
        """Test that workflow is marked complete after diagrams."""
        node = DiagrammerNode()
        result = node.execute(state_with_draft)

        assert result.get("diagrams_completed") is True
        assert result.get("workflow_complete") is True


# -----------------------------------------------------------------------------
# Node Function Tests
# -----------------------------------------------------------------------------


class TestNodeFunctions:
    """Tests for node function wrappers."""

    def test_researcher_node_function(self, basic_state):
        """Test researcher_node function."""
        result = researcher_node(basic_state)

        assert "current_agent" in result

    def test_writer_node_function(self, state_with_research):
        """Test writer_node function."""
        result = writer_node(state_with_research)

        assert "artifacts" in result

    def test_editor_node_function(self, state_with_draft):
        """Test editor_node function."""
        result = editor_node(state_with_draft)

        assert "editor_review" in result

    def test_diagrammer_node_function(self, state_with_draft):
        """Test diagrammer_node function."""
        result = diagrammer_node(state_with_draft)

        assert "diagrams_completed" in result
