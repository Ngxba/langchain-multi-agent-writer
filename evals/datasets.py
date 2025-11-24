"""
Seed Datasets for Evaluation.

This module defines seed datasets for testing the newsletter generation system.
Based on PHASE_1.MD: 10-20 typical newsletter topics with expected outcomes.
"""

from dataclasses import dataclass, field
from typing import Any, Optional


# -----------------------------------------------------------------------------
# Dataset Entry Schema
# -----------------------------------------------------------------------------


@dataclass
class DatasetEntry:
    """A single entry in the seed dataset."""

    # Input
    topic: str
    brief: Optional[str] = None
    requirements: list[str] = field(default_factory=list)
    style_profile_id: str = "neutral-concise"

    # Expected outcomes
    expected_min_sources: int = 2
    expected_min_facts: int = 5
    expected_diagram_types: list[str] = field(default_factory=list)
    expected_sections: list[str] = field(default_factory=list)

    # Quality thresholds
    min_citation_density: float = 0.8  # % of claims with citations
    max_single_domain_ratio: float = 0.6  # Max % from single domain
    target_reading_level: int = 12
    reading_level_tolerance: int = 1

    # Metadata
    category: str = "general"
    difficulty: str = "medium"
    tags: list[str] = field(default_factory=list)

    def to_run_request(self) -> dict[str, Any]:
        """Convert to RunRequest format."""
        return {
            "topic": self.topic,
            "brief": self.brief,
            "requirements": self.requirements,
            "style_profile_id": self.style_profile_id,
        }


@dataclass
class SeedDataset:
    """A collection of dataset entries for evaluation."""

    name: str
    description: str
    entries: list[DatasetEntry] = field(default_factory=list)
    version: str = "1.0"

    def __len__(self) -> int:
        return len(self.entries)

    def __iter__(self):
        return iter(self.entries)

    def filter_by_category(self, category: str) -> "SeedDataset":
        """Return subset filtered by category."""
        filtered = [e for e in self.entries if e.category == category]
        return SeedDataset(
            name=f"{self.name}_{category}",
            description=f"Filtered by category: {category}",
            entries=filtered,
        )

    def filter_by_difficulty(self, difficulty: str) -> "SeedDataset":
        """Return subset filtered by difficulty."""
        filtered = [e for e in self.entries if e.difficulty == difficulty]
        return SeedDataset(
            name=f"{self.name}_{difficulty}",
            description=f"Filtered by difficulty: {difficulty}",
            entries=filtered,
        )


# -----------------------------------------------------------------------------
# Seed Topics - 20 typical newsletter topics
# -----------------------------------------------------------------------------

