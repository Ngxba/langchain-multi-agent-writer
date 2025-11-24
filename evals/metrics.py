"""
Evaluation Metrics and Aggregation.

This module provides utilities for aggregating evaluation results
and computing pass rates across multiple runs.

Phase 1 Design - Based on PHASE_1.MD specifications.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from statistics import mean, stdev


# -----------------------------------------------------------------------------
# Evaluation Metrics Container
# -----------------------------------------------------------------------------


@dataclass
class EvaluationMetrics:
    """
    Container for evaluation metrics from a single run.
    """

    run_id: str
    dataset_entry_id: str
    timestamp: datetime = field(default_factory=datetime.now)

    # Overall status
    passed: bool = False
    overall_score: float = 0.0

    # Individual evaluator scores
    evaluator_scores: dict[str, float] = field(default_factory=dict)
    evaluator_passed: dict[str, bool] = field(default_factory=dict)

    # Detailed metrics
    citation_density: float = 0.0
    source_count: int = 0
    unique_domains: int = 0
    max_domain_ratio: float = 0.0
    fact_count: int = 0
    word_count: int = 0
    flesch_kincaid_grade: float = 0.0
    diagram_count: int = 0
    section_count: int = 0

    # Performance metrics
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    execution_time_seconds: float = 0.0

    # Issues
    critical_issues: int = 0
    major_issues: int = 0
    minor_issues: int = 0

    # Metadata
    topic: str = ""
    category: str = ""
    difficulty: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "run_id": self.run_id,
            "dataset_entry_id": self.dataset_entry_id,
            "timestamp": self.timestamp.isoformat(),
            "passed": self.passed,
            "overall_score": self.overall_score,
            "evaluator_scores": self.evaluator_scores,
            "evaluator_passed": self.evaluator_passed,
            "citation_density": self.citation_density,
            "source_count": self.source_count,
            "unique_domains": self.unique_domains,
            "max_domain_ratio": self.max_domain_ratio,
            "fact_count": self.fact_count,
            "word_count": self.word_count,
            "flesch_kincaid_grade": self.flesch_kincaid_grade,
            "diagram_count": self.diagram_count,
            "section_count": self.section_count,
            "total_tokens": self.total_tokens,
            "total_cost_usd": self.total_cost_usd,
            "execution_time_seconds": self.execution_time_seconds,
            "critical_issues": self.critical_issues,
            "major_issues": self.major_issues,
            "minor_issues": self.minor_issues,
            "topic": self.topic,
            "category": self.category,
            "difficulty": self.difficulty,
        }


# -----------------------------------------------------------------------------
# Aggregated Metrics
# -----------------------------------------------------------------------------


@dataclass
class AggregatedMetrics:
    """
    Aggregated metrics across multiple evaluation runs.
    """

    dataset_name: str
    run_count: int
    timestamp: datetime = field(default_factory=datetime.now)

    # Pass rates
    overall_pass_rate: float = 0.0
    evaluator_pass_rates: dict[str, float] = field(default_factory=dict)

    # Score statistics
    mean_overall_score: float = 0.0
    std_overall_score: float = 0.0
    min_overall_score: float = 0.0
    max_overall_score: float = 0.0

    # Evaluator score statistics
    mean_evaluator_scores: dict[str, float] = field(default_factory=dict)

    # Metric means
    mean_citation_density: float = 0.0
    mean_source_count: float = 0.0
    mean_unique_domains: float = 0.0
    mean_fact_count: float = 0.0
    mean_word_count: float = 0.0
    mean_flesch_kincaid_grade: float = 0.0

    # Performance means
    mean_tokens: float = 0.0
    mean_cost_usd: float = 0.0
    mean_execution_time: float = 0.0
    total_cost_usd: float = 0.0

    # Issue counts
    total_critical_issues: int = 0
    total_major_issues: int = 0
    total_minor_issues: int = 0

    # Breakdowns
    pass_rate_by_category: dict[str, float] = field(default_factory=dict)
    pass_rate_by_difficulty: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "dataset_name": self.dataset_name,
            "run_count": self.run_count,
            "timestamp": self.timestamp.isoformat(),
            "overall_pass_rate": self.overall_pass_rate,
            "evaluator_pass_rates": self.evaluator_pass_rates,
            "mean_overall_score": self.mean_overall_score,
            "std_overall_score": self.std_overall_score,
            "min_overall_score": self.min_overall_score,
            "max_overall_score": self.max_overall_score,
            "mean_evaluator_scores": self.mean_evaluator_scores,
            "mean_citation_density": self.mean_citation_density,
            "mean_source_count": self.mean_source_count,
            "mean_unique_domains": self.mean_unique_domains,
            "mean_fact_count": self.mean_fact_count,
            "mean_word_count": self.mean_word_count,
            "mean_flesch_kincaid_grade": self.mean_flesch_kincaid_grade,
            "mean_tokens": self.mean_tokens,
            "mean_cost_usd": self.mean_cost_usd,
            "mean_execution_time": self.mean_execution_time,
            "total_cost_usd": self.total_cost_usd,
            "total_critical_issues": self.total_critical_issues,
            "total_major_issues": self.total_major_issues,
            "total_minor_issues": self.total_minor_issues,
            "pass_rate_by_category": self.pass_rate_by_category,
            "pass_rate_by_difficulty": self.pass_rate_by_difficulty,
        }

    def summary(self) -> str:
        """Generate human-readable summary."""
        return f"""
