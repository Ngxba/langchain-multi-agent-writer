"""
Tool I/O Contracts for the Newsletter Generation System.

This module defines the input/output schemas for all tools used by agents.
These contracts ensure type safety, validation, and clear API boundaries.

Phase 1 Design - Based on PHASE_1.MD specifications (8 tools defined).
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


# -----------------------------------------------------------------------------
# Enums
# -----------------------------------------------------------------------------


class DiagramFormat(str, Enum):
    """Supported diagram output formats."""

    DRAWIO_XML = "drawio"
    PNG = "png"
    SVG = "svg"


class DiagramType(str, Enum):
    """Supported diagram types."""

    SEQUENCE = "sequence"
    MINDMAP = "mindmap"
    SWIMLANE = "swimlane"
    BLOCK = "block"
    ARCHITECTURE = "architecture"
    DATA_FLOW = "data_flow"


class ReadabilityLevel(str, Enum):
    """Reading level categories."""

    ELEMENTARY = "elementary"  # Grade 1-5
    MIDDLE_SCHOOL = "middle_school"  # Grade 6-8
    HIGH_SCHOOL = "high_school"  # Grade 9-12
    COLLEGE = "college"  # College level
    PROFESSIONAL = "professional"  # Graduate/professional


# -----------------------------------------------------------------------------
# 1. web.search - Web Search Tool
# -----------------------------------------------------------------------------


class WebSearchInput(BaseModel):
    """Input schema for web search."""

    query: str = Field(
        description="Search query string", min_length=2, max_length=500, examples=["Apache Kafka 2025 updates", "Data Mesh best practices"]
    )
    k: int = Field(default=5, description="Number of results to return", ge=1, le=20)
    include_domains: list[str] = Field(default_factory=list, description="Prefer results from these domains")
    exclude_domains: list[str] = Field(default_factory=list, description="Exclude results from these domains")


class WebSearchResult(BaseModel):
    """A single search result."""

    title: str = Field(description="Page title")
    url: str = Field(description="Page URL")
    snippet: str = Field(description="Relevant excerpt")
    domain: str = Field(default="", description="Source domain")
    relevance_score: float = Field(default=0.0, description="Search relevance score")


class WebSearchOutput(BaseModel):
    """Output schema for web search."""

    query: str = Field(description="Original query")
    results: list[WebSearchResult] = Field(description="Search results")
    total_results: int = Field(description="Total results found")
    search_time_ms: int = Field(default=0, description="Search execution time")


# -----------------------------------------------------------------------------
# 2. web.fetch - Web Fetch Tool (HITL Gated for unknown domains)
# -----------------------------------------------------------------------------


class WebFetchInput(BaseModel):
    """Input schema for web fetch."""

    url: str = Field(description="URL to fetch", examples=["https://kafka.apache.org/documentation/"])
    extract_mode: str = Field(default="text", description="Extraction mode: text, markdown, html")
    max_length: int = Field(default=10000, description="Maximum content length to return", ge=100, le=100000)


class WebFetchOutput(BaseModel):
    """Output schema for web fetch."""

    url: str = Field(description="Fetched URL")
    title: str = Field(description="Page title")
    content: str = Field(description="Extracted content")
    snippet: str = Field(description="First 500 chars as snippet")
    status: int = Field(description="HTTP status code")
    content_type: str = Field(default="text/html", description="Content MIME type")
    fetched_at: datetime = Field(default_factory=datetime.now)
    domain: str = Field(description="Source domain")
    domain_trust: str = Field(default="unknown", description="Trust level: high, medium, low, unknown")
    hitl_required: bool = Field(default=False, description="Whether HITL approval was required")
    hitl_approved: Optional[bool] = Field(default=None, description="HITL approval result if required")


# -----------------------------------------------------------------------------
# 3. local.search - Local Document Search Tool
# -----------------------------------------------------------------------------


class LocalSearchInput(BaseModel):
    """Input schema for local document search."""

    query: str = Field(description="Search query", min_length=2)
    top_k: int = Field(default=5, description="Number of results to return", ge=1, le=50)
    file_types: list[str] = Field(default_factory=lambda: ["md", "txt", "pdf"], description="File types to search")
    search_paths: list[str] = Field(default_factory=list, description="Specific paths to search (empty = all)")


class LocalSearchResult(BaseModel):
    """A single local search result."""

    path_or_id: str = Field(description="File path or document ID")
    snippet: str = Field(description="Relevant excerpt")
    relevance_score: float = Field(default=0.0, description="Search relevance")
    file_type: str = Field(default="", description="File extension")
    title: Optional[str] = Field(default=None, description="Document title if available")


class LocalSearchOutput(BaseModel):
    """Output schema for local search."""

    query: str = Field(description="Original query")
    results: list[LocalSearchResult] = Field(description="Search results")
    total_results: int = Field(description="Total results found")


# -----------------------------------------------------------------------------
# 4. citation.builder - Citation Builder Tool
# -----------------------------------------------------------------------------


class ClaimInput(BaseModel):
    """A claim to be cited."""

    claim_id: str = Field(description="Unique claim identifier")
    text: str = Field(description="Claim text")
    category: str = Field(default="general", description="Claim category: technical, statistical, opinion, background")


class SourceInput(BaseModel):
    """A source for citation."""

    source_id: str = Field(description="Unique source identifier")
    url: str = Field(description="Source URL")
    title: str = Field(description="Source title")
    domain: str = Field(description="Source domain")
    is_primary: bool = Field(default=False, description="Is this a primary source?")


class CitationBuilderInput(BaseModel):
    """Input schema for citation builder."""

    claims: list[ClaimInput] = Field(description="Claims to cite")
    sources: list[SourceInput] = Field(description="Available sources")
    min_sources_per_claim: int = Field(default=2, description="Minimum independent sources per claim")


class ClaimCitation(BaseModel):
    """Citation mapping for a claim."""

    claim_id: str = Field(description="Claim identifier")
    source_ids: list[str] = Field(description="Supporting source IDs")
    quality_score: float = Field(description="Citation quality: 1.0 = ideal, 0.0 = insufficient", ge=0.0, le=1.0)
    has_independent_sources: bool = Field(description="Whether sources are from different domains")
    has_primary_source: bool = Field(description="Whether at least one source is primary")
    issues: list[str] = Field(default_factory=list, description="Issues with this citation")


class CitationBuilderOutput(BaseModel):
    """Output schema for citation builder."""

    citations: list[ClaimCitation] = Field(description="Citation mappings")
    overall_quality: float = Field(description="Overall citation quality score", ge=0.0, le=1.0)
    uncited_claims: list[str] = Field(default_factory=list, description="Claim IDs without sufficient citations")
    warnings: list[str] = Field(default_factory=list, description="Citation warnings")


# -----------------------------------------------------------------------------
# 5. drawio.generate - DrawIO Diagram Generation Tool
# -----------------------------------------------------------------------------


class DiagramNode(BaseModel):
    """A node in the diagram."""

    id: str = Field(description="Node identifier")
    label: str = Field(description="Node label/text")
    type: str = Field(default="rectangle", description="Shape type: rectangle, ellipse, diamond, cylinder")
    style: Optional[dict[str, Any]] = Field(default=None, description="Custom style overrides")


class DiagramEdge(BaseModel):
    """An edge/connection in the diagram."""

    source: str = Field(description="Source node ID")
    target: str = Field(description="Target node ID")
    label: Optional[str] = Field(default=None, description="Edge label")
    style: str = Field(default="solid", description="Line style: solid, dashed, dotted")


class DrawioGenerateInput(BaseModel):
    """Input schema for DrawIO diagram generation."""

    intent: str = Field(
        description="What the diagram should illustrate", examples=["Show Kafka producer-consumer flow", "Data lake architecture layers"]
    )
    diagram_type: DiagramType = Field(description="Type of diagram")
    title: str = Field(description="Diagram title")
    nodes: list[DiagramNode] = Field(default_factory=list, description="Predefined nodes (optional)")
    edges: list[DiagramEdge] = Field(default_factory=list, description="Predefined edges (optional)")
    width: int = Field(default=650, description="Target width in pixels (email-friendly)", ge=300, le=1200)


class DrawioGenerateOutput(BaseModel):
    """Output schema for DrawIO diagram generation."""

    xml: str = Field(description="DrawIO XML content")
    preview_notes: str = Field(description="Human-readable description of the diagram")
    node_count: int = Field(description="Number of nodes")
    edge_count: int = Field(description="Number of edges")
    diagram_type: DiagramType = Field(description="Generated diagram type")
    filename_suggestion: str = Field(description="Suggested filename")


# -----------------------------------------------------------------------------
# 6. drawio.export - DrawIO Export Tool
# -----------------------------------------------------------------------------


class DrawioExportInput(BaseModel):
    """Input schema for DrawIO export."""

    xml: str = Field(description="DrawIO XML content")
    format: DiagramFormat = Field(default=DiagramFormat.PNG, description="Export format")
    scale: float = Field(default=1.0, description="Scale factor for export", ge=0.5, le=3.0)


class DrawioExportOutput(BaseModel):
    """Output schema for DrawIO export."""

    png_path_or_b64: str = Field(description="File path or base64-encoded image")
    format: DiagramFormat = Field(description="Export format used")
    width: int = Field(description="Image width in pixels")
    height: int = Field(description="Image height in pixels")
    file_size_bytes: int = Field(description="File size in bytes")


# -----------------------------------------------------------------------------
# 7. seo.readability - SEO/Readability Analysis Tool
# -----------------------------------------------------------------------------


class ReadabilityFlag(BaseModel):
    """A readability issue flag."""

    type: str = Field(description="Issue type: sentence_length, passive_voice, jargon, etc.")
    severity: str = Field(description="Severity: info, warning, error")
    location: Optional[str] = Field(default=None, description="Location in text")
    message: str = Field(description="Issue description")


class ReadabilitySuggestion(BaseModel):
    """A readability improvement suggestion."""

    original: str = Field(description="Original text")
    suggested: str = Field(description="Suggested improvement")
    reason: str = Field(description="Reason for suggestion")


class SeoReadabilityInput(BaseModel):
    """Input schema for readability analysis."""

    markdown: str = Field(description="Markdown content to analyze")
    target_grade_level: int = Field(default=12, description="Target Flesch-Kincaid grade level", ge=6, le=18)
    max_sentence_length: int = Field(default=25, description="Maximum recommended sentence length", ge=15, le=50)


class SeoReadabilityOutput(BaseModel):
    """Output schema for readability analysis."""

    reading_level: ReadabilityLevel = Field(description="Reading level category")
    flesch_kincaid_grade: float = Field(description="Flesch-Kincaid grade level")
    flesch_reading_ease: float = Field(description="Flesch reading ease score (0-100)")
    avg_sentence_length: float = Field(description="Average words per sentence")
    avg_word_length: float = Field(description="Average syllables per word")
    flags: list[ReadabilityFlag] = Field(default_factory=list, description="Readability issues found")
    suggestions: list[ReadabilitySuggestion] = Field(default_factory=list, description="Improvement suggestions")
    word_count: int = Field(description="Total word count")
    sentence_count: int = Field(description="Total sentence count")
    paragraph_count: int = Field(description="Total paragraph count")
    passive_voice_percentage: float = Field(description="Percentage of sentences in passive voice")


# -----------------------------------------------------------------------------
# 8. plagiarism.scan - Plagiarism Scan Tool (HITL Gated if external)
# -----------------------------------------------------------------------------


class PlagiarismMatch(BaseModel):
    """A plagiarism match."""

    matched_text: str = Field(description="Text that matched")
    source_url: str = Field(description="Source URL")
    source_title: str = Field(description="Source title")
    similarity_score: float = Field(description="Similarity percentage", ge=0.0, le=100.0)
    match_type: str = Field(default="exact", description="Match type: exact, paraphrase, structural")


class PlagiarismScanInput(BaseModel):
    """Input schema for plagiarism scan."""

    markdown: str = Field(description="Markdown content to scan")
    threshold: float = Field(default=80.0, description="Similarity threshold to flag", ge=50.0, le=100.0)
    exclude_citations: bool = Field(default=True, description="Exclude properly cited quotes")


class PlagiarismScanOutput(BaseModel):
    """Output schema for plagiarism scan."""

    overall_score: float = Field(description="Overall originality score (100 = fully original)", ge=0.0, le=100.0)
    matches: list[PlagiarismMatch] = Field(default_factory=list, description="Plagiarism matches found")
    scanned_length: int = Field(description="Characters scanned")
    flagged_length: int = Field(description="Characters flagged")
    hitl_required: bool = Field(default=True, description="Whether HITL approval was required (external API)")
    hitl_approved: Optional[bool] = Field(default=None, description="HITL approval result")
    scan_provider: str = Field(default="internal", description="Scan provider: internal, external")


# -----------------------------------------------------------------------------
# Tool Registry - Maps tool names to their I/O schemas
# -----------------------------------------------------------------------------

TOOL_CONTRACTS = {
    "web.search": {
        "input": WebSearchInput,
        "output": WebSearchOutput,
        "hitl_gated": False,
        "description": "Search the web for information. Prefer authority domains.",
    },
    "web.fetch": {
        "input": WebFetchInput,
        "output": WebFetchOutput,
        "hitl_gated": True,  # For unknown domains
        "hitl_condition": "domain_trust == 'unknown' or domain_trust == 'low'",
        "description": "Fetch and extract content from a URL. HITL required for unknown domains.",
    },
    "local.search": {
        "input": LocalSearchInput,
        "output": LocalSearchOutput,
        "hitl_gated": False,
        "description": "Search local documents. Mirrors future Drive/Notion integration.",
    },
    "citation.builder": {
        "input": CitationBuilderInput,
        "output": CitationBuilderOutput,
        "hitl_gated": False,
        "description": "Build citations enforcing >=2 independent sources per claim.",
    },
    "drawio.generate": {
        "input": DrawioGenerateInput,
        "output": DrawioGenerateOutput,
        "hitl_gated": False,
        "description": "Generate DrawIO XML diagrams from intent.",
    },
    "drawio.export": {
        "input": DrawioExportInput,
        "output": DrawioExportOutput,
        "hitl_gated": False,
        "description": "Export DrawIO XML to PNG image.",
    },
    "seo.readability": {
        "input": SeoReadabilityInput,
        "output": SeoReadabilityOutput,
        "hitl_gated": False,
        "description": "Analyze markdown for readability and SEO.",
    },
    "plagiarism.scan": {
        "input": PlagiarismScanInput,
        "output": PlagiarismScanOutput,
        "hitl_gated": True,  # If external API
        "hitl_condition": "scan_provider == 'external'",
        "description": "Scan content for plagiarism. HITL required for external API.",
    },
}


def get_tool_contract(tool_name: str) -> dict[str, Any]:
    """Get the contract for a tool by name."""
    if tool_name not in TOOL_CONTRACTS:
        raise ValueError(f"Unknown tool: {tool_name}. Available: {list(TOOL_CONTRACTS.keys())}")
    return TOOL_CONTRACTS[tool_name]


def validate_tool_input(tool_name: str, input_data: dict[str, Any]) -> BaseModel:
    """Validate input data against tool contract."""
    contract = get_tool_contract(tool_name)
    return contract["input"](**input_data)


def validate_tool_output(tool_name: str, output_data: dict[str, Any]) -> BaseModel:
    """Validate output data against tool contract."""
    contract = get_tool_contract(tool_name)
    return contract["output"](**output_data)