NEWSLETTER_TOPICS: list[DatasetEntry] = [
    # Kafka topics (5)
    DatasetEntry(
        topic="Apache Kafka Fundamentals",
        brief="Introduction to Kafka architecture and core concepts for Vietnamese engineers",
        requirements=[
            "Explain producer-consumer model",
            "Cover partition and replication concepts",
            "Include Vietnamese company use cases if available",
        ],
        expected_diagram_types=["architecture", "data_flow"],
        expected_sections=["introduction", "architecture", "core-concepts", "use-cases", "getting-started"],
        category="streaming",
        difficulty="easy",
        tags=["kafka", "fundamentals", "beginner"],
    ),
    DatasetEntry(
        topic="Kafka Connect Deep Dive",
        brief="Advanced guide to Kafka Connect for data integration pipelines",
        requirements=[
            "Cover source and sink connectors",
            "Explain connector configuration",
            "Include production best practices",
        ],
        expected_diagram_types=["data_flow", "architecture"],
        category="streaming",
        difficulty="medium",
        tags=["kafka", "connect", "integration"],
    ),
    DatasetEntry(
        topic="Kafka Streams vs Flink",
        brief="Comparative analysis of stream processing frameworks",
        requirements=[
            "Compare architecture differences",
            "Discuss performance characteristics",
            "Provide decision framework for choosing",
        ],
        expected_diagram_types=["architecture"],
        category="streaming",
        difficulty="hard",
        tags=["kafka", "flink", "comparison"],
    ),
    DatasetEntry(
        topic="Exactly-Once Semantics in Kafka",
        brief="Understanding and implementing exactly-once delivery guarantees",
        requirements=[
            "Explain idempotent producers",
            "Cover transactional messaging",
            "Include configuration examples",
        ],
        expected_diagram_types=["sequence"],
        category="streaming",
        difficulty="hard",
        tags=["kafka", "reliability", "advanced"],
    ),
    DatasetEntry(
        topic="Kafka Security Best Practices 2024",
        brief="Comprehensive security guide for Kafka deployments",
        requirements=[
            "Cover authentication mechanisms",
            "Explain authorization with ACLs",
            "Include encryption setup",
        ],
        expected_diagram_types=["architecture"],
        category="streaming",
        difficulty="medium",
        tags=["kafka", "security"],
    ),
    # Spark topics (4)
    DatasetEntry(
        topic="Apache Spark Architecture Overview",
        brief="Understanding Spark's distributed computing model",
        requirements=[
            "Explain driver and executor roles",
            "Cover DAG execution model",
            "Include memory management concepts",
        ],
        expected_diagram_types=["architecture", "data_flow"],
        category="batch",
        difficulty="medium",
        tags=["spark", "architecture"],
    ),
    DatasetEntry(
        topic="Spark SQL Optimization Techniques",
        brief="Performance tuning for Spark SQL workloads",
        requirements=[
            "Cover Catalyst optimizer",
            "Explain partitioning strategies",
            "Include query optimization tips",
        ],
        expected_diagram_types=["data_flow"],
        category="batch",
        difficulty="hard",
        tags=["spark", "sql", "optimization"],
    ),
    DatasetEntry(
        topic="Structured Streaming in Spark",
        brief="Real-time processing with Spark Structured Streaming",
        requirements=[
            "Explain streaming semantics",
            "Cover watermarks and late data",
            "Include integration patterns",
        ],
        expected_diagram_types=["data_flow", "sequence"],
        category="streaming",
        difficulty="medium",
        tags=["spark", "streaming"],
    ),
    DatasetEntry(
        topic="Delta Lake Fundamentals",
        brief="Introduction to Delta Lake for reliable data lakes",
        requirements=[
            "Explain ACID transactions",
            "Cover time travel features",
            "Include schema evolution",
        ],
        expected_diagram_types=["architecture"],
        category="storage",
        difficulty="medium",
        tags=["delta-lake", "lakehouse"],
    ),
    # Data Architecture topics (4)
    DatasetEntry(
        topic="Data Mesh Architecture Principles",
        brief="Decentralized data architecture for large organizations",
        requirements=[
            "Explain domain-oriented ownership",
            "Cover data as a product",
            "Include federated governance",
        ],
        expected_diagram_types=["architecture", "mindmap"],
        category="architecture",
        difficulty="hard",
        tags=["data-mesh", "architecture", "organization"],
    ),
    DatasetEntry(
        topic="Modern Data Stack 2024",
        brief="Overview of the modern data stack components and trends",
        requirements=[
            "Cover key tool categories",
            "Explain integration patterns",
            "Include vendor landscape",
        ],
        expected_diagram_types=["architecture", "mindmap"],
        category="architecture",
        difficulty="easy",
        tags=["modern-data-stack", "trends"],
    ),
    DatasetEntry(
        topic="Data Lakehouse Architecture",
        brief="Combining data lake and warehouse capabilities",
        requirements=[
            "Explain lakehouse concept",
            "Cover implementation options",
            "Compare with traditional approaches",
        ],
        expected_diagram_types=["architecture"],
        category="storage",
        difficulty="medium",
        tags=["lakehouse", "architecture"],
    ),
    DatasetEntry(
        topic="Real-time Analytics Architecture",
        brief="Building real-time analytics pipelines",
        requirements=[
            "Cover streaming ingestion",
            "Explain OLAP systems",
            "Include latency considerations",
        ],
        expected_diagram_types=["architecture", "data_flow"],
        category="analytics",
        difficulty="hard",
        tags=["real-time", "analytics", "architecture"],
    ),
    # Flink topics (3)
    DatasetEntry(
        topic="Apache Flink Introduction",
        brief="Getting started with Apache Flink for stream processing",
        requirements=[
            "Explain Flink architecture",
            "Cover DataStream API basics",
            "Include deployment options",
        ],
        expected_diagram_types=["architecture"],
        category="streaming",
        difficulty="easy",
        tags=["flink", "fundamentals"],
    ),
    DatasetEntry(
        topic="Flink State Management",
        brief="Understanding and managing state in Flink applications",
        requirements=[
            "Cover state backends",
            "Explain checkpointing",
            "Include savepoint strategies",
        ],
        expected_diagram_types=["architecture", "sequence"],
        category="streaming",
        difficulty="hard",
        tags=["flink", "state", "reliability"],
    ),
    DatasetEntry(
        topic="Flink SQL for Data Engineers",
        brief="Using Flink SQL for stream and batch processing",
        requirements=[
            "Cover SQL syntax extensions",
            "Explain temporal tables",
            "Include CDC integration",
        ],
        expected_diagram_types=["data_flow"],
        category="streaming",
        difficulty="medium",
        tags=["flink", "sql"],
    ),
    # Cloud & MLOps topics (4)
    DatasetEntry(
        topic="Data Engineering on AWS",
        brief="Overview of AWS services for data engineering",
        requirements=[
            "Cover key services (Glue, EMR, Kinesis)",
            "Explain integration patterns",
            "Include cost optimization tips",
        ],
        expected_diagram_types=["architecture"],
        category="cloud",
        difficulty="medium",
        tags=["aws", "cloud"],
    ),
    DatasetEntry(
        topic="MLOps for Data Teams",
        brief="Operationalizing ML models in data pipelines",
        requirements=[
            "Cover ML pipeline components",
            "Explain feature stores",
            "Include monitoring practices",
        ],
        expected_diagram_types=["architecture", "data_flow"],
        category="mlops",
        difficulty="hard",
        tags=["mlops", "ml", "operations"],
    ),
    DatasetEntry(
        topic="Data Quality Best Practices",
        brief="Implementing data quality in modern data platforms",
        requirements=[
            "Cover quality dimensions",
            "Explain testing strategies",
            "Include tool recommendations",
        ],
        expected_diagram_types=["data_flow"],
        category="quality",
        difficulty="medium",
        tags=["data-quality", "testing"],
    ),
    DatasetEntry(
        topic="dbt for Data Transformation",
        brief="Modern data transformation with dbt",
        requirements=[
            "Explain dbt concepts",
            "Cover project structure",
            "Include testing patterns",
        ],
        expected_diagram_types=["data_flow"],
        category="transformation",
        difficulty="easy",
        tags=["dbt", "transformation", "sql"],
    ),
]


