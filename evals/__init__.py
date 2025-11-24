"""
Evaluation Framework for the Newsletter Generation System.

This module provides:
- Seed dataset definitions for testing
- Quality rubrics and scoring
- LangSmith integration for online/offline evaluation
- Evaluation metrics and thresholds

Phase 1 Design - Based on PHASE_1.MD specifications.
"""

from .datasets import (
    SeedDataset,
    DatasetEntry,
    get_seed_dataset,
    NEWSLETTER_TOPICS,
)
from .rubrics import (
    QualityRubric,
    RubricResult,
    CitationRubric,
    ReadabilityRubric,
    StyleRubric,
    DiagramRubric,
    evaluate_with_rubrics,
)
from .evaluators import (
    EvaluatorBase,
    CitationDensityEvaluator,
    SourceIndependenceEvaluator,
    ReadingLevelEvaluator,
    DiagramInclusionEvaluator,
    create_evaluator_suite,
)
from .metrics import (
    EvaluationMetrics,
    aggregate_metrics,
    compute_pass_rate,
)

__all__ = [
    # Datasets
    "SeedDataset",
    "DatasetEntry",
    "get_seed_dataset",
    "NEWSLETTER_TOPICS",
    # Rubrics
    "QualityRubric",
    "RubricResult",
    "CitationRubric",
    "ReadabilityRubric",
    "StyleRubric",
    "DiagramRubric",
    "evaluate_with_rubrics",
    # Evaluators
    "EvaluatorBase",
    "CitationDensityEvaluator",
    "SourceIndependenceEvaluator",
    "ReadingLevelEvaluator",
    "DiagramInclusionEvaluator",
    "create_evaluator_suite",
    # Metrics
    "EvaluationMetrics",
    "aggregate_metrics",
    "compute_pass_rate",
]
