"""
Editor Node - Quality enforcement and review.

Context: draft.md, draft.html, citations[], style_profile
Produces: issues[], pass_fail_status, corrected_draft
Tools: seo.readability, plagiarism.scan, citation.builder

Phase 2 Implementation.
"""

import logging
import re
from datetime import datetime
from typing import Any, Optional

from .base_node import BaseAgentNode

logger = logging.getLogger(__name__)


class EditorNode(BaseAgentNode):
    """
    Editor agent node.

    Enforces quality rubrics and determines publication readiness.
    - Citation integrity (>=2 independent sources per claim)
    - Style adherence
    - Readability metrics
    - Safety checks
    """

    def __init__(self, **kwargs):
        super().__init__(agent_name="editor", **kwargs)

    def get_context_slice(self, state: dict[str, Any]) -> dict[str, Any]:
        """Extract editor's context slice."""
        return {
            "draft_md": state.get("artifacts", {}).get("draft.md", {}).get("content"),
            "draft_html": state.get("artifacts", {}).get("draft.html", {}).get("content"),
            "citations": state.get("citations", []),
            "facts": state.get("facts", []),
            "style_profile": state.get("style_profile", {}),
            "iteration_count": state.get("iteration_count", 0),
            "previous_issues": state.get("issues", []),
            "diagram_intents": state.get("diagram_intents", []),
        }

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """
        Execute editorial review.

        1. Get context slice
        2. Check citation integrity
        3. Analyze readability
        4. Verify structure
        5. Scan for safety issues
        6. Determine pass/fail
        7. Handoff appropriately
        """
        logger.info("Editor node executing")

        # Increment iteration
        state = self.increment_iteration(state)

        # Get context
        context = self.get_context_slice(state)
        draft = context.get("draft_md", "")
        citations = context.get("citations", [])
        facts = context.get("facts", [])
        style_profile = context.get("style_profile", {})
        iteration_count = state.get("iteration_count", 1)

        if not draft:
            logger.warning("No draft to review")
            return self.handoff_to("writer", state, "No draft provided for review")

        # Collect all issues
        issues = []

        # 1. Citation integrity check
        citation_issues = self._check_citation_integrity(draft, facts, citations)
        issues.extend(citation_issues)

        # 2. Readability analysis
        readability_issues = self._check_readability(draft, style_profile)
        issues.extend(readability_issues)

        # 3. Structure verification
        structure_issues = self._check_structure(draft, style_profile)
        issues.extend(structure_issues)

        # 4. Safety scan
        safety_issues = self._check_safety(draft)
        issues.extend(safety_issues)

        # Categorize issues
        critical_issues = [i for i in issues if i.get("severity") == "critical"]
        major_issues = [i for i in issues if i.get("severity") == "major"]
        minor_issues = [i for i in issues if i.get("severity") == "minor"]

        # Determine pass/fail
        # FAIL if any critical issues, or too many major issues
        passed = len(critical_issues) == 0 and len(major_issues) <= 2

        # Check iteration limit
        max_iterations = state.get("max_iterations", 5)
        if iteration_count >= max_iterations:
            logger.warning(f"Max iterations ({max_iterations}) reached, forcing pass with issues documented")
            passed = True  # Force pass but document issues

        # Update state
        state["issues"] = issues
        state["editor_review"] = {
            "pass": passed,
            "critical_count": len(critical_issues),
            "major_count": len(major_issues),
            "minor_count": len(minor_issues),
            "iteration": iteration_count,
            "timestamp": datetime.now().isoformat(),
        }

        # Store review artifact
        if "artifacts" not in state:
            state["artifacts"] = {}

        state["artifacts"]["review.json"] = {
            "name": "review.json",
            "content": {
                "pass": passed,
                "issues": issues,
                "metrics": state.get("readability_metrics", {}),
            },
            "content_type": "application/json",
            "created_at": datetime.now().isoformat(),
            "created_by": "editor",
        }

        # Determine next action
        if passed:
            # Check if diagrams are needed
            diagram_intents = context.get("diagram_intents", [])
            if diagram_intents:
                message = f"Review PASSED: {len(minor_issues)} minor issues. Ready for diagrams."
                return self.handoff_to("diagrammer", state, message)
            else:
                # Mark as complete
                state["workflow_complete"] = True
                message = "Review PASSED: Content ready for publication."
                return state
        else:
            # Determine where to send back
            if citation_issues and any(i.get("severity") == "critical" for i in citation_issues):
                # Citation problems - send to researcher
                message = f"Review FAILED: {len(critical_issues)} critical citation issues"
                return self.handoff_to("researcher", state, message)
            else:
                # Content problems - send to writer
                message = f"Review FAILED: {len(critical_issues)} critical, {len(major_issues)} major issues"
                return self.handoff_to("writer", state, message)

    def _check_citation_integrity(
        self,
        draft: str,
        facts: list[dict],
        citations: list[dict],
    ) -> list[dict]:
        """Check citation integrity."""
        issues: list[dict] = []

        # Extract claim IDs from draft
        claim_pattern = r"<!-- claim_id: (CLAIM_[A-Z0-9]+) -->"
        claim_ids_in_draft = re.findall(claim_pattern, draft)

        # Build claim -> sources mapping
        claim_to_sources = {}
        for fact in facts:
            claim_id = fact.get("claim_id", "")
            source_ids = fact.get("source_ids", [])
            claim_to_sources[claim_id] = source_ids

        # Check each claim has >=2 sources
        for claim_id in claim_ids_in_draft:
            source_ids = claim_to_sources.get(claim_id, [])
            if len(source_ids) < 2:
                issues.append(
                    {
                        "issue_id": f"CIT_{len(issues) + 1:03d}",
                        "severity": "critical" if len(source_ids) == 0 else "major",
                        "category": "citation",
                        "title": f"Insufficient sources for {claim_id}",
                        "description": f"Claim {claim_id} has only {len(source_ids)} source(s), requires >=2",
                        "location": f"claim_id: {claim_id}",
                        "resolution": "Add additional independent sources",
                        "resolved": False,
                    }
                )

        # Check domain diversity
        if citations:
            domain_counts: dict[str, int] = {}
            for citation in citations:
                domain = citation.get("domain", "unknown")
                domain_counts[domain] = domain_counts.get(domain, 0) + 1

            total = sum(domain_counts.values())
            for domain, count in domain_counts.items():
                percentage = (count / total) * 100
                if percentage > 60:
                    issues.append(
                        {
                            "issue_id": f"CIT_{len(issues) + 1:03d}",
                            "severity": "major",
                            "category": "citation",
                            "title": "Low domain diversity",
                            "description": f"Domain {domain} represents {percentage:.1f}% of sources (>60%)",
                            "location": "citations",
                            "resolution": "Add sources from other domains",
                            "resolved": False,
                        }
                    )

        return issues

    def _check_readability(
        self,
        draft: str,
        style_profile: dict,
    ) -> list[dict]:
        """Check readability metrics."""
        issues: list[dict] = []

        # Use seo.readability tool if available
        if "seo.readability" in self.tools:
            try:
                metrics = self.call_tool("seo.readability", markdown=draft)

                # Check Flesch-Kincaid grade level
                target_grade = style_profile.get("reading_level", 10)
                actual_grade = metrics.get("fk_grade", 0)

                if abs(actual_grade - target_grade) > 2:
                    issues.append(
                        {
                            "issue_id": f"READ_{len(issues) + 1:03d}",
                            "severity": "major",
                            "category": "readability",
                            "title": "Reading level mismatch",
                            "description": f"FK Grade {actual_grade:.1f} vs target {target_grade}",
                            "location": "entire draft",
                            "resolution": "Adjust sentence complexity",
                            "resolved": False,
                        }
                    )

                # Check passive voice
                passive_pct = metrics.get("passive_voice_pct", 0)
                if passive_pct > 20:
                    issues.append(
                        {
                            "issue_id": f"READ_{len(issues) + 1:03d}",
                            "severity": "minor",
                            "category": "readability",
                            "title": "High passive voice usage",
                            "description": f"Passive voice at {passive_pct:.1f}% (target <20%)",
                            "location": "entire draft",
                            "resolution": "Convert passive to active voice",
                            "resolved": False,
                        }
                    )

            except Exception as e:
                logger.warning(f"Readability check failed: {e}")

        # Basic sentence length check
        sentences = re.split(r"[.!?]+", draft)
        sentences = [s.strip() for s in sentences if s.strip()]

        if sentences:
            avg_words = sum(len(s.split()) for s in sentences) / len(sentences)
            target_range = style_profile.get("sentence_length", "12-20 words")

            # Parse target range
            try:
                if "-" in str(target_range):
                    parts = str(target_range).replace("words", "").strip().split("-")
                    min_words = int(parts[0])
                    max_words = int(parts[1])

                    if avg_words < min_words or avg_words > max_words:
                        issues.append(
                            {
                                "issue_id": f"READ_{len(issues) + 1:03d}",
                                "severity": "minor",
                                "category": "readability",
                                "title": "Sentence length outside range",
                                "description": f"Avg {avg_words:.1f} words vs target {target_range}",
                                "location": "entire draft",
                                "resolution": "Adjust sentence lengths",
                                "resolved": False,
                            }
                        )
            except (ValueError, IndexError):
                pass  # Skip if can't parse target

        return issues

    def _check_structure(
        self,
        draft: str,
        style_profile: dict,
    ) -> list[dict]:
        """Check structure against style profile."""
        issues: list[dict] = []

        # Get expected structure
        structure = style_profile.get("structure", {})
        if isinstance(structure, dict):
            expected_sections = structure.get("sections", ["hook", "summary", "sections", "key-takeaways", "CTA"])
        else:
            expected_sections = structure if isinstance(structure, list) else []

        # Map section names to patterns
        section_patterns = {
            "hook": r"^#\s+[^\n]+\n\n[^\#]",  # Title followed by non-heading text
            "summary": r"##\s+(Summary|Executive Summary|Overview)",
            "sections": r"##\s+\w+",  # Any ## heading
            "key-takeaways": r"##\s+(Key Takeaways|Takeaways|Key Points)",
            "CTA": r"##\s+(What's Next|Next Steps|Call to Action|CTA)",
        }

        for section in expected_sections:
            pattern = section_patterns.get(section.lower())
            if pattern and not re.search(pattern, draft, re.IGNORECASE | re.MULTILINE):
                issues.append(
                    {
                        "issue_id": f"STRUCT_{len(issues) + 1:03d}",
                        "severity": "major" if section in ["summary", "key-takeaways"] else "minor",
                        "category": "structure",
                        "title": f"Missing section: {section}",
                        "description": f"Expected section '{section}' not found in draft",
                        "location": "document structure",
                        "resolution": f"Add {section} section",
                        "resolved": False,
                    }
                )

        return issues

    def _check_safety(self, draft: str) -> list[dict]:
        """Check for safety issues."""
        issues: list[dict] = []

        # PII patterns
        pii_patterns = {
            "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
            "phone": r"\b(\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
            "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
        }

        for pii_type, pattern in pii_patterns.items():
            matches = re.findall(pattern, draft)
            if matches:
                # Filter out common false positives
                if pii_type == "email":
                    # Skip example/placeholder emails
                    matches = [m for m in matches if not any(x in m.lower() for x in ["example", "test", "sample", "noreply"])]

                if matches:
                    issues.append(
                        {
                            "issue_id": f"SAFE_{len(issues) + 1:03d}",
                            "severity": "critical",
                            "category": "safety",
                            "title": f"Potential PII detected: {pii_type}",
                            "description": f"Found {len(matches)} potential {pii_type} pattern(s)",
                            "location": "draft content",
                            "resolution": "Remove or mask PII",
                            "resolved": False,
                        }
                    )

        # Risky advice patterns
        risky_patterns = [
            (r"(?i)\b(never|always)\s+(?:use|do|run)\b.*(?:production|live|real)", "Absolute advice for production"),
            (r"(?i)\b(disable|turn off)\s+(?:security|ssl|tls|authentication|firewall)\b", "Security disabling advice"),
        ]

        for pattern, description in risky_patterns:
            if re.search(pattern, draft):
                issues.append(
                    {
                        "issue_id": f"SAFE_{len(issues) + 1:03d}",
                        "severity": "major",
                        "category": "safety",
                        "title": "Risky advice detected",
                        "description": description,
                        "location": "draft content",
                        "resolution": "Add appropriate disclaimers or rephrase",
                        "resolved": False,
                    }
                )

        return issues


# Singleton instance
_node: Optional[EditorNode] = None


def get_editor_node() -> EditorNode:
    """Get the editor node instance."""
    global _node
    if _node is None:
        _node = EditorNode()
    return _node


def editor_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    LangGraph node function for editor.

    Args:
        state: Current workflow state

    Returns:
        Updated state
    """
    return get_editor_node().execute(state)
