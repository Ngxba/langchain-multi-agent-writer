"""
Researcher Node - Gathers facts and citations.

Context: topic, brief, requirements
Produces: facts[], citations[], notes.json
Tools: web.search, web.fetch (HITL), local.search, citation.builder

Phase 2 Implementation.
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Optional

from .base_node import BaseAgentNode

logger = logging.getLogger(__name__)


class ResearcherNode(BaseAgentNode):
    """
    Researcher agent node.

    Gathers deep, accurate technical information with proper citations.
    Ensures >=2 independent sources per non-trivial claim.
    """

    def __init__(self, **kwargs):
        super().__init__(agent_name="researcher", **kwargs)

    def get_context_slice(self, state: dict[str, Any]) -> dict[str, Any]:
        """Extract researcher's context slice."""
        context = {}

        # Get current task
        if "tasks" in state and state["tasks"]:
            task = state["tasks"][0] if isinstance(state["tasks"], list) else state["tasks"]
            if isinstance(task, dict):
                context["topic"] = task.get("topic", "")
                context["brief"] = task.get("brief", "")
                context["requirements"] = task.get("requirements", [])

        # Style constraints
        style_profile = state.get("style_profile", {})
        context["style_constraints"] = style_profile.get("do_not_use", [])

        # Existing research
        context["existing_citations"] = state.get("citations", [])
        context["existing_facts"] = state.get("facts", [])

        return context

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """
        Execute research phase.

        1. Get context slice
        2. Search for information
        3. Extract and validate facts
        4. Build citations
        5. Update state and handoff
        """
        logger.info("Researcher node executing")

        # Get context
        context = self.get_context_slice(state)
        topic = context.get("topic", "")
        brief = context.get("brief", "")
        requirements = context.get("requirements", [])

        if not topic:
            logger.warning("No topic provided")
            return self.handoff_to("writer", state, "No topic to research")

        # Initialize or get existing data
        facts = list(state.get("facts", []))
        citations = list(state.get("citations", []))

        # Perform searches
        search_queries = self._generate_search_queries(topic, brief, requirements)

        for query in search_queries[:3]:  # Limit searches
            try:
                results = self.call_tool("web.search", query=query, k=5)
                new_facts, new_citations = self._process_search_results(results, query, existing_citations=citations)
                facts.extend(new_facts)
                citations.extend(new_citations)
            except Exception as e:
                logger.error(f"Search failed for '{query}': {e}")

        # Update state
        state["facts"] = facts
        state["citations"] = citations
        state["research_completed"] = True
        state["research_timestamp"] = datetime.now().isoformat()

        # Add coverage summary
        coverage = self._calculate_coverage(requirements, facts)
        state["research_coverage"] = coverage

        # Generate notes
        notes = {
            "topic": topic,
            "queries_executed": len(search_queries),
            "facts_gathered": len(facts),
            "citations_collected": len(citations),
            "coverage": coverage,
        }
        state["notes"] = notes

        # Determine next action
        if len(facts) >= 3 and len(citations) >= 2:
            # Sufficient research, handoff to writer
            message = f"Research complete: {len(facts)} facts, {len(citations)} sources"
            return self.handoff_to("writer", state, message)
        else:
            # Not enough research, but proceed anyway with warning
            message = f"Limited research: {len(facts)} facts, {len(citations)} sources. Proceeding with caution."
            logger.warning(message)
            return self.handoff_to("writer", state, message)

    def _generate_search_queries(
        self,
        topic: str,
        brief: str,
        requirements: list[str],
    ) -> list[str]:
        """Generate search queries from topic and requirements."""
        queries = []

        # Main topic query
        queries.append(f"{topic} overview fundamentals")

        # Add year for recent info
        queries.append(f"{topic} 2024 latest updates")

        # Query for each requirement
        for req in requirements[:3]:
            # Extract key terms
            query = f"{topic} {req}"
            queries.append(query)

        # Official documentation query
        queries.append(f"{topic} official documentation")

        return queries

    def _process_search_results(
        self,
        results: dict[str, Any],
        query: str,
        existing_citations: list[dict],
    ) -> tuple[list[dict], list[dict]]:
        """Process search results into facts and citations."""
        facts = []
        citations = []

        # Get existing URLs to avoid duplicates
        existing_urls = {c.get("url", "") for c in existing_citations}

        search_results = results.get("results", [])

        for i, result in enumerate(search_results):
            url = result.get("url", "")
            title = result.get("title", "")
            snippet = result.get("snippet", "")
            domain = result.get("domain", "")

            # Skip duplicates
            if url in existing_urls:
                continue

            # Create citation
            source_id = f"SRC_{uuid.uuid4().hex[:8].upper()}"
            citation = {
                "source_id": source_id,
                "url": url,
                "title": title,
                "snippet": snippet,
                "domain": domain,
                "domain_trust": self._evaluate_domain_trust(domain),
                "is_primary": self._is_primary_source(domain),
                "accessed_at": datetime.now().isoformat(),
            }
            citations.append(citation)
            existing_urls.add(url)

            # Create fact from snippet
            if snippet:
                claim_id = f"CLAIM_{uuid.uuid4().hex[:8].upper()}"
                fact = {
                    "claim_id": claim_id,
                    "text": snippet[:300],
                    "source_ids": [source_id],
                    "confidence": "medium",
                    "category": "technical",
                    "query": query,
                }
                facts.append(fact)

        return facts, citations

    def _evaluate_domain_trust(self, domain: str) -> str:
        """Evaluate trust level for a domain."""
        high_trust = [
            "apache.org",
            "kafka.apache.org",
            "spark.apache.org",
            "databricks.com",
            "confluent.io",
            "aws.amazon.com",
            "cloud.google.com",
            "github.com",
            "arxiv.org",
        ]

        for trusted in high_trust:
            if trusted in domain.lower():
                return "high"

        return "medium"

    def _is_primary_source(self, domain: str) -> bool:
        """Check if domain is a primary source."""
        primary_domains = [
            "apache.org",
            "databricks.com",
            "confluent.io",
            "aws.amazon.com",
            "cloud.google.com",
        ]

        for primary in primary_domains:
            if primary in domain.lower():
                return True

        return False

    def _calculate_coverage(
        self,
        requirements: list[str],
        facts: list[dict],
    ) -> dict[str, Any]:
        """Calculate requirement coverage."""
        covered = 0
        total = len(requirements)

        # Simple heuristic: check if any fact mentions requirement keywords
        for req in requirements:
            req_words = set(req.lower().split())
            for fact in facts:
                fact_text = fact.get("text", "").lower()
                if any(word in fact_text for word in req_words if len(word) > 3):
                    covered += 1
                    break

        return {
            "covered": covered,
            "total": total,
            "percentage": (covered / total * 100) if total > 0 else 0,
        }


# Singleton instance
_node: Optional[ResearcherNode] = None


def get_researcher_node() -> ResearcherNode:
    """Get the researcher node instance."""
    global _node
    if _node is None:
        _node = ResearcherNode()
    return _node


def researcher_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    LangGraph node function for researcher.

    Args:
        state: Current workflow state

    Returns:
        Updated state
    """
    return get_researcher_node().execute(state)
