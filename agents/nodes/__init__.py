"""
Agent Nodes for LangGraph Workflow.

This module provides node functions for each agent department
that can be used in LangGraph workflows.

Phase 2 Implementation.
"""

from .base_node import BaseAgentNode, NodeResult
from .researcher_node import ResearcherNode, researcher_node
from .writer_node import WriterNode, writer_node
from .editor_node import EditorNode, editor_node
from .diagrammer_node import DiagrammerNode, diagrammer_node

__all__ = [
    # Base
    "BaseAgentNode",
    "NodeResult",
    # Nodes
    "ResearcherNode",
    "WriterNode",
    "EditorNode",
    "DiagrammerNode",
    # Functions
    "researcher_node",
    "writer_node",
    "editor_node",
    "diagrammer_node",
]
