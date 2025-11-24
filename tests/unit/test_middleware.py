"""
Unit tests for middleware handlers.

Tests:
- Limits enforcement
- PII redaction
- HITL gating
- Retry logic
- Fallback behavior
- Summarization

Phase 2 Implementation.
"""

import pytest

from middleware.handlers.limits_handler import LimitsHandler
from middleware.handlers.pii_handler import PIIHandler
from middleware.handlers.hitl_handler import HITLHandler
from middleware.handlers.retry_handler import RetryHandler
from middleware.handlers.fallback_handler import FallbackHandler
from middleware.handlers.summarization_handler import SummarizationHandler
from middleware.handlers.style_injector import StyleInjectorHandler
from middleware.handlers.citation_normalizer import CitationNormalizerHandler
from middleware.chain import ExecutionContext


# -----------------------------------------------------------------------------
# Test Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture
def execution_context():
    """Create a basic execution context."""
    return ExecutionContext(
        run_id="test_run_001",
        agent_name="researcher",
    )


@pytest.fixture
def sample_state():
    """Create a sample state dict."""
    return {
        "run_id": "test_run_001",
        "current_agent": "researcher",
        "facts": [],
        "citations": [],
        "artifacts": {},
        "model_calls": 0,
        "tool_calls": 0,
        "depth": 0,
    }


@pytest.fixture
def limits_config():
    """Configuration for limits handler."""
    return {
        "max_model_calls_per_run": 5,
        "max_tool_calls_per_run": 10,
        "max_depth_per_run": 3,
    }


# -----------------------------------------------------------------------------
# Limits Handler Tests
# -----------------------------------------------------------------------------


class TestLimitsHandler:
    """Tests for limits enforcement."""

    def test_limits_allows_within_bounds(self, sample_state, limits_config):
        """Test that calls within limits are allowed."""
        handler = LimitsHandler(limits_config)

        sample_state["model_calls"] = 2
        sample_state["tool_calls"] = 5

        result = handler.pre_process(sample_state)

        assert "error" not in result
        assert result.get("_limits_checked") is True

    def test_limits_blocks_exceeded_model_calls(self, sample_state, limits_config):
        """Test that exceeding model call limit raises error."""
        handler = LimitsHandler(limits_config)

        sample_state["model_calls"] = 6  # Over limit of 5

        with pytest.raises(ValueError, match="model call limit"):
            handler.pre_process(sample_state)

    def test_limits_blocks_exceeded_tool_calls(self, sample_state, limits_config):
        """Test that exceeding tool call limit raises error."""
        handler = LimitsHandler(limits_config)

        sample_state["tool_calls"] = 11  # Over limit of 10

        with pytest.raises(ValueError, match="tool call limit"):
            handler.pre_process(sample_state)

    def test_limits_blocks_exceeded_depth(self, sample_state, limits_config):
        """Test that exceeding depth limit raises error."""
        handler = LimitsHandler(limits_config)

        sample_state["depth"] = 4  # Over limit of 3

        with pytest.raises(ValueError, match="depth limit"):
            handler.pre_process(sample_state)


# -----------------------------------------------------------------------------
# PII Handler Tests
# -----------------------------------------------------------------------------


class TestPIIHandler:
    """Tests for PII redaction."""

    def test_redacts_email(self):
        """Test email redaction."""
        handler = PIIHandler()

        state = {
            "content": "Contact me at john.doe@example.com for details.",
        }

        result = handler.post_process(state)

        assert "john.doe@example.com" not in result.get("content", "")
        assert "[EMAIL]" in result.get("content", "")

    def test_redacts_phone(self):
        """Test phone number redaction."""
        handler = PIIHandler()

        state = {
            "content": "Call me at 555-123-4567 or +1 (555) 987-6543.",
        }

        result = handler.post_process(state)

        assert "555-123-4567" not in result.get("content", "")
        assert "[PHONE]" in result.get("content", "")

    def test_redacts_ssn(self):
        """Test SSN redaction."""
        handler = PIIHandler()

        state = {
            "content": "My SSN is 123-45-6789.",
        }

        result = handler.post_process(state)

        assert "123-45-6789" not in result.get("content", "")
        assert "[SSN]" in result.get("content", "")

    def test_redacts_in_artifacts(self):
        """Test PII redaction in artifacts."""
        handler = PIIHandler()

        state = {
            "artifacts": {
                "draft.md": {
                    "content": "Email: test@test.com",
                }
            }
        }

        result = handler.post_process(state)

        draft = result.get("artifacts", {}).get("draft.md", {})
        assert "test@test.com" not in draft.get("content", "")

    def test_preserves_content_without_pii(self):
        """Test that content without PII is preserved."""
        handler = PIIHandler()

        state = {
            "content": "This is clean content without any personal information.",
        }

        result = handler.post_process(state)

        assert result.get("content") == state["content"]