Evaluation Summary: {self.dataset_name}
{"=" * 50}
Runs: {self.run_count}
Overall Pass Rate: {self.overall_pass_rate:.1%}
Mean Score: {self.mean_overall_score:.2f} (±{self.std_overall_score:.2f})

Evaluator Pass Rates:
{chr(10).join(f"  - {k}: {v:.1%}" for k, v in self.evaluator_pass_rates.items())}

Key Metrics (Mean):
  - Citation Density: {self.mean_citation_density:.1%}
  - Sources: {self.mean_source_count:.1f}
  - Facts: {self.mean_fact_count:.1f}
  - Word Count: {self.mean_word_count:.0f}
  - FK Grade: {self.mean_flesch_kincaid_grade:.1f}

Performance:
  - Mean Tokens: {self.mean_tokens:.0f}
  - Mean Cost: ${self.mean_cost_usd:.4f}
  - Total Cost: ${self.total_cost_usd:.4f}
  - Mean Time: {self.mean_execution_time:.1f}s

Issues:
  - Critical: {self.total_critical_issues}
  - Major: {self.total_major_issues}
  - Minor: {self.total_minor_issues}

Pass Rate by Category:
{chr(10).join(f"  - {k}: {v:.1%}" for k, v in self.pass_rate_by_category.items())}

