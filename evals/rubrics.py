"""
Quality Rubrics for Evaluation.

This module defines the quality rubrics used to evaluate newsletter outputs.
Based on PHASE_1.MD specifications for Editor quality gates.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional
import re


# -----------------------------------------------------------------------------
# Rubric Result Types
# -----------------------------------------------------------------------------


class Severity(str, Enum):
    """Issue severity levels."""

    CRITICAL = "critical"  # Blocks publication
    MAJOR = "major"  # Must resolve or waive
    MINOR = "minor"  # Should fix, can pass


class RubricStatus(str, Enum):
    """Overall rubric evaluation status."""

    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"


@dataclass
class RubricIssue:
    """A single issue found during evaluation."""

    rubric_name: str
    severity: Severity
    category: str
    description: str
    location: Optional[str] = None
    suggestion: Optional[str] = None
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class RubricResult:
    """Result of evaluating a single rubric."""

    rubric_name: str
    status: RubricStatus
    score: float  # 0.0 to 1.0
    issues: list[RubricIssue] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    message: str = ""

    @property
    def passed(self) -> bool:
        return self.status == RubricStatus.PASS

    @property
    def has_critical(self) -> bool:
        return any(i.severity == Severity.CRITICAL for i in self.issues)

    @property
    def has_major(self) -> bool:
        return any(i.severity == Severity.MAJOR for i in self.issues)


# -----------------------------------------------------------------------------
# Base Rubric Class
# -----------------------------------------------------------------------------


class QualityRubric(ABC):
    """Abstract base class for quality rubrics."""

    def __init__(self, name: str, description: str, weight: float = 1.0):
        self.name = name
        self.description = description
        self.weight = weight

    @abstractmethod
    def evaluate(self, draft: str, citations: list[dict], facts: list[dict], style_profile: dict, **kwargs) -> RubricResult:
        """
        Evaluate content against this rubric.

        Args:
            draft: The markdown draft content
            citations: List of citation dicts
            facts: List of fact dicts with claim_ids
            style_profile: The active style profile
            **kwargs: Additional context

        Returns:
            RubricResult with status, score, and issues
        """
        pass


# -----------------------------------------------------------------------------
# Citation Rubric
# -----------------------------------------------------------------------------


class CitationRubric(QualityRubric):
    """
    Evaluates citation quality and coverage.

    Checks:
    - Citation density (% of claims with citations)
    - Source independence (unique domains)
    - Primary source inclusion
    - Domain diversity
    """

    def __init__(
        self,
        min_sources_per_claim: int = 2,
        max_single_domain_ratio: float = 0.6,
        require_primary: bool = True,
    ):
        super().__init__(
            name="citation_rubric",
            description="Evaluates citation quality and coverage",
            weight=1.5,  # Higher weight for critical rubric
        )
        self.min_sources_per_claim = min_sources_per_claim
        self.max_single_domain_ratio = max_single_domain_ratio
        self.require_primary = require_primary

    def evaluate(self, draft: str, citations: list[dict], facts: list[dict], style_profile: dict, **kwargs) -> RubricResult:
        issues = []
        metrics: dict[str, float | int] = {}

        # Extract claim references from draft
        claim_refs = self._extract_claim_refs(draft)
        metrics["total_claims_in_draft"] = len(claim_refs)

        # Build citation map
        source_by_claim = {}
        for fact in facts:
            claim_id = fact.get("claim_id", "")
            source_ids = fact.get("source_ids", [])
            source_by_claim[claim_id] = source_ids

        # Check citation coverage
        uncited_claims = []
        undercited_claims = []

        for claim_id in claim_refs:
            sources = source_by_claim.get(claim_id, [])
            if not sources:
                uncited_claims.append(claim_id)
            elif len(sources) < self.min_sources_per_claim:
                undercited_claims.append((claim_id, len(sources)))

        # Citation density
        if claim_refs:
            citation_density: float = 1 - (len(uncited_claims) / len(claim_refs))
        else:
            citation_density = 0.0
        metrics["citation_density"] = citation_density

        if uncited_claims:
            issues.append(
                RubricIssue(
                    rubric_name=self.name,
                    severity=Severity.CRITICAL,
                    category="citation_coverage",
                    description=f"Found {len(uncited_claims)} claims without any citations",
                    data={"uncited_claims": uncited_claims},
                    suggestion="Add citations for these claims or mark as background info",
                )
            )

        if undercited_claims:
            issues.append(
                RubricIssue(
                    rubric_name=self.name,
                    severity=Severity.MAJOR,
                    category="citation_sufficiency",
                    description=f"Found {len(undercited_claims)} claims with <{self.min_sources_per_claim} sources",
                    data={"undercited_claims": undercited_claims},
                    suggestion="Add independent sources for these claims",
                )
            )

        # Check domain diversity
        domain_counts: dict[str, int] = {}
        for citation in citations:
            domain = citation.get("domain", "unknown")
            domain_counts[domain] = domain_counts.get(domain, 0) + 1

        total_citations = len(citations)
        if total_citations > 0:
            max_domain_ratio: float = max(domain_counts.values()) / total_citations
            metrics["max_single_domain_ratio"] = max_domain_ratio
            metrics["unique_domains"] = len(domain_counts)

            if max_domain_ratio > self.max_single_domain_ratio:
                dominant_domain = max(domain_counts, key=lambda k: domain_counts[k])
                issues.append(
                    RubricIssue(
                        rubric_name=self.name,
                        severity=Severity.MAJOR,
                        category="domain_diversity",
                        description=f"Domain {dominant_domain} accounts for {max_domain_ratio:.0%} of citations",
                        data={"domain_counts": domain_counts},
                        suggestion="Add sources from different domains",
                    )
                )

        # Check for primary sources
        if self.require_primary:
            primary_count = sum(1 for c in citations if c.get("is_primary", False))
            metrics["primary_source_count"] = primary_count

            if primary_count == 0 and citations:
                issues.append(
                    RubricIssue(
                        rubric_name=self.name,
                        severity=Severity.MAJOR,
                        category="source_quality",
                        description="No primary sources found in citations",
                        suggestion="Include at least one primary/official source",
                    )
                )

        # Calculate score
        score = citation_density
        if issues:
            critical_count = sum(1 for i in issues if i.severity == Severity.CRITICAL)
            major_count = sum(1 for i in issues if i.severity == Severity.MAJOR)
            score = score * (1 - 0.3 * critical_count - 0.1 * major_count)
            score = max(0.0, score)

        # Determine status
        if any(i.severity == Severity.CRITICAL for i in issues):
            status = RubricStatus.FAIL
        elif any(i.severity == Severity.MAJOR for i in issues):
            status = RubricStatus.WARNING
        else:
            status = RubricStatus.PASS

        return RubricResult(
            rubric_name=self.name,
            status=status,
            score=score,
            issues=issues,
            metrics=metrics,
            message=f"Citation density: {citation_density:.0%}, {len(domain_counts)} unique domains",
        )

    @staticmethod
    def _extract_claim_refs(draft: str) -> list[str]:
        """Extract claim_id references from draft."""
        # Pattern: <!-- claim_id: CLAIM_001, CLAIM_002 -->
        pattern = r"<!--\s*claim_id:\s*([^-]+)\s*-->"
        matches = re.findall(pattern, draft)

        claim_ids = []
        for match in matches:
            ids = [id.strip() for id in match.split(",")]
            claim_ids.extend(ids)

        return list(set(claim_ids))


# -----------------------------------------------------------------------------
# Readability Rubric
# -----------------------------------------------------------------------------


class ReadabilityRubric(QualityRubric):
    """
    Evaluates content readability.

    Checks:
    - Flesch-Kincaid grade level
    - Average sentence length
    - Passive voice percentage
    - Word count
    """

    def __init__(
        self,
        target_grade: int = 12,
        grade_tolerance: int = 1,
        max_sentence_length: int = 25,
        max_passive_voice_pct: float = 20.0,
        word_count_range: tuple[int, int] = (800, 1200),
    ):
        super().__init__(
            name="readability_rubric",
            description="Evaluates content readability metrics",
            weight=1.0,
        )
        self.target_grade = target_grade
        self.grade_tolerance = grade_tolerance
        self.max_sentence_length = max_sentence_length
        self.max_passive_voice_pct = max_passive_voice_pct
        self.word_count_range = word_count_range

    def evaluate(self, draft: str, citations: list[dict], facts: list[dict], style_profile: dict, **kwargs) -> RubricResult:
        issues = []
        metrics: dict[str, float | int] = {}

        # Override from style profile if present
        readability_config = style_profile.get("readability", {})
        target_grade = readability_config.get("grade_level", self.target_grade)
        grade_tolerance = readability_config.get("grade_tolerance", self.grade_tolerance)

        # Calculate basic metrics
        sentences = self._split_sentences(draft)
        words = draft.split()
        word_count = len(words)

        metrics["word_count"] = word_count
        metrics["sentence_count"] = len(sentences)

        # Word count check
        min_words, max_words = self.word_count_range
        if word_count < min_words:
            issues.append(
                RubricIssue(
                    rubric_name=self.name,
                    severity=Severity.MAJOR,
                    category="word_count",
                    description=f"Word count {word_count} below minimum {min_words}",
                    suggestion="Expand content with more detail",
                )
            )
        elif word_count > max_words:
            issues.append(
                RubricIssue(
                    rubric_name=self.name,
                    severity=Severity.MINOR,
                    category="word_count",
                    description=f"Word count {word_count} above maximum {max_words}",
                    suggestion="Consider trimming less essential content",
                )
            )

        # Average sentence length
        if sentences:
            avg_sentence_length: float = word_count / len(sentences)
            metrics["avg_sentence_length"] = avg_sentence_length

            if avg_sentence_length > self.max_sentence_length:
                issues.append(
                    RubricIssue(
                        rubric_name=self.name,
                        severity=Severity.MINOR,
                        category="sentence_length",
                        description=f"Average sentence length {avg_sentence_length:.1f} words exceeds {self.max_sentence_length}",
                        suggestion="Break long sentences into shorter ones",
                    )
                )

        # Flesch-Kincaid approximation
        syllable_count = self._count_syllables(draft)
        if sentences and words:
            fk_grade: float = 0.39 * (word_count / len(sentences)) + 11.8 * (syllable_count / word_count) - 15.59
            metrics["flesch_kincaid_grade"] = fk_grade

            if abs(fk_grade - target_grade) > grade_tolerance:
                severity = Severity.MAJOR if abs(fk_grade - target_grade) > grade_tolerance * 2 else Severity.MINOR
                issues.append(
                    RubricIssue(
                        rubric_name=self.name,
                        severity=severity,
                        category="reading_level",
                        description=f"Reading level {fk_grade:.1f} outside target {target_grade}±{grade_tolerance}",
                        suggestion="Adjust vocabulary and sentence complexity",
                    )
                )

        # Passive voice check (simple heuristic)
        passive_patterns = [
            r"\bwas\s+\w+ed\b",
            r"\bwere\s+\w+ed\b",
            r"\bbeen\s+\w+ed\b",
            r"\bwas\s+\w+en\b",
            r"\bwere\s+\w+en\b",
            r"\bbeen\s+\w+en\b",
            r"\bis\s+being\s+\w+ed\b",
            r"\bare\s+being\s+\w+ed\b",
        ]
        passive_count = sum(len(re.findall(p, draft, re.I)) for p in passive_patterns)
        passive_pct: float = (passive_count / len(sentences) * 100) if sentences else 0.0
        metrics["passive_voice_percentage"] = passive_pct

        if passive_pct > self.max_passive_voice_pct:
            issues.append(
                RubricIssue(
                    rubric_name=self.name,
                    severity=Severity.MINOR,
                    category="passive_voice",
                    description=f"Passive voice {passive_pct:.1f}% exceeds {self.max_passive_voice_pct}%",
                    suggestion="Convert passive constructions to active voice",
                )
            )

        # Calculate score
        score = 1.0
        for issue in issues:
            if issue.severity == Severity.CRITICAL:
                score -= 0.3
            elif issue.severity == Severity.MAJOR:
                score -= 0.15
            else:
                score -= 0.05
        score = max(0.0, score)

        # Determine status
        if any(i.severity == Severity.CRITICAL for i in issues):
            status = RubricStatus.FAIL
        elif any(i.severity == Severity.MAJOR for i in issues):
            status = RubricStatus.WARNING
        else:
            status = RubricStatus.PASS

        return RubricResult(
            rubric_name=self.name,
            status=status,
            score=score,
            issues=issues,
            metrics=metrics,
            message=f"Grade level: {metrics.get('flesch_kincaid_grade', 'N/A'):.1f}, Words: {word_count}",
        )

    @staticmethod
    def _split_sentences(text: str) -> list[str]:
        """Split text into sentences."""
        # Simple sentence splitting
        sentences = re.split(r"[.!?]+", text)
        return [s.strip() for s in sentences if s.strip()]

    @staticmethod
    def _count_syllables(text: str) -> int:
        """Approximate syllable count."""
        text = text.lower()
        text = re.sub(r"[^a-z]", " ", text)
        words = text.split()

        count = 0
        for word in words:
            # Count vowel groups
            syllables = len(re.findall(r"[aeiouy]+", word))
            # Adjust for common patterns
            if word.endswith("e"):
                syllables -= 1
            if word.endswith("le") and len(word) > 2 and word[-3] not in "aeiouy":
                syllables += 1
            syllables = max(1, syllables)
            count += syllables

        return count


# -----------------------------------------------------------------------------
# Style Rubric
# -----------------------------------------------------------------------------


class StyleRubric(QualityRubric):
    """
    Evaluates adherence to style profile.

    Checks:
    - Required sections present
    - Prohibited phrases absent
    - Structure compliance
    """

    def __init__(self):
        super().__init__(
            name="style_rubric",
            description="Evaluates adherence to style profile",
            weight=1.0,
        )

    def evaluate(self, draft: str, citations: list[dict], facts: list[dict], style_profile: dict, **kwargs) -> RubricResult:
        issues = []
        metrics: dict[str, float | int] = {}

        # Get structure requirements
        structure = style_profile.get("structure", {})
        required_sections = structure.get("sections", [])

        # Extract section headers from draft
        headers = re.findall(r"^#{1,3}\s+(.+)$", draft, re.MULTILINE)
        headers_lower = [h.lower() for h in headers]
        metrics["section_count"] = len(headers)

        # Check required sections
        missing_sections = []
        for section in required_sections:
            # Flexible matching
            if not any(section.lower() in h for h in headers_lower):
                missing_sections.append(section)

        if missing_sections:
            issues.append(
                RubricIssue(
                    rubric_name=self.name,
                    severity=Severity.MAJOR,
                    category="structure",
                    description=f"Missing required sections: {', '.join(missing_sections)}",
                    data={"missing_sections": missing_sections},
                    suggestion="Add the missing sections to match style profile",
                )
            )

        # Check prohibited phrases
        do_not_use = style_profile.get("do_not_use", [])
        found_prohibited = []
        draft_lower = draft.lower()

        for phrase in do_not_use:
            if phrase.lower() in draft_lower:
                found_prohibited.append(phrase)

        if found_prohibited:
            issues.append(
                RubricIssue(
                    rubric_name=self.name,
                    severity=Severity.MINOR,
                    category="prohibited_content",
                    description=f"Found prohibited phrases: {', '.join(found_prohibited)}",
                    data={"found_phrases": found_prohibited},
                    suggestion="Remove or rephrase the prohibited content",
                )
            )

        # Check key takeaways
        min_takeaways = structure.get("min_takeaways", 3)
        takeaway_section = re.search(r"##\s*(Key\s*)?Takeaways?\s*\n([\s\S]*?)(?=\n##|$)", draft, re.I)
        if takeaway_section:
            takeaway_items = re.findall(r"^\s*[-*]\s+.+", takeaway_section.group(2), re.MULTILINE)
            metrics["takeaway_count"] = len(takeaway_items)

            if len(takeaway_items) < min_takeaways:
                issues.append(
                    RubricIssue(
                        rubric_name=self.name,
                        severity=Severity.MINOR,
                        category="takeaways",
                        description=f"Only {len(takeaway_items)} takeaways, minimum is {min_takeaways}",
                        suggestion=f"Add at least {min_takeaways - len(takeaway_items)} more takeaways",
                    )
                )

        # Calculate score
        score = 1.0
        for issue in issues:
            if issue.severity == Severity.CRITICAL:
                score -= 0.3
            elif issue.severity == Severity.MAJOR:
                score -= 0.15
            else:
                score -= 0.05
        score = max(0.0, score)

        # Determine status
        if any(i.severity == Severity.CRITICAL for i in issues):
            status = RubricStatus.FAIL
        elif any(i.severity == Severity.MAJOR for i in issues):
            status = RubricStatus.WARNING
        else:
            status = RubricStatus.PASS

        return RubricResult(
            rubric_name=self.name,
            status=status,
            score=score,
            issues=issues,
            metrics=metrics,
            message=f"Found {len(headers)} sections, {len(missing_sections)} missing",
        )


# -----------------------------------------------------------------------------
# Diagram Rubric
# -----------------------------------------------------------------------------


class DiagramRubric(QualityRubric):
    """
    Evaluates diagram quality and inclusion.

    Checks:
    - Diagram intents fulfilled
    - Placement documented
    - Alt text provided
    """

    def __init__(self):
        super().__init__(
            name="diagram_rubric",
            description="Evaluates diagram quality and inclusion",
            weight=0.8,
        )

    def evaluate(
        self,
        draft: str,
        citations: list[dict],
        facts: list[dict],
        style_profile: dict,
        diagrams: list[dict] | None = None,
        diagram_intents: list[dict] | None = None,
        **kwargs,
    ) -> RubricResult:
        issues = []
        metrics: dict[str, float | int] = {}

        diagrams = diagrams or []
        diagram_intents = diagram_intents or []

        metrics["diagram_intent_count"] = len(diagram_intents)
        metrics["diagram_generated_count"] = len(diagrams)

        # Check if all intents have diagrams
        intent_ids = {d.get("intent_id") for d in diagram_intents}
        generated_ids = {d.get("intent_id") for d in diagrams}

        missing_diagrams = intent_ids - generated_ids
        if missing_diagrams:
            issues.append(
                RubricIssue(
                    rubric_name=self.name,
                    severity=Severity.MAJOR,
                    category="missing_diagrams",
                    description=f"Missing diagrams for {len(missing_diagrams)} intents",
                    data={"missing_ids": list(missing_diagrams)},
                    suggestion="Generate diagrams for all defined intents",
                )
            )

        # Check diagram references in draft
        diagram_refs = re.findall(r"<!--\s*DIAGRAM_INTENT:\s*(\w+)\s*-->", draft)
        metrics["diagram_references"] = len(diagram_refs)

        unreferenced = generated_ids - set(diagram_refs)
        if unreferenced and diagrams:
            issues.append(
                RubricIssue(
                    rubric_name=self.name,
                    severity=Severity.MINOR,
                    category="unreferenced_diagrams",
                    description=f"{len(unreferenced)} diagrams not referenced in draft",
                    data={"unreferenced_ids": list(unreferenced)},
                    suggestion="Add diagram reference markers in the draft",
                )
            )

        # Check for alt text
        for diagram in diagrams:
            if not diagram.get("alt_text"):
                issues.append(
                    RubricIssue(
                        rubric_name=self.name,
                        severity=Severity.MINOR,
                        category="accessibility",
                        description=f"Diagram {diagram.get('intent_id')} missing alt text",
                        suggestion="Add descriptive alt text for accessibility",
                    )
                )

        # Calculate score
        if not diagram_intents:
            score = 1.0  # No diagrams expected
        else:
            fulfillment_rate = len(generated_ids) / len(intent_ids) if intent_ids else 1.0
            score = fulfillment_rate

        for issue in issues:
            if issue.severity == Severity.CRITICAL:
                score -= 0.3
            elif issue.severity == Severity.MAJOR:
                score -= 0.15
            else:
                score -= 0.05
        score = max(0.0, score)

        # Determine status
        if any(i.severity == Severity.CRITICAL for i in issues):
            status = RubricStatus.FAIL
        elif any(i.severity == Severity.MAJOR for i in issues):
            status = RubricStatus.WARNING
        else:
            status = RubricStatus.PASS

        return RubricResult(
            rubric_name=self.name,
            status=status,
            score=score,
            issues=issues,
            metrics=metrics,
            message=f"Generated {len(diagrams)}/{len(diagram_intents)} diagrams",
        )


# -----------------------------------------------------------------------------
# Evaluation Runner
# -----------------------------------------------------------------------------


def evaluate_with_rubrics(
    draft: str, citations: list[dict], facts: list[dict], style_profile: dict, rubrics: list[QualityRubric] | None = None, **kwargs
) -> dict[str, RubricResult]:
    """
    Evaluate content against all rubrics.

    Returns dict mapping rubric name to result.
    """
    if rubrics is None:
        rubrics = [
            CitationRubric(),
            ReadabilityRubric(),
            StyleRubric(),
            DiagramRubric(),
        ]

    results = {}
    for rubric in rubrics:
        result = rubric.evaluate(draft=draft, citations=citations, facts=facts, style_profile=style_profile, **kwargs)
        results[rubric.name] = result

    return results


def compute_overall_pass(results: dict[str, RubricResult]) -> tuple[bool, str]:
    """
    Determine overall pass/fail from rubric results.

    Returns:
        Tuple of (passed, reason)
    """
    # Any critical issue = fail
    for name, result in results.items():
        if result.has_critical:
            return False, f"Critical issues in {name}"

    # All rubrics must pass or warn
    for name, result in results.items():
        if result.status == RubricStatus.FAIL:
            return False, f"Rubric {name} failed"

    return True, "All rubrics passed"