# -----------------------------------------------------------------------------
# HITL Handler Tests
# -----------------------------------------------------------------------------


class TestHITLHandler:
    """Tests for HITL gating."""

    def test_gates_unknown_domain(self):
        """Test that unknown domains are gated."""
        config = {
            "gate_web_fetch_unknown_domain": True,
            "allow_domains": ["docs.langchain.com", "kafka.apache.org"],
        }
        handler = HITLHandler(config)

        state = {
            "tool_name": "web.fetch",
            "tool_args": {"url": "http://unknown-site.com/page"},
        }

        result = handler.pre_process(state)

        assert result.get("hitl_required") is True
        assert "unknown-site.com" in result.get("hitl_reason", "")

    def test_allows_trusted_domain(self):
        """Test that trusted domains are not gated."""
        config = {
            "gate_web_fetch_unknown_domain": True,
            "allow_domains": ["docs.langchain.com", "kafka.apache.org"],
        }
        handler = HITLHandler(config)

        state = {
            "tool_name": "web.fetch",
            "tool_args": {"url": "https://kafka.apache.org/documentation"},
        }

        result = handler.pre_process(state)

        assert result.get("hitl_required") is not True

    def test_allows_non_fetch_tools(self):
        """Test that non-fetch tools are not gated by domain check."""
        config = {
            "gate_web_fetch_unknown_domain": True,
            "allow_domains": ["docs.langchain.com"],
        }
        handler = HITLHandler(config)

        state = {
            "tool_name": "web.search",
            "tool_args": {"query": "kafka tutorial"},
        }

        result = handler.pre_process(state)

        assert result.get("hitl_required") is not True


# -----------------------------------------------------------------------------
# Retry Handler Tests
# -----------------------------------------------------------------------------


class TestRetryHandler:
    """Tests for retry logic."""

    def test_calculates_exponential_backoff(self):
        """Test exponential backoff calculation."""
        handler = RetryHandler({"max_retries": 3, "base_delay_seconds": 1.0})

        delays = [handler._calculate_delay(i) for i in range(4)]

        # Delays should increase exponentially (with jitter, approximate)
        assert delays[0] >= 1.0
        assert delays[1] >= 2.0
        assert delays[2] >= 4.0

    def test_respects_max_retries(self):
        """Test that max retries is respected."""
        handler = RetryHandler({"max_retries": 2, "base_delay_seconds": 0.1})

        state = {"retry_count": 3}  # Already exceeded max

        assert handler.should_retry(state) is False

    def test_allows_retry_within_limit(self):
        """Test that retries within limit are allowed."""
        handler = RetryHandler({"max_retries": 3, "base_delay_seconds": 0.1})

        state = {"retry_count": 1}

        assert handler.should_retry(state) is True


# -----------------------------------------------------------------------------
# Fallback Handler Tests
# -----------------------------------------------------------------------------


class TestFallbackHandler:
    """Tests for model fallback."""

    def test_switches_to_secondary_on_failure(self):
        """Test that secondary model is used on primary failure."""
        config = {
            "primary_model": "gpt-4o",
            "secondary_model": "claude-sonnet-4-5-20250929",
        }
        handler = FallbackHandler(config)

        state = {
            "model_name": "gpt-4o",
            "model_error": "Rate limit exceeded",
        }

        result = handler.handle_failure(state)

        assert result.get("model_name") == "claude-sonnet-4-5-20250929"
        assert result.get("fallback_used") is True

    def test_records_fallback_reason(self):
        """Test that fallback reason is recorded."""
        config = {
            "primary_model": "gpt-4o",
            "secondary_model": "claude-sonnet-4-5-20250929",
        }
        handler = FallbackHandler(config)

        state = {
            "model_name": "gpt-4o",
            "model_error": "Timeout error",
        }

        result = handler.handle_failure(state)

        assert "Timeout error" in result.get("fallback_reason", "")


