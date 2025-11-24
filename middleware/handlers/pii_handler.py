"""
PII Handler - Redacts personally identifiable information from outputs.

Priority: 200 (early, before HITL sees data)

Phase 2 Implementation.
"""

import logging
import re
from datetime import datetime
from typing import Any, Optional

from middleware.chain import MiddlewareHandler, ExecutionContext

logger = logging.getLogger(__name__)


# Default PII patterns
DEFAULT_PATTERNS = {
    "email": (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[EMAIL_REDACTED]"),
    "phone_vn": (r"\b(0|\+84)[0-9]{9,10}\b", "[PHONE_REDACTED]"),
    "phone_intl": (r"\b\+?[1-9][0-9]{7,14}\b", "[PHONE_REDACTED]"),
    "ssn": (r"\b[0-9]{3}-[0-9]{2}-[0-9]{4}\b", "[SSN_REDACTED]"),
    "credit_card": (r"\b[0-9]{4}[- ]?[0-9]{4}[- ]?[0-9]{4}[- ]?[0-9]{4}\b", "[CC_REDACTED]"),
    "ip_address": (r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b", "[IP_REDACTED]"),
}


class PIIHandler(MiddlewareHandler):
    """
    Redacts PII from outward artifacts.

    Scans output content for PII patterns and replaces with redaction tokens.
    """

    def __init__(self, config: dict[str, Any], priority: int = 200):
        super().__init__(name="PIIHandler", priority=priority)

        self.enabled = config.get("enabled", True)
        self.log_redactions = config.get("log_redactions", True)
        self.scan_fields = config.get("scan_fields", ["draft", "draft_md", "draft_html", "content", "snippet"])

        # Build patterns from config
        self.patterns: dict[str, tuple[re.Pattern, str]] = {}
        pattern_config = config.get("patterns", {})

        for name, (pattern, replacement) in DEFAULT_PATTERNS.items():
            configured_replacement = pattern_config.get(name, replacement)
            self.patterns[name] = (re.compile(pattern, re.IGNORECASE), configured_replacement)

        logger.info(f"PIIHandler initialized with {len(self.patterns)} patterns")

    def before_call(self, ctx: ExecutionContext) -> ExecutionContext:
        """PII redaction happens on output, not input."""
        return ctx

    def after_call(self, ctx: ExecutionContext, result: Any) -> tuple[ExecutionContext, Any]:
        """Scan and redact PII from output."""
        if not self.enabled:
            return ctx, result

        redaction_count = 0
        redacted_types: list[str] = []

        # Redact from output_data
        if isinstance(ctx.output_data, dict):
            ctx.output_data, count, types = self._redact_dict(ctx.output_data)
            redaction_count += count
            redacted_types.extend(types)

        # Redact from result if it's a dict
        if isinstance(result, dict):
            result, count, types = self._redact_dict(result)
            redaction_count += count
            redacted_types.extend(types)

        # Redact from result if it's a string
        elif isinstance(result, str):
            result, count, types = self._redact_string(result)
            redaction_count += count
            redacted_types.extend(types)

        # Update context flags
        if redaction_count > 0:
            ctx.pii_redacted = True
            ctx.metadata["pii_redaction_count"] = redaction_count
            ctx.metadata["pii_redacted_types"] = list(set(redacted_types))
            ctx.metadata["pii_redacted_at"] = datetime.now().isoformat()

            if self.log_redactions:
                logger.info(f"PII redacted: {redaction_count} items of types {set(redacted_types)}")

        return ctx, result

    def on_error(self, ctx: ExecutionContext, error: Exception) -> tuple[ExecutionContext, Optional[Exception]]:
        """Pass through errors."""
        return ctx, error

    def _redact_string(self, text: str) -> tuple[str, int, list[str]]:
        """Redact PII from a string."""
        total_count = 0
        redacted_types = []

        for name, (pattern, replacement) in self.patterns.items():
            matches = pattern.findall(text)
            if matches:
                count = len(matches)
                total_count += count
                redacted_types.append(name)
                text = pattern.sub(replacement, text)

        return text, total_count, redacted_types

    def _redact_dict(self, data: dict[str, Any]) -> tuple[dict[str, Any], int, list[str]]:
        """Redact PII from a dictionary, scanning specified fields."""
        total_count = 0
        redacted_types: list[str] = []

        for key, value in data.items():
            if isinstance(value, str):
                # Only scan specified fields or all string fields
                if not self.scan_fields or key in self.scan_fields:
                    redacted, count, types = self._redact_string(value)
                    data[key] = redacted
                    total_count += count
                    redacted_types.extend(types)

            elif isinstance(value, dict):
                data[key], count, types = self._redact_dict(value)
                total_count += count
                redacted_types.extend(types)

            elif isinstance(value, list):
                data[key], count, types = self._redact_list(value)
                total_count += count
                redacted_types.extend(types)

        return data, total_count, redacted_types

    def _redact_list(self, items: list[Any]) -> tuple[list[Any], int, list[str]]:
        """Redact PII from a list."""
        total_count = 0
        redacted_types: list[str] = []
        result: list[Any] = []

        for item in items:
            if isinstance(item, str):
                redacted_str, count, types = self._redact_string(item)
                result.append(redacted_str)
                total_count += count
                redacted_types.extend(types)

            elif isinstance(item, dict):
                redacted_dict, count, types = self._redact_dict(item)
                result.append(redacted_dict)
                total_count += count
                redacted_types.extend(types)

            else:
                result.append(item)

        return result, total_count, redacted_types

    def pre_process(self, state: dict[str, Any]) -> dict[str, Any]:
        """Pre-process state (no-op for PII handler - redaction is post-process)."""
        return state

    def post_process(self, state: dict[str, Any]) -> dict[str, Any]:
        """
        Post-process state for PII redaction.

        This is the simplified interface for direct state processing.
        """
        if not self.enabled:
            return state

        redaction_count = 0
        redacted_types: list[str] = []

        # Redact from content field
        if "content" in state and isinstance(state["content"], str):
            state["content"], count, types = self._redact_string(state["content"])
            redaction_count += count
            redacted_types.extend(types)

        # Redact from artifacts
        if "artifacts" in state and isinstance(state["artifacts"], dict):
            for artifact_name, artifact in state["artifacts"].items():
                if isinstance(artifact, dict) and "content" in artifact:
                    if isinstance(artifact["content"], str):
                        artifact["content"], count, types = self._redact_string(artifact["content"])
                        redaction_count += count
                        redacted_types.extend(types)

        # Redact from facts
        if "facts" in state and isinstance(state["facts"], list):
            for fact in state["facts"]:
                if isinstance(fact, dict) and "text" in fact:
                    fact["text"], count, types = self._redact_string(fact["text"])
                    redaction_count += count
                    redacted_types.extend(types)

        # Mark state as having PII redacted
        if redaction_count > 0:
            state["_pii_redacted"] = True
            state["_pii_redaction_count"] = redaction_count

        return state