Pass Rate by Difficulty:
{chr(10).join(f"  - {k}: {v:.1%}" for k, v in self.pass_rate_by_difficulty.items())}
"""


# -----------------------------------------------------------------------------
# Aggregation Functions
# -----------------------------------------------------------------------------


def aggregate_metrics(metrics_list: list[EvaluationMetrics], dataset_name: str = "evaluation") -> AggregatedMetrics:
    """
    Aggregate metrics from multiple evaluation runs.

    Args:
        metrics_list: List of EvaluationMetrics from individual runs
        dataset_name: Name for the aggregated result

    Returns:
        AggregatedMetrics with computed statistics
    """
    if not metrics_list:
        return AggregatedMetrics(dataset_name=dataset_name, run_count=0)

    n = len(metrics_list)

    # Overall pass rate
    pass_count = sum(1 for m in metrics_list if m.passed)
    overall_pass_rate = pass_count / n

    # Overall score statistics
    scores = [m.overall_score for m in metrics_list]
    mean_score = mean(scores)
    std_score = stdev(scores) if n > 1 else 0.0
    min_score = min(scores)
    max_score = max(scores)

    # Evaluator pass rates
    evaluator_names: set[str] = set()
    for m in metrics_list:
        evaluator_names.update(m.evaluator_passed.keys())

    evaluator_pass_rates = {}
    mean_evaluator_scores = {}
    for name in evaluator_names:
        passed_count = sum(1 for m in metrics_list if m.evaluator_passed.get(name, False))
        evaluator_pass_rates[name] = passed_count / n

        scores = [m.evaluator_scores.get(name, 0.0) for m in metrics_list]
        mean_evaluator_scores[name] = mean(scores)

    # Metric means
    mean_citation_density = mean(m.citation_density for m in metrics_list)
    mean_source_count = mean(m.source_count for m in metrics_list)
    mean_unique_domains = mean(m.unique_domains for m in metrics_list)
    mean_fact_count = mean(m.fact_count for m in metrics_list)
    mean_word_count = mean(m.word_count for m in metrics_list)
    mean_fk_grade = mean(m.flesch_kincaid_grade for m in metrics_list)

    # Performance means
    mean_tokens = mean(m.total_tokens for m in metrics_list)
    mean_cost = mean(m.total_cost_usd for m in metrics_list)
    mean_time = mean(m.execution_time_seconds for m in metrics_list)
    total_cost = sum(m.total_cost_usd for m in metrics_list)

    # Issue totals
    total_critical = sum(m.critical_issues for m in metrics_list)
    total_major = sum(m.major_issues for m in metrics_list)
    total_minor = sum(m.minor_issues for m in metrics_list)

    # Pass rate by category
    category_metrics: dict[str, list[bool]] = {}
    for m in metrics_list:
        if m.category:
            if m.category not in category_metrics:
                category_metrics[m.category] = []
            category_metrics[m.category].append(m.passed)

    pass_rate_by_category = {cat: sum(passes) / len(passes) for cat, passes in category_metrics.items()}

    # Pass rate by difficulty
    difficulty_metrics: dict[str, list[bool]] = {}
    for m in metrics_list:
        if m.difficulty:
            if m.difficulty not in difficulty_metrics:
                difficulty_metrics[m.difficulty] = []
            difficulty_metrics[m.difficulty].append(m.passed)

    pass_rate_by_difficulty = {diff: sum(passes) / len(passes) for diff, passes in difficulty_metrics.items()}

    return AggregatedMetrics(
        dataset_name=dataset_name,
        run_count=n,
        overall_pass_rate=overall_pass_rate,
        evaluator_pass_rates=evaluator_pass_rates,
        mean_overall_score=mean_score,
        std_overall_score=std_score,
        min_overall_score=min_score,
        max_overall_score=max_score,
        mean_evaluator_scores=mean_evaluator_scores,
        mean_citation_density=mean_citation_density,
        mean_source_count=mean_source_count,
        mean_unique_domains=mean_unique_domains,
        mean_fact_count=mean_fact_count,
        mean_word_count=mean_word_count,
        mean_flesch_kincaid_grade=mean_fk_grade,
        mean_tokens=mean_tokens,
        mean_cost_usd=mean_cost,
        mean_execution_time=mean_time,
        total_cost_usd=total_cost,
        total_critical_issues=total_critical,
        total_major_issues=total_major,
        total_minor_issues=total_minor,
        pass_rate_by_category=pass_rate_by_category,
        pass_rate_by_difficulty=pass_rate_by_difficulty,
    )


def compute_pass_rate(
    metrics_list: list[EvaluationMetrics],
    evaluator_name: Optional[str] = None,
) -> float:
    """
    Compute pass rate for a specific evaluator or overall.

    Args:
        metrics_list: List of EvaluationMetrics
        evaluator_name: Specific evaluator name, or None for overall

    Returns:
        Pass rate as a float (0.0 to 1.0)
    """
    if not metrics_list:
        return 0.0

    if evaluator_name is None:
        passed = sum(1 for m in metrics_list if m.passed)
    else:
        passed = sum(1 for m in metrics_list if m.evaluator_passed.get(evaluator_name, False))

    return passed / len(metrics_list)


def filter_metrics_by(
    metrics_list: list[EvaluationMetrics],
    category: Optional[str] = None,
    difficulty: Optional[str] = None,
    passed_only: bool = False,
) -> list[EvaluationMetrics]:
    """
    Filter metrics list by criteria.

    Args:
        metrics_list: List of EvaluationMetrics
        category: Filter by category
        difficulty: Filter by difficulty
        passed_only: Only include passed runs

    Returns:
        Filtered list
    """
    filtered = metrics_list

    if category:
        filtered = [m for m in filtered if m.category == category]

    if difficulty:
        filtered = [m for m in filtered if m.difficulty == difficulty]

    if passed_only:
        filtered = [m for m in filtered if m.passed]

    return filtered


# -----------------------------------------------------------------------------
# Threshold Definitions
# -----------------------------------------------------------------------------

# Default thresholds for evaluation metrics
DEFAULT_THRESHOLDS = {
    "citation_density": 0.80,  # 80% of claims must be cited
    "min_sources_per_claim": 2,  # At least 2 sources per claim
    "max_single_domain_ratio": 0.60,  # No more than 60% from one domain
    "min_facts": 5,  # At least 5 facts extracted
    "min_sources": 2,  # At least 2 unique sources
    "target_reading_level": 12,  # FK grade 12
    "reading_level_tolerance": 1,  # +/- 1 grade acceptable
    "max_passive_voice": 20,  # Max 20% passive voice
    "word_count_min": 800,
    "word_count_max": 1200,
}


def get_threshold(metric_name: str, custom_thresholds: Optional[dict] = None) -> Any:
    """
    Get threshold value for a metric.

    Args:
        metric_name: Name of the metric
        custom_thresholds: Optional custom threshold overrides

    Returns:
        Threshold value
    """
    thresholds = {**DEFAULT_THRESHOLDS}
    if custom_thresholds:
        thresholds.update(custom_thresholds)

    return thresholds.get(metric_name)
