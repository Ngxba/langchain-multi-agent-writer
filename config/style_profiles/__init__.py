"""
Style Profile Management for the Newsletter Generation System.

This module provides:
- StyleProfile Pydantic schema for validation
- Profile loading from JSON files
- Default profile definitions
- Profile injection utilities

Phase 1 Design - Based on PHASE_1.MD specifications.
"""

import json
from pathlib import Path
from typing import Any
from pydantic import BaseModel, Field


# -----------------------------------------------------------------------------
# Style Profile Schema
# -----------------------------------------------------------------------------


class CitationPolicy(BaseModel):
    """Citation requirements for the style."""

    min_sources_per_claim: int = Field(default=2, description="Minimum independent sources per non-trivial claim")
    require_primary_source: bool = Field(default=True, description="Whether to require at least one primary source")
    max_single_domain_percentage: int = Field(default=60, description="Maximum percentage of citations from a single domain")
    prefer_domains: list[str] = Field(default_factory=list, description="Preferred source domains")


class ReadabilityTargets(BaseModel):
    """Readability targets for the style."""

    grade_level: int = Field(default=12, description="Target Flesch-Kincaid grade level")
    grade_tolerance: int = Field(default=1, description="Acceptable deviation from target grade")
    sentence_length_min: int = Field(default=12, description="Minimum average sentence length (words)")
    sentence_length_max: int = Field(default=20, description="Maximum average sentence length (words)")
    max_passive_voice_percentage: int = Field(default=20, description="Maximum percentage of passive voice sentences")


class ContentStructure(BaseModel):
    """Content structure requirements."""

    sections: list[str] = Field(
        default_factory=lambda: ["hook", "summary", "sections", "key-takeaways", "CTA"], description="Required sections in order"
    )
    min_sections: int = Field(default=3, description="Minimum number of content sections")
    max_sections: int = Field(default=7, description="Maximum number of content sections")
    min_takeaways: int = Field(default=3, description="Minimum number of key takeaways")
    max_takeaways: int = Field(default=5, description="Maximum number of key takeaways")
    word_count_min: int = Field(default=800, description="Minimum word count")
    word_count_max: int = Field(default=1200, description="Maximum word count")


class StyleProfile(BaseModel):
    """
    Complete style profile definition.

    A style profile defines the voice, structure, and quality requirements
    for newsletter content. It is injected into agent prompts at runtime.
    """

    # Identity
    id: str = Field(description="Unique profile identifier")
    name: str = Field(description="Human-readable profile name")
    description: str = Field(default="", description="Profile description")

    # Voice & Tone
    voice: str = Field(default="neutral, confident, helpful", description="Voice characteristics")
    tone_adjectives: list[str] = Field(default_factory=lambda: ["professional", "educational", "approachable"], description="Tone descriptors")

    # Constraints
    do_not_use: list[str] = Field(
        default_factory=lambda: ["sensational claims", "vague sources", "clickbait"], description="Phrases/patterns to avoid"
    )
    avoid_topics: list[str] = Field(default_factory=list, description="Topics to avoid or handle carefully")

    # Structure
    structure: ContentStructure = Field(default_factory=ContentStructure, description="Content structure requirements")

    # Readability
    readability: ReadabilityTargets = Field(default_factory=ReadabilityTargets, description="Readability targets")

    # Citations
    citation_policy: CitationPolicy = Field(default_factory=CitationPolicy, description="Citation requirements")

    # Audience
    target_audience: str = Field(
        default="Vietnamese tech professionals (data engineers, architects, tech leads)", description="Target audience description"
    )
    audience_expertise_level: str = Field(default="intermediate", description="Expected expertise: beginner, intermediate, advanced")

    # Language
    primary_language: str = Field(default="vi", description="Primary content language")
    allow_code_blocks: bool = Field(default=True, description="Whether code blocks are allowed")
    code_language_preferences: list[str] = Field(
        default_factory=lambda: ["python", "sql", "yaml", "json"], description="Preferred programming languages for examples"
    )

    # Metadata
    version: str = Field(default="1.0", description="Profile version")
    created_by: str = Field(default="system", description="Profile creator")
    tags: list[str] = Field(default_factory=list, description="Profile tags")

    def to_prompt_string(self) -> str:
        """Convert profile to a string suitable for prompt injection."""
        return f"""
## Style Profile: {self.name}

### Voice & Tone
- Voice: {self.voice}
- Tone: {", ".join(self.tone_adjectives)}

### Structure Requirements
- Sections: {" → ".join(self.structure.sections)}
- Word count: {self.structure.word_count_min}-{self.structure.word_count_max} words
- Key takeaways: {self.structure.min_takeaways}-{self.structure.max_takeaways} items

### Readability Targets
- Grade level: {self.readability.grade_level} (±{self.readability.grade_tolerance})
- Sentence length: {self.readability.sentence_length_min}-{self.readability.sentence_length_max} words
- Max passive voice: {self.readability.max_passive_voice_percentage}%

### Citation Policy
- Minimum sources per claim: {self.citation_policy.min_sources_per_claim}
- Require primary source: {self.citation_policy.require_primary_source}
- Max single domain: {self.citation_policy.max_single_domain_percentage}%

### DO NOT USE
{chr(10).join(f"- {item}" for item in self.do_not_use)}

### Target Audience
{self.target_audience} ({self.audience_expertise_level} level)
"""