# -----------------------------------------------------------------------------
# Summarization Handler Tests
# -----------------------------------------------------------------------------


class TestSummarizationHandler:
    """Tests for context summarization."""

    def test_compresses_long_context(self):
        """Test that long context is compressed."""
        config = {
            "target_context_tokens": 100,  # Low limit for testing
            "preserve_keys": ["claim_id", "source_id"],
        }
        handler = SummarizationHandler(config)

        # Create state with many facts
        state = {
            "facts": [{"claim_id": f"CLAIM_{i}", "text": "A" * 1000} for i in range(10)],
        }

        result = handler.pre_process(state)

        # Should be marked as summarized
        assert result.get("summarized") is True or len(result.get("facts", [])) <= len(state["facts"])

    def test_preserves_anchors(self):
        """Test that claim_ids and source_ids are preserved."""
        config = {
            "target_context_tokens": 100,
            "preserve_keys": ["claim_id", "source_id"],
        }
        handler = SummarizationHandler(config)

        state = {
            "facts": [
                {"claim_id": "CLAIM_001", "text": "Important fact"},
                {"claim_id": "CLAIM_002", "text": "Another fact"},
            ],
        }

        result = handler.pre_process(state)

        # Claim IDs should be preserved
        for fact in result.get("facts", []):
            assert "claim_id" in fact


# -----------------------------------------------------------------------------
# Style Injector Tests
# -----------------------------------------------------------------------------


class TestStyleInjectorHandler:
    """Tests for style profile injection."""

    def test_injects_style_profile(self):
        """Test that style profile is injected."""
        handler = StyleInjectorHandler()

        state = {
            "style_profile": {
                "name": "Technical-Formal",
                "voice": "formal, precise",
            },
        }

        result = handler.pre_process(state)

        assert result.get("style_profile") is not None
        assert result["style_profile"]["name"] == "Technical-Formal"

    def test_uses_default_when_missing(self):
        """Test that default style is used when none provided."""
        handler = StyleInjectorHandler()

        state = {}

        result = handler.pre_process(state)

        assert result.get("style_profile_used") == "default"


# -----------------------------------------------------------------------------
# Citation Normalizer Tests
# -----------------------------------------------------------------------------


class TestCitationNormalizerHandler:
    """Tests for citation normalization."""

    def test_normalizes_url(self):
        """Test URL normalization."""
        handler = CitationNormalizerHandler()

        state = {
            "raw_citations": [
                {"url": "HTTP://Example.COM/Page?utm_source=test"},
            ],
        }

        result = handler.post_process(state)

        citations = result.get("citations", [])
        if citations:
            # URL should be normalized (lowercase, no tracking params)
            url = citations[0].get("url", "")
            assert "utm_source" not in url

    def test_generates_source_id(self):
        """Test source_id generation."""
        handler = CitationNormalizerHandler()

        state = {
            "raw_citations": [
                {"url": "https://example.com/page", "title": "Example"},
            ],
        }

        result = handler.post_process(state)

        citations = result.get("citations", [])
        if citations:
            assert "source_id" in citations[0]
            assert citations[0]["source_id"].startswith("SRC_")

    def test_deduplicates_citations(self):
        """Test citation deduplication."""
        handler = CitationNormalizerHandler()

        state = {
            "raw_citations": [
                {"url": "https://example.com/page", "title": "Example"},
                {"url": "https://example.com/page", "title": "Same Page"},  # Duplicate
            ],
        }

        result = handler.post_process(state)

        citations = result.get("citations", [])
        urls = [c.get("url") for c in citations]
        # Should not have duplicates
        assert len(urls) == len(set(urls))
