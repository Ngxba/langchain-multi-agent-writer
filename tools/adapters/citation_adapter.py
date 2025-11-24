"""
Citation Builder Adapter - Builds and validates citations for claims.

Not HITL gated.

Phase 2 Implementation.
"""

import logging
from typing import Any

from tools.contracts import (
    CitationBuilderInput,
    CitationBuilderOutput,
    ClaimCitation,
    ClaimInput,
    SourceInput,
)

logger = logging.getLogger(__name__)


class CitationBuilderAdapter:
    """
    Adapter for citation building functionality.

    Validates that claims have sufficient citations and
    enforces the >=2 independent sources rule.
    """

    def __init__(self, min_sources_per_claim: int = 2):
        self.min_sources_per_claim = min_sources_per_claim

    def build(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Build and validate citations for claims.

        Args:
            input_data: Dict matching CitationBuilderInput schema

        Returns:
            Dict matching CitationBuilderOutput schema
        """
        # Validate input
        try:
            validated_input = CitationBuilderInput(**input_data)
        except Exception as e:
            logger.error(f"Invalid citation input: {e}")
            raise ValueError(f"Invalid citation input: {e}")

        min_sources = validated_input.min_sources_per_claim or self.min_sources_per_claim

        logger.info(f"Building citations for {len(validated_input.claims)} claims")

        # Build source lookup
        sources_by_id = {s.source_id: s for s in validated_input.sources}

        # Build domain lookup for independence check
        domains_by_source: dict[str, str] = {}
        for source in validated_input.sources:
            domains_by_source[source.source_id] = source.domain

        # Process each claim
        citations: list[ClaimCitation] = []
        uncited_claims: list[str] = []
        total_quality = 0.0

        for claim in validated_input.claims:
            citation = self._process_claim(
                claim,
                sources_by_id,
                domains_by_source,
                min_sources,
            )
            citations.append(citation)

            if not citation.source_ids:
                uncited_claims.append(claim.claim_id)

            total_quality += citation.quality_score

        # Calculate overall quality
        overall_quality = total_quality / len(citations) if citations else 0.0

        # Generate warnings
        warnings = []
        if uncited_claims:
            warnings.append(f"{len(uncited_claims)} claims have no citations")

        low_quality = [c for c in citations if c.quality_score < 0.5]
        if low_quality:
            warnings.append(f"{len(low_quality)} claims have low citation quality")

        # Create output
        output = CitationBuilderOutput(
            citations=citations,
            overall_quality=overall_quality,
            uncited_claims=uncited_claims,
            warnings=warnings,
        )

        return output.model_dump()

    def _process_claim(
        self,
        claim: ClaimInput,
        sources_by_id: dict[str, SourceInput],
        domains_by_source: dict[str, str],
        min_sources: int,
    ) -> ClaimCitation:
        """Process a single claim and build its citation."""
        issues = []

        # For now, we don't have source_ids on claims from input
        # In real implementation, this would come from the research phase
        # Here we simulate by checking available sources

        # Get source IDs (in real impl, this would be provided)
        source_ids: list[str] = []

        # Check source count (used implicitly in logic below)
        _ = len(source_ids) >= min_sources

        # Check independence (different domains)
        domains = set()
        for sid in source_ids:
            if sid in domains_by_source:
                domains.add(domains_by_source[sid])

        has_independent = len(domains) >= min(min_sources, len(source_ids))

        # Check for primary source
        has_primary = any(sources_by_id.get(sid, SourceInput(source_id="", url="", title="", domain="")).is_primary for sid in source_ids)

        # Build issues list
        if not source_ids:
            issues.append("No sources linked to this claim")
        elif len(source_ids) < min_sources:
            issues.append(f"Only {len(source_ids)} sources, need {min_sources}")

        if source_ids and not has_independent:
            issues.append("Sources are not from independent domains")

        if source_ids and not has_primary:
            issues.append("No primary source among citations")

        # Calculate quality score
        quality = self._calculate_quality(
            source_count=len(source_ids),
            min_sources=min_sources,
            has_independent=has_independent,
            has_primary=has_primary,
        )

        return ClaimCitation(
            claim_id=claim.claim_id,
            source_ids=source_ids,
            quality_score=quality,
            has_independent_sources=has_independent,
            has_primary_source=has_primary,
            issues=issues,
        )

    def _calculate_quality(
        self,
        source_count: int,
        min_sources: int,
        has_independent: bool,
        has_primary: bool,
    ) -> float:
        """Calculate citation quality score (0.0 to 1.0)."""
        score = 0.0

        # Source count (40% weight)
        if source_count >= min_sources:
            score += 0.4
        elif source_count > 0:
            score += 0.4 * (source_count / min_sources)

        # Independence (30% weight)
        if has_independent:
            score += 0.3

        # Primary source (30% weight)
        if has_primary:
            score += 0.3

        return round(score, 2)


# Singleton instance
_adapter = CitationBuilderAdapter()


def build_citations(
    claims: list[dict[str, Any]],
    sources: list[dict[str, Any]],
    min_sources_per_claim: int = 2,
) -> dict[str, Any]:
    """
    Build and validate citations for claims.

    Args:
        claims: List of claim dicts
        sources: List of source dicts
        min_sources_per_claim: Minimum sources required per claim

    Returns:
        Dict with citation analysis
    """
    input_data = {
        "claims": claims,
        "sources": sources,
        "min_sources_per_claim": min_sources_per_claim,
    }
    return _adapter.build(input_data)
