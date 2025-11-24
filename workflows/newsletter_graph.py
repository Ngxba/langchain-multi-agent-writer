"""
Newsletter Generation LangGraph Workflow.

This module defines the LangGraph workflow for newsletter generation
using the 4-department agent system with middleware integration.

Phase 2 Implementation.
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Callable, Literal, Optional, Union

from langgraph.graph import StateGraph, END

from agents.nodes import (
    researcher_node,
    writer_node,
    editor_node,
    diagrammer_node,
)
from middleware.chain import MiddlewareChain, SimpleMiddlewareChain, get_middleware_chain

# Type alias for middleware chain types
MiddlewareChainType = Union[MiddlewareChain, SimpleMiddlewareChain]

logger = logging.getLogger(__name__)


# Type alias for node names
NodeName = Literal["researcher", "writer", "editor", "diagrammer"]


def create_newsletter_graph(
    middleware_chain: Optional[MiddlewareChainType] = None,
) -> StateGraph:
    """
    Create the newsletter generation LangGraph workflow.

    Workflow:
        researcher -> writer -> editor -> (diagrammer | END)
                           ^         |
                           +----<----+ (if FAIL)

    Args:
        middleware_chain: Optional middleware chain for request/response processing

    Returns:
        Compiled StateGraph
    """
    # Use provided middleware or get default
    chain = middleware_chain or get_middleware_chain()

    # Create state graph
    graph = StateGraph(dict)

    # Add nodes with middleware wrapping
    graph.add_node("researcher", _wrap_with_middleware(researcher_node, "researcher", chain))
    graph.add_node("writer", _wrap_with_middleware(writer_node, "writer", chain))
    graph.add_node("editor", _wrap_with_middleware(editor_node, "editor", chain))
    graph.add_node("diagrammer", _wrap_with_middleware(diagrammer_node, "diagrammer", chain))

    # Add entry point
    graph.set_entry_point("researcher")

    # Add edges
    # Researcher always goes to Writer
    graph.add_edge("researcher", "writer")

    # Writer always goes to Editor
    graph.add_edge("writer", "editor")

    # Editor routes based on pass/fail
    graph.add_conditional_edges(
        "editor",
        _route_after_editor,
        {
            "diagrammer": "diagrammer",
            "writer": "writer",
            "researcher": "researcher",
            "end": END,
        },
    )

    # Diagrammer goes to END
    graph.add_edge("diagrammer", END)

    return graph


def _wrap_with_middleware(
    node_func: Callable[[dict[str, Any]], dict[str, Any]],
    agent_name: str,
    chain: MiddlewareChainType,
) -> Callable[[dict[str, Any]], dict[str, Any]]:
    """Wrap a node function with middleware processing."""

    def wrapped(state: dict[str, Any]) -> dict[str, Any]:
        # Pre-process through middleware
        try:
            processed_state = chain.process_request(state, agent_name)
        except Exception as e:
            logger.error(f"Middleware pre-processing failed: {e}")
            processed_state = state

        # Execute node
        result = node_func(processed_state)

        # Post-process through middleware
        try:
            final_state = chain.process_response(result, agent_name)
        except Exception as e:
            logger.error(f"Middleware post-processing failed: {e}")
            final_state = result

        return final_state

    wrapped.__name__ = f"{agent_name}_node"
    return wrapped


def _route_after_editor(state: dict[str, Any]) -> str:
    """
    Determine next node after Editor.

    Routing logic:
    - If passed and has diagram intents -> diagrammer
    - If passed and no diagram intents -> end
    - If failed with citation issues -> researcher
    - If failed with content issues -> writer
    """
    # Check if workflow is marked complete
    if state.get("workflow_complete"):
        return "end"

    # Check editor review result
    editor_review = state.get("editor_review", {})
    passed = editor_review.get("pass", False)

    if passed:
        # Check for diagram intents
        diagram_intents = state.get("diagram_intents", [])
        if diagram_intents and not state.get("diagrams_completed"):
            return "diagrammer"
        return "end"
    else:
        # Route based on next_agent in state
        next_agent = state.get("current_agent", "writer")
        if next_agent == "researcher":
            return "researcher"
        return "writer"


def create_initial_state(
    topic: str,
    brief: Optional[str] = None,
    requirements: Optional[list[str]] = None,
    style_profile: Optional[dict] = None,
    max_iterations: int = 5,
) -> dict[str, Any]:
    """
    Create initial state for a newsletter generation run.

    Args:
        topic: Main topic for the newsletter
        brief: Optional content brief
        requirements: Specific requirements
        style_profile: Style profile to use
        max_iterations: Maximum edit iterations

    Returns:
        Initial state dict
    """
    run_id = f"run_{uuid.uuid4().hex[:12]}"
    task_id = f"task_{uuid.uuid4().hex[:8]}"

    # Create task
    task = {
        "task_id": task_id,
        "topic": topic,
        "brief": brief or f"Write a comprehensive article about {topic}",
        "requirements": requirements or [],
        "constraints": [],
        "status": "in_progress",
        "created_at": datetime.now().isoformat(),
    }

    # Default style profile if not provided
    if style_profile is None:
        style_profile = {
            "name": "Neutral-Concise",
            "voice": "neutral, confident, helpful",
            "sentence_length": "12-20 words",
            "structure": {"sections": ["hook", "summary", "sections", "key-takeaways", "CTA"]},
            "do_not_use": ["sensational claims", "vague sources"],
            "citation_policy": ">=2 independent sources for non-trivial claims",
        }

    return {
        # Task state
        "tasks": [task],
        "current_task_id": task_id,
        # Research state
        "facts": [],
        "citations": [],
        # Artifact state
        "artifacts": {},
        "diagram_intents": [],
        "diagrams": [],
        # Quality state
        "issues": [],
        "editor_pass": False,
        "iteration_count": 0,
        # HITL state
        "approvals": [],
        "pending_approval": None,
        # Style state
        "style_profile": style_profile,
        # Workflow metadata
        "run_id": run_id,
        "started_at": datetime.now().isoformat(),
        "current_agent": "researcher",
        "workflow_status": "running",
        "max_iterations": max_iterations,
        # Messages
        "messages": [],
        # Handoffs tracking
        "handoffs": [],
    }


class NewsletterWorkflow:
    """
    High-level interface for newsletter generation workflow.

    Provides a simple API for running the newsletter generation workflow
    with proper initialization and result extraction.
    """

    def __init__(
        self,
        middleware_chain: Optional[MiddlewareChainType] = None,
        checkpointer: Optional[Any] = None,
    ):
        """
        Initialize the workflow.

        Args:
            middleware_chain: Optional middleware chain
            checkpointer: Optional LangGraph checkpointer for persistence
        """
        self.middleware_chain = middleware_chain or get_middleware_chain()
        self.checkpointer = checkpointer
        self._graph = None

    @property
    def graph(self) -> StateGraph:
        """Get or create the compiled graph."""
        if self._graph is None:
            graph = create_newsletter_graph(self.middleware_chain)
            compile_kwargs = {}
            if self.checkpointer:
                compile_kwargs["checkpointer"] = self.checkpointer
            self._graph = graph.compile(**compile_kwargs)
        return self._graph

    def generate(
        self,
        topic: str,
        brief: Optional[str] = None,
        requirements: Optional[list[str]] = None,
        style_profile: Optional[dict] = None,
        max_iterations: int = 5,
        config: Optional[dict] = None,
    ) -> dict[str, Any]:
        """
        Generate a newsletter on the given topic.

        Args:
            topic: Main topic for the newsletter
            brief: Optional content brief
            requirements: Specific requirements
            style_profile: Style profile to use
            max_iterations: Maximum edit iterations
            config: Optional LangGraph config

        Returns:
            Final workflow state with generated content
        """
        # Create initial state
        initial_state = create_initial_state(
            topic=topic,
            brief=brief,
            requirements=requirements,
            style_profile=style_profile,
            max_iterations=max_iterations,
        )

        # Run the graph
        config = config or {}
        if "configurable" not in config:
            config["configurable"] = {}
        if "thread_id" not in config["configurable"]:
            config["configurable"]["thread_id"] = initial_state["run_id"]

        logger.info(f"Starting newsletter generation for topic: {topic}")

        try:
            # Invoke the graph
            final_state = self.graph.invoke(initial_state, config=config)

            # Mark completion
            final_state["workflow_status"] = "completed"
            final_state["completed_at"] = datetime.now().isoformat()

            logger.info(f"Newsletter generation completed for topic: {topic}")

        except Exception as e:
            logger.error(f"Newsletter generation failed: {e}")
            final_state = initial_state
            final_state["workflow_status"] = "failed"
            final_state["error_message"] = str(e)
            final_state["completed_at"] = datetime.now().isoformat()

        return final_state

    def extract_results(self, state: dict[str, Any]) -> dict[str, Any]:
        """
        Extract results from final state.

        Args:
            state: Final workflow state

        Returns:
            Dictionary with extracted results
        """
        return {
            "status": state.get("workflow_status"),
            "run_id": state.get("run_id"),
            # Content
            "draft_md": state.get("artifacts", {}).get("draft.md", {}).get("content"),
            "draft_html": state.get("artifacts", {}).get("draft.html", {}).get("content"),
            # Research
            "facts_count": len(state.get("facts", [])),
            "citations_count": len(state.get("citations", [])),
            "citations": state.get("citations", []),
            # Quality
            "editor_pass": state.get("editor_review", {}).get("pass", False),
            "issues": state.get("issues", []),
            "iteration_count": state.get("iteration_count", 0),
            # Diagrams
            "diagrams": state.get("diagrams", []),
            "placement_notes": state.get("placement_notes", []),
            # Metadata
            "started_at": state.get("started_at"),
            "completed_at": state.get("completed_at"),
            "handoffs": state.get("handoffs", []),
            # Errors
            "error": state.get("error_message"),
        }


# Convenience function for quick generation
def generate_newsletter(
    topic: str,
    brief: Optional[str] = None,
    requirements: Optional[list[str]] = None,
    style_profile: Optional[dict] = None,
    max_iterations: int = 5,
) -> dict[str, Any]:
    """
    Convenience function to generate a newsletter.

    Args:
        topic: Main topic for the newsletter
        brief: Optional content brief
        requirements: Specific requirements
        style_profile: Style profile to use
        max_iterations: Maximum edit iterations

    Returns:
        Final workflow state
    """
    workflow = NewsletterWorkflow()
    return workflow.generate(
        topic=topic,
        brief=brief,
        requirements=requirements,
        style_profile=style_profile,
        max_iterations=max_iterations,
    )