# -----------------------------------------------------------------------------
# Dataset Factory
# -----------------------------------------------------------------------------


def get_seed_dataset(
    name: str = "newsletter_topics_v1",
    categories: list[str] | None = None,
    difficulties: list[str] | None = None,
    max_entries: int | None = None,
) -> SeedDataset:
    """
    Get a seed dataset with optional filtering.

    Args:
        name: Dataset name
        categories: Filter by categories (e.g., ["streaming", "batch"])
        difficulties: Filter by difficulty (e.g., ["easy", "medium"])
        max_entries: Maximum number of entries to return

    Returns:
        SeedDataset with filtered entries
    """
    entries = NEWSLETTER_TOPICS.copy()

    if categories:
        entries = [e for e in entries if e.category in categories]

    if difficulties:
        entries = [e for e in entries if e.difficulty in difficulties]

    if max_entries:
        entries = entries[:max_entries]

    return SeedDataset(
        name=name,
        description=f"Seed dataset with {len(entries)} newsletter topics",
        entries=entries,
    )


# -----------------------------------------------------------------------------
# LangSmith Dataset Export (for integration)
# -----------------------------------------------------------------------------


def export_for_langsmith(dataset: SeedDataset) -> list[dict[str, Any]]:
    """
    Export dataset in LangSmith-compatible format.

    Each entry becomes:
    {
        "input": {"topic": ..., "brief": ..., ...},
        "expected": {"min_sources": ..., ...}
    }
    """
    exported = []
    for entry in dataset:
        exported.append(
            {
                "input": {
                    "topic": entry.topic,
                    "brief": entry.brief,
                    "requirements": entry.requirements,
                    "style_profile_id": entry.style_profile_id,
                },
                "expected": {
                    "min_sources": entry.expected_min_sources,
                    "min_facts": entry.expected_min_facts,
                    "diagram_types": entry.expected_diagram_types,
                    "sections": entry.expected_sections,
                    "min_citation_density": entry.min_citation_density,
                    "max_single_domain_ratio": entry.max_single_domain_ratio,
                    "target_reading_level": entry.target_reading_level,
                },
                "metadata": {
                    "category": entry.category,
                    "difficulty": entry.difficulty,
                    "tags": entry.tags,
                },
            }
        )
    return exported
