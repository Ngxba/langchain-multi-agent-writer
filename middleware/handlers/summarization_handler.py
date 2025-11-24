"""
Summarization Handler - Compresses context while preserving anchors.

Priority: 600 (after fallback)

Phase 2 Implementation.
"""

import logging
from typing import Any, Optional

from middleware.chain import MiddlewareHandler, ExecutionContext

logger = logging.getLogger(__name__)


class SummarizationHandler(MiddlewareHandler):
    """
    Compresses context while preserving key anchors for provenance.

    Triggers when context exceeds token threshold.
    Preserves: claim_id, source_id, url, title, confidence
    """

    def __init__(self, config: dict[str, Any], priority: int = 600):
        super().__init__(name="SummarizationHandler", priority=priority)

        self.target_tokens = config.get("target_context_tokens", 6000)
        self.trigger_threshold = config.get("trigger_threshold_tokens", 8000)
        self.preserve_keys = config.get("preserve_keys", ["claim_id", "source_id", "url", "title", "confidence"])
        self.summarization_model = config.get("summarization_model", "gpt-4o-mini")
        self.record_summarization = config.get("record_summarization", True)

        logger.info(f"SummarizationHandler initialized: target={self.target_tokens}, trigger={self.trigger_threshold}")

    def before_call(self, ctx: ExecutionContext) -> ExecutionContext:
        """Check if context needs summarization before call."""

        # Estimate token count
        estimated_tokens = self._estimate_tokens(ctx.state)

        if estimated_tokens <= self.trigger_threshold:
            return ctx

        logger.info(f"Context exceeds threshold: {estimated_tokens} > {self.trigger_threshold}")

        # Summarize state
        ctx.state = self._summarize_state(ctx.state)
        ctx.summarized = True

        if self.record_summarization:
            ctx.metadata["summarization_triggered"] = True
            ctx.metadata["pre_summarization_tokens"] = estimated_tokens
            ctx.metadata["post_summarization_tokens"] = self._estimate_tokens(ctx.state)
            ctx.state["summarized"] = True

        logger.info(f"Context summarized: {estimated_tokens} -> {ctx.metadata.get('post_summarization_tokens', 'N/A')} tokens")

        return ctx

    def after_call(self, ctx: ExecutionContext, result: Any) -> tuple[ExecutionContext, Any]:
        """Pass through."""
        return ctx, result

    def on_error(self, ctx: ExecutionContext, error: Exception) -> tuple[ExecutionContext, Optional[Exception]]:
        """Pass through errors."""
        return ctx, error

    def _estimate_tokens(self, data: Any) -> int:
        """
        Estimate token count for data.

        Uses rough approximation: ~4 characters per token.
        """
        if data is None:
            return 0

        if isinstance(data, str):
            return len(data) // 4

        if isinstance(data, (int, float, bool)):
            return 1

        if isinstance(data, list):
            return sum(self._estimate_tokens(item) for item in data)

        if isinstance(data, dict):
            return sum(self._estimate_tokens(k) + self._estimate_tokens(v) for k, v in data.items())

        # Fallback: convert to string
        return len(str(data)) // 4

    def _summarize_state(self, state: dict[str, Any]) -> dict[str, Any]:
        """
        Summarize state while preserving anchors.

        Strategy:
        1. Keep all preserved keys intact
        2. Truncate long text fields
        3. Limit list lengths
        4. Compress notes/messages
        """
        summarized: dict[str, Any] = {}

        for key, value in state.items():
            if key in ["facts", "citations"]:
                # Preserve but potentially limit
                summarized[key] = self._summarize_list(value, max_items=20)
            elif key == "messages":
                # Compress message history
                summarized[key] = self._compress_messages(value)
            elif key == "artifacts":
                # Keep artifact metadata, truncate content
                summarized[key] = self._summarize_artifacts(value)
            elif key == "notes":
                # Truncate notes
                summarized[key] = self._truncate_text(str(value), max_chars=2000)
            else:
                # Keep other fields as-is
                summarized[key] = value

        return summarized

    def _summarize_list(self, items: list[Any], max_items: int = 20) -> list[Any]:
        """Summarize a list while preserving anchors."""
        if not isinstance(items, list):
            return items

        # Keep most recent items
        if len(items) <= max_items:
            return items

        # Keep first few and last few
        keep_first = max_items // 3
        keep_last = max_items - keep_first

        result = items[:keep_first] + items[-keep_last:]

        # Add marker
        result.insert(
            keep_first,
            {
                "_summarized": True,
                "_removed_count": len(items) - max_items,
            },
        )

        return result

    def _compress_messages(self, messages: list[Any], max_messages: int = 10) -> list[Any]:
        """Compress message history while preserving key information."""
        if not isinstance(messages, list):
            return messages

        if len(messages) <= max_messages:
            return messages

        # Keep first (system) and last N messages
        keep_last = max_messages - 1

        result = []

        # Keep first message if it's system
        if messages and isinstance(messages[0], dict):
            if messages[0].get("role") == "system":
                result.append(messages[0])

        # Add summary marker
        result.append({"role": "system", "content": f"[{len(messages) - keep_last - len(result)} messages summarized]"})

        # Keep last messages
        result.extend(messages[-keep_last:])

        return result

    def _summarize_artifacts(self, artifacts: dict[str, Any]) -> dict[str, Any]:
        """Summarize artifacts, truncating content."""
        if not isinstance(artifacts, dict):
            return artifacts

        summarized: dict[str, Any] = {}

        for name, artifact in artifacts.items():
            if isinstance(artifact, dict):
                content = artifact.get("content", "")
                truncated_content = self._truncate_text(content, max_chars=5000) if "content" in artifact else content
                summarized[name] = {
                    **artifact,
                    "content": truncated_content,
                }
            else:
                summarized[name] = self._truncate_text(str(artifact), max_chars=5000)

        return summarized

    def _truncate_text(self, text: str, max_chars: int = 2000) -> str:
        """Truncate text while preserving structure."""
        if len(text) <= max_chars:
            return text

        # Try to truncate at a natural break point
        truncate_at = max_chars - 50  # Leave room for marker

        # Look for paragraph break
        last_para = text.rfind("\n\n", 0, truncate_at)
        if last_para > truncate_at // 2:
            truncate_at = last_para

        # Look for sentence break
        else:
            last_sentence = max(
                text.rfind(". ", 0, truncate_at),
                text.rfind("? ", 0, truncate_at),
                text.rfind("! ", 0, truncate_at),
            )
            if last_sentence > truncate_at // 2:
                truncate_at = last_sentence + 1

        return text[:truncate_at] + f"\n\n[... {len(text) - truncate_at} chars truncated ...]"

    def _extract_preserved_data(self, data: Any) -> dict[str, Any]:
        """Extract preserved keys from data structure."""
        preserved = {}

        if isinstance(data, dict):
            for key in self.preserve_keys:
                if key in data:
                    preserved[key] = data[key]

        return preserved

    def pre_process(self, state: dict[str, Any]) -> dict[str, Any]:
        """
        Pre-process state for context summarization.

        Compresses facts and citations if they exceed token limits.
        """

        # Simple token estimation (4 chars per token average)
        def estimate_tokens(text: str) -> int:
            return len(text) // 4

        total_tokens = 0

        # Estimate tokens in facts
        facts = state.get("facts", [])
        for fact in facts:
            total_tokens += estimate_tokens(str(fact))

        # Estimate tokens in citations
        citations = state.get("citations", [])
        for citation in citations:
            total_tokens += estimate_tokens(str(citation))

        # If over limit, truncate but preserve anchors
        if total_tokens > self.target_tokens:
            state["summarized"] = True
            # Truncate fact text but keep claim_ids
            for fact in facts:
                if "text" in fact and len(fact["text"]) > 200:
                    fact["text"] = fact["text"][:200] + "..."

        return state

    def post_process(self, state: dict[str, Any]) -> dict[str, Any]:
        """Post-process state (no-op for summarization handler)."""
        return state
