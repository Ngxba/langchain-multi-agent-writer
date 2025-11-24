"""
Shared Agent State Schema for the Newsletter Generation System.

This module defines the unified typed state container that all agents share.
The state is designed to be service-friendly and can be lifted into backend
services without changing semantics.

Phase 1 Design - Based on PHASE_1.MD specifications.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


# -----------------------------------------------------------------------------
# Enums
# -----------------------------------------------------------------------------


class ConfidenceLevel(str, Enum):
    """Confidence level for claims/facts."""

    HIGH = "high"  # Multiple authoritative sources
    MEDIUM = "medium"  # Single authoritative or multiple secondary sources
    LOW = "low"  # Background information, single secondary source
    UNVERIFIED = "unverified"  # Needs verification


class ApprovalStatus(str, Enum):
    """HITL approval status."""

    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    SKIPPED = "skipped"


class DiagramType(str, Enum):
    """Supported diagram types."""

    SEQUENCE = "sequence"
    MINDMAP = "mindmap"
    SWIMLANE = "swimlane"
    BLOCK = "block"
    ARCHITECTURE = "architecture"
    DATA_FLOW = "data_flow"


class TaskStatus(str, Enum):
    """Status of a task in the workflow."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    FAILED = "failed"


# -----------------------------------------------------------------------------
# Core Data Models
# -----------------------------------------------------------------------------


class Task(BaseModel):
    """A structured task/request in the workflow."""

    task_id: str = Field(description="Unique identifier for the task")
    topic: str = Field(description="Main topic for the newsletter")
    brief: Optional[str] = Field(default=None, description="Content brief/summary")
    requirements: list[str] = Field(default_factory=list, description="Specific requirements")
    constraints: list[str] = Field(default_factory=list, description="Constraints to follow")
    style_profile_id: Optional[str] = Field(default=None, description="Style profile to use")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="Current task status")
    created_at: datetime = Field(default_factory=datetime.now)


class Citation(BaseModel):
    """A canonical source reference."""

    source_id: str = Field(description="Unique identifier for this source")
    url: str = Field(description="Source URL")
    title: str = Field(description="Source title")
    snippet: str = Field(default="", description="Relevant excerpt from source")
    domain: str = Field(default="", description="Source domain (e.g., 'kafka.apache.org')")
    domain_trust: str = Field(default="unknown", description="Trust level: high, medium, low, unknown")
    accessed_at: datetime = Field(default_factory=datetime.now, description="When source was accessed")
    is_primary: bool = Field(default=False, description="Is this a primary/official source?")


class Fact(BaseModel):
    """A normalized claim extracted from research."""

    claim_id: str = Field(description="Unique identifier for this claim")
    text: str = Field(description="The claim/fact statement")
    quote: Optional[str] = Field(default=None, description="Direct quote from source if available")
    source_ids: list[str] = Field(default_factory=list, description="Citation source_ids supporting this claim")
    confidence: ConfidenceLevel = Field(default=ConfidenceLevel.UNVERIFIED)
    category: str = Field(default="general", description="Category: technical, statistical, opinion, background")
    requires_verification: bool = Field(default=True, description="Whether this needs independent verification")


class Approval(BaseModel):
    """A HITL approval decision."""

    approval_id: str = Field(description="Unique identifier")
    action: str = Field(description="What action required approval (e.g., 'fetch_unknown_domain')")
    target: str = Field(description="What was being approved (e.g., URL)")
    status: ApprovalStatus = Field(default=ApprovalStatus.PENDING)
    rationale: Optional[str] = Field(default=None, description="User's reason for decision")
    decided_at: Optional[datetime] = Field(default=None)
    decided_by: str = Field(default="system", description="Who made the decision")


class DiagramIntent(BaseModel):
    """Intent for diagram generation."""

    intent_id: str = Field(description="Unique identifier")
    diagram_type: DiagramType = Field(description="Type of diagram to generate")
    title: str = Field(description="Diagram title")
    description: str = Field(description="What the diagram should illustrate")
    nodes: list[dict[str, Any]] = Field(default_factory=list, description="Nodes/components")
    edges: list[dict[str, Any]] = Field(default_factory=list, description="Connections between nodes")
    placement_hint: Optional[str] = Field(default=None, description="Where in doc to place diagram")