# -----------------------------------------------------------------------------
# Profile Registry
# -----------------------------------------------------------------------------

_PROFILE_CACHE: dict[str, StyleProfile] = {}


def get_profile(profile_id: str) -> StyleProfile:
    """
    Get a style profile by ID.

    Looks for profile in:
    1. In-memory cache
    2. JSON file in style_profiles directory
    3. Built-in defaults
    """
    if profile_id in _PROFILE_CACHE:
        return _PROFILE_CACHE[profile_id]

    # Try loading from file
    profile_dir = Path(__file__).parent
    profile_path = profile_dir / f"{profile_id}.json"

    if profile_path.exists():
        with open(profile_path) as f:
            data = json.load(f)
            profile = StyleProfile(**data)
            _PROFILE_CACHE[profile_id] = profile
            return profile

    # Check built-in defaults
    if profile_id in DEFAULT_PROFILES:
        profile = DEFAULT_PROFILES[profile_id]
        _PROFILE_CACHE[profile_id] = profile
        return profile

    raise ValueError(f"Style profile not found: {profile_id}")


def list_profiles() -> list[str]:
    """List all available profile IDs."""
    profile_dir = Path(__file__).parent
    file_profiles = [p.stem for p in profile_dir.glob("*.json")]
    builtin_profiles = list(DEFAULT_PROFILES.keys())
    return list(set(file_profiles + builtin_profiles))


def register_profile(profile: StyleProfile) -> None:
    """Register a profile in the cache."""
    _PROFILE_CACHE[profile.id] = profile


def save_profile(profile: StyleProfile, overwrite: bool = False) -> Path:
    """Save a profile to JSON file."""
    profile_dir = Path(__file__).parent
    profile_path = profile_dir / f"{profile.id}.json"

    if profile_path.exists() and not overwrite:
        raise FileExistsError(f"Profile already exists: {profile_path}")

    with open(profile_path, "w") as f:
        json.dump(profile.model_dump(), f, indent=2)

    _PROFILE_CACHE[profile.id] = profile
    return profile_path


# -----------------------------------------------------------------------------
# Default Profiles
# -----------------------------------------------------------------------------

