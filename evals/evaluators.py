"""
Evaluators for LangSmith Integration.

This module defines evaluators that can be used with LangSmith for
online and offline evaluation of newsletter outputs.

Based on PHASE_1.MD specifications.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
import re


# -----------------------------------------------------------------------------
# Evaluator Result
# -----------------------------------------------------------------------------


@dataclass
class EvaluatorResult:
    """Result from an evaluator."""

    evaluator_name: str
    score: float  # 0.0 to 1.0
    passed: bool
    feedback: str
    details: dict[str, Any] = field(default_factory=dict)


# -----------------------------------------------------------------------------
# Base Evaluator
# -----------------------------------------------------------------------------


class EvaluatorBase(ABC):
    """
    Base class for evaluators.

    Evaluators are designed to work with LangSmith's evaluation framework.
    They take a run output and expected values, and return a score.
    """

    def __init__(self, name: str, description: str, threshold: float = 0.8):
        self.name = name
        self.description = description
        self.threshold = threshold

    @abstractmethod
    def evaluate(self, output: dict[str, Any], expected: dict[str, Any], **kwargs) -> EvaluatorResult:
        """
        Evaluate a run output against expected values.

        Args:
            output: The actual output from the run
            expected: Expected values from the dataset
            **kwargs: Additional context

        Returns:
            EvaluatorResult with score and feedback
        """
        pass

    def __call__(self, output: dict, expected: dict, **kwargs) -> EvaluatorResult:
        """Make evaluator callable."""
        return self.evaluate(output, expected, **kwargs)


# -----------------------------------------------------------------------------
# Citation Density Evaluator
# -----------------------------------------------------------------------------


class CitationDensityEvaluator(EvaluatorBase):
    """
    Evaluates citation density in the output.

    Measures: % of claims that have proper citations
    Target: >= expected min_citation_density
    """

    def __init__(self, threshold: float = 0.8):
        super().__init__(
            name="citation_density",
            description="Measures percentage of claims with proper citations",
            threshold=threshold,
        )

    def evaluate(self, output: dict[str, Any], expected: dict[str, Any], **kwargs) -> EvaluatorResult:
        # Extract data
        draft = output.get("draft", output.get("draft_md", ""))
        facts = output.get("facts", [])

        # Get expected threshold
        expected_density = expected.get("min_citation_density", self.threshold)

        # Count claim references in draft
        claim_pattern = r"<!--\s*claim_id:\s*([^-]+)\s*-->"
        claim_refs = re.findall(claim_pattern, draft)
        unique_claims = set()
        for match in claim_refs:
            ids = [id.strip() for id in match.split(",")]
            unique_claims.update(ids)

        # Count facts with citations
        cited_claims = 0
        total_claims = len(facts)

        for fact in facts:
            source_ids = fact.get("source_ids", [])
            if source_ids and len(source_ids) >= 2:
                cited_claims += 1

        # Calculate density
        if total_claims > 0:
            density = cited_claims / total_claims
        else:
            density = 1.0 if not unique_claims else 0.0

        passed = density >= expected_density

        return EvaluatorResult(
            evaluator_name=self.name,
            score=density,
            passed=passed,
            feedback=f"Citation density: {density:.1%} (target: {expected_density:.1%})",
            details={
                "cited_claims": cited_claims,
                "total_claims": total_claims,
                "claim_refs_in_draft": len(unique_claims),
                "target_density": expected_density,
            },
        )


# -----------------------------------------------------------------------------
# Source Independence Evaluator
# -----------------------------------------------------------------------------


class SourceIndependenceEvaluator(EvaluatorBase):
    """
    Evaluates source independence (unique domains).

    Measures: Domain diversity ratio
    Target: No single domain > max_single_domain_ratio
    """

    def __init__(self, max_ratio: float = 0.6):
        super().__init__(
            name="source_independence",
            description="Measures domain diversity of citations",
            threshold=max_ratio,
        )

    def evaluate(self, output: dict[str, Any], expected: dict[str, Any], **kwargs) -> EvaluatorResult:
        citations = output.get("citations", [])
        max_ratio = expected.get("max_single_domain_ratio", self.threshold)

        if not citations:
            return EvaluatorResult(
                evaluator_name=self.name,
                score=1.0,
                passed=True,
                feedback="No citations to evaluate",
                details={"citation_count": 0},
            )

        # Count domains
        domain_counts: dict[str, int] = {}
        for citation in citations:
            domain = citation.get("domain", "unknown")
            domain_counts[domain] = domain_counts.get(domain, 0) + 1

        # Calculate max ratio
        total = len(citations)
        max_domain_ratio = max(domain_counts.values()) / total
        unique_domains = len(domain_counts)

        # Score: 1.0 if under threshold, decreasing above
        if max_domain_ratio <= max_ratio:
            score = 1.0
        else:
            score = max_ratio / max_domain_ratio

        passed = max_domain_ratio <= max_ratio

        return EvaluatorResult(
            evaluator_name=self.name,
            score=score,
            passed=passed,
            feedback=f"Max domain ratio: {max_domain_ratio:.1%} ({unique_domains} unique domains)",
            details={
                "domain_counts": domain_counts,
                "max_domain_ratio": max_domain_ratio,
                "unique_domains": unique_domains,
                "target_max_ratio": max_ratio,
            },
        )


# -----------------------------------------------------------------------------
# Reading Level Evaluator
# -----------------------------------------------------------------------------


class ReadingLevelEvaluator(EvaluatorBase):
    """
    Evaluates reading level using Flesch-Kincaid grade.

    Measures: FK grade level
    Target: Within tolerance of target_reading_level
    """

    def __init__(self, tolerance: int = 1):
        super().__init__(
            name="reading_level",
            description="Evaluates Flesch-Kincaid grade level",
            threshold=tolerance,
        )

    def evaluate(self, output: dict[str, Any], expected: dict[str, Any], **kwargs) -> EvaluatorResult:
        draft = output.get("draft", output.get("draft_md", ""))
        target_grade = expected.get("target_reading_level", 12)
        tolerance = expected.get("reading_level_tolerance", self.threshold)

        # Calculate FK grade
        sentences = self._split_sentences(draft)
        words = draft.split()
        word_count = len(words)
        sentence_count = len(sentences) or 1
        syllable_count = self._count_syllables(draft)

        if word_count == 0:
            return EvaluatorResult(
                evaluator_name=self.name,
                score=0.0,
                passed=False,
                feedback="Empty content",
                details={"word_count": 0},
            )

        fk_grade = 0.39 * (word_count / sentence_count) + 11.8 * (syllable_count / word_count) - 15.59

        # Calculate score based on distance from target
        distance = abs(fk_grade - target_grade)
        if distance <= tolerance:
            score = 1.0
        else:
            score = max(0.0, 1.0 - (distance - tolerance) / 5.0)

        passed = distance <= tolerance

        return EvaluatorResult(
            evaluator_name=self.name,
            score=score,
            passed=passed,
            feedback=f"FK grade: {fk_grade:.1f} (target: {target_grade}±{tolerance})",
            details={
                "flesch_kincaid_grade": fk_grade,
                "target_grade": target_grade,
                "tolerance": tolerance,
                "word_count": word_count,
                "sentence_count": sentence_count,
            },
        )

    @staticmethod
    def _split_sentences(text: str) -> list[str]:
        sentences = re.split(r"[.!?]+", text)
        return [s.strip() for s in sentences if s.strip()]

    @staticmethod
    def _count_syllables(text: str) -> int:
        text = text.lower()
        text = re.sub(r"[^a-z]", " ", text)
        words = text.split()
        count = 0
        for word in words:
            syllables = len(re.findall(r"[aeiouy]+", word))
            if word.endswith("e"):
                syllables -= 1
            syllables = max(1, syllables)
            count += syllables
        return count


# -----------------------------------------------------------------------------
# Diagram Inclusion Evaluator
# -----------------------------------------------------------------------------


class DiagramInclusionEvaluator(EvaluatorBase):
    """
    Evaluates diagram inclusion.

    Measures: % of expected diagram types included
    Target: All expected diagrams present
    """

    def __init__(self):
        super().__init__(
            name="diagram_inclusion",
            description="Evaluates presence of expected diagrams",
            threshold=1.0,
        )

    def evaluate(self, output: dict[str, Any], expected: dict[str, Any], **kwargs) -> EvaluatorResult:
        diagrams = output.get("diagrams", [])
        diagram_intents = output.get("diagram_intents", [])
        expected_types = expected.get("diagram_types", [])

        if not expected_types:
            return EvaluatorResult(
                evaluator_name=self.name,
                score=1.0,
                passed=True,
                feedback="No diagrams expected",
                details={"expected_types": []},
            )

        # Get generated diagram types
        generated_types = set()
        for diagram in diagrams:
            dtype = diagram.get("diagram_type", diagram.get("type", ""))
            if dtype:
                generated_types.add(dtype)

        # Also check intents
        for intent in diagram_intents:
            dtype = intent.get("diagram_type", "")
            if dtype:
                generated_types.add(dtype)

        # Check coverage
        expected_set = set(expected_types)
        covered = expected_set & generated_types
        missing = expected_set - generated_types

        score = len(covered) / len(expected_set) if expected_set else 1.0
        passed = len(missing) == 0

        return EvaluatorResult(
            evaluator_name=self.name,
            score=score,
            passed=passed,
            feedback=f"Diagram coverage: {len(covered)}/{len(expected_set)} types",
            details={
                "expected_types": list(expected_set),
                "generated_types": list(generated_types),
                "covered": list(covered),
                "missing": list(missing),
            },
        )


# -----------------------------------------------------------------------------
# Structure Compliance Evaluator
# -----------------------------------------------------------------------------


class StructureComplianceEvaluator(EvaluatorBase):
    """
    Evaluates structure compliance with style profile.

    Measures: % of expected sections present
    """

    def __init__(self):
        super().__init__(
            name="structure_compliance",
            description="Evaluates presence of required sections",
            threshold=1.0,
        )

    def evaluate(self, output: dict[str, Any], expected: dict[str, Any], **kwargs) -> EvaluatorResult:
        draft = output.get("draft", output.get("draft_md", ""))
        expected_sections = expected.get("sections", [])

        if not expected_sections:
            return EvaluatorResult(
                evaluator_name=self.name,
                score=1.0,
                passed=True,
                feedback="No specific sections expected",
                details={"expected_sections": []},
            )

        # Extract headers from draft
        headers = re.findall(r"^#{1,3}\s+(.+)$", draft, re.MULTILINE)
        headers_lower = [h.lower() for h in headers]

        # Check for expected sections
        found = []
        missing = []

        for section in expected_sections:
            section_lower = section.lower()
            if any(section_lower in h for h in headers_lower):
                found.append(section)
            else:
                missing.append(section)

        score = len(found) / len(expected_sections) if expected_sections else 1.0
        passed = len(missing) == 0

        return EvaluatorResult(
            evaluator_name=self.name,
            score=score,
            passed=passed,
            feedback=f"Section coverage: {len(found)}/{len(expected_sections)}",
            details={
                "expected_sections": expected_sections,
                "found_sections": found,
                "missing_sections": missing,
                "actual_headers": headers,
            },
        )


# -----------------------------------------------------------------------------
# Fact Count Evaluator
# -----------------------------------------------------------------------------


class FactCountEvaluator(EvaluatorBase):
    """
    Evaluates minimum fact count.

    Measures: Number of extracted facts
    Target: >= expected min_facts
    """

    def __init__(self, min_facts: int = 5):
        super().__init__(
            name="fact_count",
            description="Evaluates minimum number of extracted facts",
            threshold=min_facts,
        )

    def evaluate(self, output: dict[str, Any], expected: dict[str, Any], **kwargs) -> EvaluatorResult:
        facts = output.get("facts", [])
        min_facts = expected.get("min_facts", self.threshold)

        fact_count = len(facts)
        score = min(1.0, fact_count / min_facts) if min_facts > 0 else 1.0
        passed = fact_count >= min_facts

        return EvaluatorResult(
            evaluator_name=self.name,
            score=score,
            passed=passed,
            feedback=f"Fact count: {fact_count} (minimum: {min_facts})",
            details={
                "fact_count": fact_count,
                "min_facts": min_facts,
            },
        )


# -----------------------------------------------------------------------------
# Source Count Evaluator
# -----------------------------------------------------------------------------


class SourceCountEvaluator(EvaluatorBase):
    """
    Evaluates minimum source count.

    Measures: Number of unique citations
    Target: >= expected min_sources
    """

    def __init__(self, min_sources: int = 2):
        super().__init__(
            name="source_count",
            description="Evaluates minimum number of unique sources",
            threshold=min_sources,
        )

    def evaluate(self, output: dict[str, Any], expected: dict[str, Any], **kwargs) -> EvaluatorResult:
        citations = output.get("citations", [])
        min_sources = expected.get("min_sources", self.threshold)

        source_count = len(citations)
        score = min(1.0, source_count / min_sources) if min_sources > 0 else 1.0
        passed = source_count >= min_sources

        return EvaluatorResult(
            evaluator_name=self.name,
            score=score,
            passed=passed,
            feedback=f"Source count: {source_count} (minimum: {min_sources})",
            details={
                "source_count": source_count,
                "min_sources": min_sources,
            },
        )


# -----------------------------------------------------------------------------
# Evaluator Suite Factory
# -----------------------------------------------------------------------------


def create_evaluator_suite(
    include_diagrams: bool = True,
    include_structure: bool = True,
) -> list[EvaluatorBase]:
    """
    Create a standard suite of evaluators.

    Args:
        include_diagrams: Whether to include diagram evaluator
        include_structure: Whether to include structure evaluator

    Returns:
        List of evaluators
    """
    evaluators = [
        CitationDensityEvaluator(),
        SourceIndependenceEvaluator(),
        ReadingLevelEvaluator(),
        FactCountEvaluator(),
        SourceCountEvaluator(),
    ]

    if include_diagrams:
        evaluators.append(DiagramInclusionEvaluator())

    if include_structure:
        evaluators.append(StructureComplianceEvaluator())

    return evaluators


def run_evaluator_suite(
    output: dict[str, Any],
    expected: dict[str, Any],
    evaluators: list[EvaluatorBase] | None = None,
) -> dict[str, EvaluatorResult]:
    """
    Run all evaluators and return results.

    Returns:
        Dict mapping evaluator name to result
    """
    if evaluators is None:
        evaluators = create_evaluator_suite()

    results = {}
    for evaluator in evaluators:
        result = evaluator.evaluate(output, expected)
        results[evaluator.name] = result

    return results


def compute_aggregate_score(results: dict[str, EvaluatorResult]) -> float:
    """Compute weighted aggregate score from evaluator results."""
    if not results:
        return 0.0

    total_score = sum(r.score for r in results.values())
    return total_score / len(results)


def all_evaluators_passed(results: dict[str, EvaluatorResult]) -> bool:
    """Check if all evaluators passed."""
    return all(r.passed for r in results.values())
