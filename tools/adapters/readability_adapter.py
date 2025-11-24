"""
Readability Adapter - Analyzes content readability and SEO metrics.

Not HITL gated.

Phase 2 Implementation.
"""

import logging
import re
from typing import Any

from tools.contracts import (
    SeoReadabilityInput,
    SeoReadabilityOutput,
    ReadabilityFlag,
    ReadabilitySuggestion,
    ReadabilityLevel,
)

logger = logging.getLogger(__name__)


class ReadabilityAdapter:
    """
    Adapter for readability analysis.

    Analyzes markdown content for:
    - Flesch-Kincaid grade level
    - Flesch reading ease
    - Sentence length
    - Passive voice
    - Word count
    """

    def __init__(
        self,
        target_grade: int = 12,
        max_sentence_length: int = 25,
        max_passive_voice_pct: float = 20.0,
    ):
        self.target_grade = target_grade
        self.max_sentence_length = max_sentence_length
        self.max_passive_voice_pct = max_passive_voice_pct

    def analyze(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Analyze content readability.

        Args:
            input_data: Dict matching SeoReadabilityInput schema

        Returns:
            Dict matching SeoReadabilityOutput schema
        """
        # Validate input
        try:
            validated_input = SeoReadabilityInput(**input_data)
        except Exception as e:
            logger.error(f"Invalid readability input: {e}")
            raise ValueError(f"Invalid readability input: {e}")

        markdown = validated_input.markdown
        target_grade = validated_input.target_grade_level or self.target_grade
        max_sentence_len = validated_input.max_sentence_length or self.max_sentence_length

        logger.info(f"Analyzing readability for {len(markdown)} chars")

        # Strip markdown formatting for analysis
        plain_text = self._strip_markdown(markdown)

        # Calculate metrics
        sentences = self._split_sentences(plain_text)
        words = plain_text.split()
        word_count = len(words)
        sentence_count = len(sentences) or 1
        paragraph_count = len([p for p in plain_text.split("\n\n") if p.strip()])

        # Calculate syllables
        syllable_count = self._count_syllables(plain_text)

        # Flesch-Kincaid Grade Level
        if word_count > 0 and sentence_count > 0:
            fk_grade = 0.39 * (word_count / sentence_count) + 11.8 * (syllable_count / word_count) - 15.59
        else:
            fk_grade = 0

        # Flesch Reading Ease
        if word_count > 0 and sentence_count > 0:
            fk_ease = 206.835 - 1.015 * (word_count / sentence_count) - 84.6 * (syllable_count / word_count)
        else:
            fk_ease = 0

        # Average metrics
        avg_sentence_length = word_count / sentence_count if sentence_count > 0 else 0
        avg_word_length = syllable_count / word_count if word_count > 0 else 0

        # Passive voice detection
        passive_count = self._count_passive_voice(sentences)
        passive_pct = (passive_count / sentence_count * 100) if sentence_count > 0 else 0

        # Determine reading level category
        reading_level = self._categorize_reading_level(fk_grade)

        # Generate flags
        flags = self._generate_flags(
            fk_grade=fk_grade,
            target_grade=target_grade,
            avg_sentence_length=avg_sentence_length,
            max_sentence_len=max_sentence_len,
            passive_pct=passive_pct,
            sentences=sentences,
        )

        # Generate suggestions
        suggestions = self._generate_suggestions(
            sentences=sentences,
            max_sentence_len=max_sentence_len,
            passive_pct=passive_pct,
        )

        # Create output
        output = SeoReadabilityOutput(
            reading_level=reading_level,
            flesch_kincaid_grade=round(fk_grade, 1),
            flesch_reading_ease=round(fk_ease, 1),
            avg_sentence_length=round(avg_sentence_length, 1),
            avg_word_length=round(avg_word_length, 2),
            flags=flags,
            suggestions=suggestions,
            word_count=word_count,
            sentence_count=sentence_count,
            paragraph_count=paragraph_count,
            passive_voice_percentage=round(passive_pct, 1),
        )

        return output.model_dump()

    def _strip_markdown(self, markdown: str) -> str:
        """Remove markdown formatting."""
        text = markdown

        # Remove code blocks
        text = re.sub(r"```[\s\S]*?```", "", text)
        text = re.sub(r"`[^`]+`", "", text)

        # Remove headers
        text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)

        # Remove links but keep text
        text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)

        # Remove images
        text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", "", text)

        # Remove bold/italic
        text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
        text = re.sub(r"\*([^*]+)\*", r"\1", text)
        text = re.sub(r"__([^_]+)__", r"\1", text)
        text = re.sub(r"_([^_]+)_", r"\1", text)

        # Remove bullet points
        text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.MULTILINE)

        # Remove HTML comments
        text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)

        return text.strip()

    def _split_sentences(self, text: str) -> list[str]:
        """Split text into sentences."""
        # Simple sentence splitting
        sentences = re.split(r"(?<=[.!?])\s+", text)
        return [s.strip() for s in sentences if s.strip() and len(s.strip()) > 3]

    def _count_syllables(self, text: str) -> int:
        """Count syllables in text."""
        text = text.lower()
        text = re.sub(r"[^a-z\s]", "", text)
        words = text.split()

        total = 0
        for word in words:
            syllables = len(re.findall(r"[aeiouy]+", word))
            if word.endswith("e"):
                syllables -= 1
            if word.endswith("le") and len(word) > 2 and word[-3] not in "aeiouy":
                syllables += 1
            total += max(1, syllables)

        return total

    def _count_passive_voice(self, sentences: list[str]) -> int:
        """Count sentences with passive voice."""
        passive_patterns = [
            r"\b(was|were|been|being|is|are|am)\s+\w+ed\b",
            r"\b(was|were|been|being|is|are|am)\s+\w+en\b",
            r"\b(was|were|been|being)\s+being\s+\w+",
        ]

        count = 0
        for sentence in sentences:
            for pattern in passive_patterns:
                if re.search(pattern, sentence, re.IGNORECASE):
                    count += 1
                    break

        return count

    def _categorize_reading_level(self, grade: float) -> ReadabilityLevel:
        """Categorize reading level from grade."""
        if grade <= 5:
            return ReadabilityLevel.ELEMENTARY
        elif grade <= 8:
            return ReadabilityLevel.MIDDLE_SCHOOL
        elif grade <= 12:
            return ReadabilityLevel.HIGH_SCHOOL
        elif grade <= 16:
            return ReadabilityLevel.COLLEGE
        else:
            return ReadabilityLevel.PROFESSIONAL

    def _generate_flags(
        self,
        fk_grade: float,
        target_grade: int,
        avg_sentence_length: float,
        max_sentence_len: int,
        passive_pct: float,
        sentences: list[str],
    ) -> list[ReadabilityFlag]:
        """Generate readability flags."""
        flags = []

        # Grade level flag
        grade_diff = abs(fk_grade - target_grade)
        if grade_diff > 2:
            flags.append(
                ReadabilityFlag(
                    type="reading_level",
                    severity="warning" if grade_diff <= 3 else "error",
                    message=f"Reading level {fk_grade:.1f} differs from target {target_grade} by {grade_diff:.1f} grades",
                )
            )

        # Sentence length flag
        if avg_sentence_length > max_sentence_len:
            flags.append(
                ReadabilityFlag(
                    type="sentence_length",
                    severity="warning",
                    message=f"Average sentence length {avg_sentence_length:.1f} exceeds maximum {max_sentence_len}",
                )
            )

        # Find long sentences
        for i, sentence in enumerate(sentences):
            word_count = len(sentence.split())
            if word_count > max_sentence_len * 1.5:
                flags.append(
                    ReadabilityFlag(
                        type="long_sentence",
                        severity="info",
                        location=f"Sentence {i + 1}",
                        message=f"Sentence has {word_count} words",
                    )
                )

        # Passive voice flag
        if passive_pct > self.max_passive_voice_pct:
            flags.append(
                ReadabilityFlag(
                    type="passive_voice",
                    severity="warning",
                    message=f"Passive voice {passive_pct:.1f}% exceeds maximum {self.max_passive_voice_pct}%",
                )
            )

        return flags

    def _generate_suggestions(
        self,
        sentences: list[str],
        max_sentence_len: int,
        passive_pct: float,
    ) -> list[ReadabilitySuggestion]:
        """Generate improvement suggestions."""
        suggestions = []

        # Find sentences to split
        for sentence in sentences[:5]:  # Limit to first 5
            word_count = len(sentence.split())
            if word_count > max_sentence_len * 1.2:
                suggestions.append(
                    ReadabilitySuggestion(
                        original=sentence[:100] + "..." if len(sentence) > 100 else sentence,
                        suggested="Consider splitting this sentence into shorter ones",
                        reason=f"Sentence has {word_count} words, target is {max_sentence_len}",
                    )
                )

        # Passive voice suggestion
        if passive_pct > self.max_passive_voice_pct:
            suggestions.append(
                ReadabilitySuggestion(
                    original="[Multiple sentences]",
                    suggested="Convert passive voice to active voice",
                    reason=f"Passive voice is at {passive_pct:.1f}%, target is <{self.max_passive_voice_pct}%",
                )
            )

        return suggestions


# Singleton instance
_adapter = ReadabilityAdapter()


def check_readability(
    markdown: str,
    target_grade_level: int = 12,
    max_sentence_length: int = 25,
) -> dict[str, Any]:
    """
    Check content readability.

    Args:
        markdown: Markdown content to analyze
        target_grade_level: Target FK grade level
        max_sentence_length: Maximum recommended sentence length

    Returns:
        Dict with readability analysis
    """
    input_data = {
        "markdown": markdown,
        "target_grade_level": target_grade_level,
        "max_sentence_length": max_sentence_length,
    }
    return _adapter.analyze(input_data)