DEFAULT_PROFILES: dict[str, StyleProfile] = {
    "neutral-concise": StyleProfile(
        id="neutral-concise",
        name="Neutral Concise",
        description="Default professional style for Vietnamese tech newsletters",
        voice="neutral, confident, helpful",
        tone_adjectives=["professional", "clear", "concise"],
        do_not_use=[
            "sensational claims",
            "vague sources",
            "clickbait headlines",
            "excessive jargon without explanation",
        ],
        structure=ContentStructure(
            sections=["hook", "summary", "sections", "key-takeaways", "CTA"],
            word_count_min=800,
            word_count_max=1200,
        ),
        readability=ReadabilityTargets(
            grade_level=12,
            sentence_length_min=12,
            sentence_length_max=20,
        ),
        citation_policy=CitationPolicy(
            min_sources_per_claim=2,
            require_primary_source=True,
            prefer_domains=[
                "kafka.apache.org",
                "spark.apache.org",
                "flink.apache.org",
                "databricks.com",
                "confluent.io",
            ],
        ),
        target_audience="Vietnamese tech professionals (data engineers, architects)",
        audience_expertise_level="intermediate",
    ),
    "technical-deep": StyleProfile(
        id="technical-deep",
        name="Technical Deep Dive",
        description="In-depth technical content for advanced practitioners",
        voice="authoritative, detailed, precise",
        tone_adjectives=["technical", "thorough", "expert"],
        do_not_use=[
            "oversimplification",
            "hand-waving explanations",
            "unsubstantiated benchmarks",
        ],
        structure=ContentStructure(
            sections=["hook", "summary", "background", "deep-dive", "implementation", "takeaways", "references"],
            word_count_min=1500,
            word_count_max=2500,
            min_sections=5,
            max_sections=10,
        ),
        readability=ReadabilityTargets(
            grade_level=14,
            grade_tolerance=2,
            sentence_length_min=15,
            sentence_length_max=25,
        ),
        citation_policy=CitationPolicy(
            min_sources_per_claim=2,
            require_primary_source=True,
            max_single_domain_percentage=40,
        ),
        target_audience="Senior engineers and architects",
        audience_expertise_level="advanced",
    ),
    "beginner-friendly": StyleProfile(
        id="beginner-friendly",
        name="Beginner Friendly",
        description="Accessible content for newcomers to BigData",
        voice="friendly, patient, encouraging",
        tone_adjectives=["approachable", "educational", "supportive"],
        do_not_use=[
            "unexplained acronyms",
            "assumed prior knowledge",
            "complex nested concepts",
        ],
        structure=ContentStructure(
            sections=["hook", "what-is-it", "why-it-matters", "how-it-works", "getting-started", "next-steps"],
            word_count_min=600,
            word_count_max=1000,
            min_takeaways=3,
            max_takeaways=5,
        ),
        readability=ReadabilityTargets(
            grade_level=10,
            sentence_length_min=10,
            sentence_length_max=18,
            max_passive_voice_percentage=15,
        ),
        citation_policy=CitationPolicy(
            min_sources_per_claim=1,
            require_primary_source=False,
        ),
        target_audience="Junior developers and tech enthusiasts",
        audience_expertise_level="beginner",
    ),
}


# -----------------------------------------------------------------------------
# Utility Functions
# -----------------------------------------------------------------------------


def inject_profile_into_prompt(prompt_template: str, profile: StyleProfile) -> str:
    """
    Inject a style profile into a prompt template.

    Replaces {STYLE_PROFILE} placeholder with profile string.
    """
    profile_string = profile.to_prompt_string()
    return prompt_template.replace("{STYLE_PROFILE}", profile_string)


def validate_content_against_profile(
    content: str,
    profile: StyleProfile,
    metrics: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Validate content against a style profile.

    Returns list of violations found.
    """
    violations = []

    # Check word count
    word_count = metrics.get("word_count", 0)
    if word_count < profile.structure.word_count_min:
        violations.append(
            {
                "type": "word_count",
                "severity": "major",
                "message": f"Word count {word_count} below minimum {profile.structure.word_count_min}",
            }
        )
    if word_count > profile.structure.word_count_max:
        violations.append(
            {
                "type": "word_count",
                "severity": "major",
                "message": f"Word count {word_count} above maximum {profile.structure.word_count_max}",
            }
        )

    # Check reading level
    grade_level = metrics.get("flesch_kincaid_grade", 0)
    target = profile.readability.grade_level
    tolerance = profile.readability.grade_tolerance
    if abs(grade_level - target) > tolerance:
        violations.append(
            {
                "type": "readability",
                "severity": "major",
                "message": f"Grade level {grade_level:.1f} outside target {target}±{tolerance}",
            }
        )

    # Check passive voice
    passive_pct = metrics.get("passive_voice_percentage", 0)
    max_passive = profile.readability.max_passive_voice_percentage
    if passive_pct > max_passive:
        violations.append(
            {
                "type": "passive_voice",
                "severity": "minor",
                "message": f"Passive voice {passive_pct:.1f}% above maximum {max_passive}%",
            }
        )

    # Check for prohibited phrases
    content_lower = content.lower()
    for phrase in profile.do_not_use:
        if phrase.lower() in content_lower:
            violations.append(
                {
                    "type": "prohibited_phrase",
                    "severity": "minor",
                    "message": f"Contains prohibited phrase: '{phrase}'",
                }
            )

    return violations