class Artifact(BaseModel):
    """Generated content artifact."""

    name: str = Field(description="Artifact name (e.g., 'draft.md')")
    content: str = Field(description="Artifact content")
    content_type: str = Field(default="text/markdown", description="MIME type")
    created_at: datetime = Field(default_factory=datetime.now)
    created_by: str = Field(default="", description="Agent that created this")
    version: int = Field(default=1, description="Version number")


class QualityIssue(BaseModel):
    """A quality issue found during editing."""

    issue_id: str = Field(description="Unique identifier")
    severity: str = Field(description="critical, major, minor")
    category: str = Field(description="Category: citation, style, readability, factual, pii, risk")
    description: str = Field(description="Description of the issue")
    location: Optional[str] = Field(default=None, description="Where in doc the issue is")
    suggestion: Optional[str] = Field(default=None, description="Suggested fix")
    resolved: bool = Field(default=False)


class TokenUsage(BaseModel):
    """Token usage and cost tracking."""

    total_input_tokens: int = Field(default=0)
    total_output_tokens: int = Field(default=0)
    total_cost_usd: float = Field(default=0.0)
    by_agent: dict[str, dict[str, Any]] = Field(default_factory=dict, description="Per-agent breakdown: {agent: {input, output, cost}}")
    by_model: dict[str, dict[str, Any]] = Field(default_factory=dict, description="Per-model breakdown: {model: {input, output, cost}}")


# -----------------------------------------------------------------------------
# Run Request / Input Schema
# -----------------------------------------------------------------------------


class RunRequest(BaseModel):
    """
    Input schema for starting a newsletter generation run.
    This is what the user/API provides to kick off the workflow.
    """

    topic: str = Field(description="Main topic for the newsletter")
    brief: Optional[str] = Field(default=None, description="Optional content brief")
    requirements: list[str] = Field(default_factory=list, description="Specific requirements")
    style_profile_id: Optional[str] = Field(default=None, description="Style profile to use")
    sources: list[str] = Field(default_factory=list, description="Pre-provided URLs or file paths")
    publish: bool = Field(default=False, description="Whether to publish after generation")
    max_iterations: int = Field(default=5, description="Max edit loops")
    thread_id: Optional[str] = Field(default=None, description="Thread ID for conversation history")


# -----------------------------------------------------------------------------
# Main Agent State
# -----------------------------------------------------------------------------


class AgentState(BaseModel):
    """
    Unified Agent State - Single typed container shared by all agents.

    This is the core state that flows through the LangGraph workflow.
    Each agent reads/writes specific slices of this state based on their role.

    Context Slicing (who sees what):
    - Researcher: topic, brief, requirements → produces facts[], citations[]
    - Writer: facts[], citations[], style_profile → produces draft.md, draft.html
    - Editor: draft.*, citations[], style_profile → produces corrected draft, issues[]
    - Diagrammer: diagram_intents → produces diagrams[]
    """

    # --- Conversational State ---
    messages: list[dict[str, Any]] = Field(default_factory=list, description="Conversational turns in LangGraph message format")

    # --- Task State ---
    tasks: list[Task] = Field(default_factory=list, description="Structured tasks/requests")
    current_task_id: Optional[str] = Field(default=None, description="ID of the currently active task")

    # --- Research State ---
    facts: list[Fact] = Field(default_factory=list, description="Normalized claims extracted from research")
    citations: list[Citation] = Field(default_factory=list, description="Canonical sources with metadata")

    # --- Artifact State ---
    artifacts: dict[str, Artifact] = Field(default_factory=dict, description="Generated artifacts keyed by name (draft.md, draft.html, etc.)")
    diagram_intents: list[DiagramIntent] = Field(default_factory=list, description="Diagram generation intents")
    diagrams: list[dict[str, Any]] = Field(default_factory=list, description="Generated diagram XMLs and metadata")

    # --- Quality State ---
    issues: list[QualityIssue] = Field(default_factory=list, description="Quality issues found during editing")
    editor_pass: bool = Field(default=False, description="Whether editor has approved the draft")
    iteration_count: int = Field(default=0, description="Number of edit iterations")

    # --- HITL State ---
    approvals: list[Approval] = Field(default_factory=list, description="HITL approval decisions")
    pending_approval: Optional[Approval] = Field(default=None, description="Currently pending approval (blocks workflow)")

    # --- Style State ---
    style_profile_id: Optional[str] = Field(default=None, description="Active style profile ID")
    style_profile: Optional[dict[str, Any]] = Field(default=None, description="Loaded style profile data")

    # --- Metering State ---
    token_usage: TokenUsage = Field(default_factory=TokenUsage, description="Token usage and cost tracking")

    # --- Workflow Metadata ---
    run_id: Optional[str] = Field(default=None, description="Unique run identifier")
    started_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)
    current_agent: Optional[str] = Field(default=None, description="Currently active agent")
    workflow_status: str = Field(default="initialized", description="Overall workflow status")
    fallback_used: bool = Field(default=False, description="Whether fallback model was used")
    error_message: Optional[str] = Field(default=None, description="Error if workflow failed")

    class Config:
        """Pydantic config."""

        extra = "allow"  # Allow extra fields for extensibility


