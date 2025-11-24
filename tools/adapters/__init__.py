"""
Tool Adapters for Newsletter Generation System.

This module provides middleware-wrapped tool implementations
with strict I/O schemas and proper error handling.

Phase 2 Implementation.
"""

from .search_adapter import WebSearchAdapter, search_web
from .fetch_adapter import WebFetchAdapter, fetch_url
from .citation_adapter import CitationBuilderAdapter, build_citations
from .diagram_adapter import DiagramAdapter, generate_diagram, export_diagram
from .readability_adapter import ReadabilityAdapter, check_readability

__all__ = [
    # Adapters
    "WebSearchAdapter",
    "WebFetchAdapter",
    "CitationBuilderAdapter",
    "DiagramAdapter",
    "ReadabilityAdapter",
    # Functions
    "search_web",
    "fetch_url",
    "build_citations",
    "generate_diagram",
    "export_diagram",
    "check_readability",
]