# -----------------------------------------------------------------------------
# Stop Conditions
# -----------------------------------------------------------------------------


def check_stop_conditions(state: AgentState, max_iterations: int = 5) -> tuple[bool, str]:
    """
    Check if the workflow should stop.

    Stop Conditions:
    1. artifacts["draft.md"] present AND editor_pass=True
    2. iteration_count >= max_iterations
    3. Unrecoverable error

    Returns:
        Tuple of (should_stop, reason)
    """
    # Check for draft completion
    if "draft.md" in state.artifacts and state.editor_pass:
        return True, "completed"

    # Check iteration limit
    if state.iteration_count >= max_iterations:
        return True, "max_iterations_reached"

    # Check for errors
    if state.workflow_status == "failed":
        return True, f"failed: {state.error_message}"

    return False, "continue"


# -----------------------------------------------------------------------------
# State Slicers (for context engineering per agent)
# -----------------------------------------------------------------------------


def slice_for_researcher(state: AgentState) -> dict[str, Any]:
    """Extract the state slice that Researcher needs."""
    current_task = None
    if state.current_task_id:
        for task in state.tasks:
            if task.task_id == state.current_task_id:
                current_task = task
                break

    return {
        "topic": current_task.topic if current_task else None,
        "brief": current_task.brief if current_task else None,
        "requirements": current_task.requirements if current_task else [],
        "style_constraints": state.style_profile.get("do_not_use", []) if state.style_profile else [],
        "existing_citations": [c.model_dump() for c in state.citations],
        "existing_facts": [f.model_dump() for f in state.facts],
    }


def slice_for_writer(state: AgentState) -> dict[str, Any]:
    """Extract the state slice that Writer needs."""
    return {
        "facts": [f.model_dump() for f in state.facts],
        "citations": [c.model_dump() for c in state.citations],
        "style_profile": state.style_profile,
        "diagram_intents": [d.model_dump() for d in state.diagram_intents],
        "previous_draft": state.artifacts["draft.md"].content if "draft.md" in state.artifacts else None,
        "issues_to_fix": [i.model_dump() for i in state.issues if not i.resolved],
    }


def slice_for_editor(state: AgentState) -> dict[str, Any]:
    """Extract the state slice that Editor needs."""
    return {
        "draft_md": state.artifacts["draft.md"].content if "draft.md" in state.artifacts else None,
        "draft_html": state.artifacts["draft.html"].content if "draft.html" in state.artifacts else None,
        "citations": [c.model_dump() for c in state.citations],
        "style_profile": state.style_profile,
        "iteration_count": state.iteration_count,
        "previous_issues": [i.model_dump() for i in state.issues],
    }


def slice_for_diagrammer(state: AgentState) -> dict[str, Any]:
    """Extract the state slice that Diagrammer needs."""
    # Get relevant section text for context
    draft_content = state.artifacts["draft.md"].content if "draft.md" in state.artifacts else ""

    return {
        "diagram_intents": [d.model_dump() for d in state.diagram_intents],
        "draft_sections": draft_content,  # Diagrammer may need context
        "existing_diagrams": state.diagrams,
    }
