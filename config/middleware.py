"""
Middleware Hook Points for the Newsletter Generation System.

This module defines the middleware plan with hook signatures for production readiness.
Middleware is executed in a specific order to ensure proper handling of:
- Cost/time limits
- Safety (PII redaction)
- Human approval (HITL)
- Resilience (retry, fallback)
- Context management (summarization)
- Custom business logic (style injection, citation normalization)

Phase 1 Design - Based on PHASE_1.MD specifications.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional


# -----------------------------------------------------------------------------
# Middleware Base Classes
# -----------------------------------------------------------------------------


class MiddlewarePriority(int, Enum):
    """Execution order priority (lower = earlier)."""

    LIMITS = 100  # Hard ceilings first
    PII_REDACTION = 200  # Egress filter
    HITL_GATE = 300  # Approval interrupts
    RETRY = 400  # Tool retry logic
    FALLBACK = 500  # Model fallback
    SUMMARIZATION = 600  # Context compression
    STYLE_PROFILE = 700  # Custom: style injection
    CITATIONS = 800  # Custom: citation normalization


@dataclass
class MiddlewareContext:
    """Context passed through middleware chain."""

    run_id: str
    agent_name: str
    tool_name: Optional[str] = None
    model_name: Optional[str] = None
    input_data: dict[str, Any] = field(default_factory=dict)
    output_data: dict[str, Any] = field(default_factory=dict)
    state: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    # Tracking
    model_calls: int = 0
    tool_calls: int = 0
    depth: int = 0
    # Flags
    hitl_required: bool = False
    hitl_approved: Optional[bool] = None
    hitl_rationale: Optional[str] = None
    fallback_used: bool = False
    pii_redacted: bool = False
    summarized: bool = False


@dataclass
class MiddlewareResult:
    """Result from middleware execution."""

    proceed: bool = True  # Whether to continue
    modified_context: Optional[MiddlewareContext] = None
    interrupt_reason: Optional[str] = None
    interrupt_data: Optional[dict[str, Any]] = None


class BaseMiddleware(ABC):
    """Abstract base class for all middleware."""

    def __init__(self, priority: MiddlewarePriority, name: str):
        self.priority = priority
        self.name = name
        self.enabled = True

    @abstractmethod
    def before_call(self, ctx: MiddlewareContext) -> MiddlewareResult:
        """Called before tool/model invocation."""
        pass

    @abstractmethod
    def after_call(self, ctx: MiddlewareContext) -> MiddlewareResult:
        """Called after tool/model invocation."""
        pass

    def on_error(self, ctx: MiddlewareContext, error: Exception) -> MiddlewareResult:
        """Called when an error occurs. Default: re-raise."""
        raise error


# -----------------------------------------------------------------------------
# 1. Tool/Model Call Limits Middleware
# -----------------------------------------------------------------------------


@dataclass
class LimitsConfig:
    """Configuration for call limits."""

    max_model_calls_per_run: int = 30
    max_tool_calls_per_run: int = 50
    max_depth_per_run: int = 8


class CallLimitsMiddleware(BaseMiddleware):
    """
    Enforces hard ceilings on model/tool calls and recursion depth.

    Priority: 100 (first in chain)

    Behavior:
    - Tracks call counts in context
    - Aborts run if any limit exceeded
    - Returns clear error message
    """

    def __init__(self, config: LimitsConfig):
        super().__init__(MiddlewarePriority.LIMITS, "CallLimitsMiddleware")
        self.config = config

    def before_call(self, ctx: MiddlewareContext) -> MiddlewareResult:
        # Check model calls
        if ctx.model_name and ctx.model_calls >= self.config.max_model_calls_per_run:
            return MiddlewareResult(
                proceed=False,
                interrupt_reason="max_model_calls_exceeded",
                interrupt_data={
                    "limit": self.config.max_model_calls_per_run,
                    "current": ctx.model_calls,
                },
            )

        # Check tool calls
        if ctx.tool_name and ctx.tool_calls >= self.config.max_tool_calls_per_run:
            return MiddlewareResult(
                proceed=False,
                interrupt_reason="max_tool_calls_exceeded",
                interrupt_data={
                    "limit": self.config.max_tool_calls_per_run,
                    "current": ctx.tool_calls,
                },
            )

        # Check depth
        if ctx.depth >= self.config.max_depth_per_run:
            return MiddlewareResult(
                proceed=False,
                interrupt_reason="max_depth_exceeded",
                interrupt_data={
                    "limit": self.config.max_depth_per_run,
                    "current": ctx.depth,
                },
            )

        return MiddlewareResult(proceed=True)

    def after_call(self, ctx: MiddlewareContext) -> MiddlewareResult:
        # Increment counters
        if ctx.model_name:
            ctx.model_calls += 1
        if ctx.tool_name:
            ctx.tool_calls += 1
        return MiddlewareResult(proceed=True, modified_context=ctx)


# -----------------------------------------------------------------------------
# 2. PII Redaction Middleware
# -----------------------------------------------------------------------------


@dataclass
class PIIPattern:
    """A pattern for detecting PII."""

    name: str
    pattern: str  # Regex pattern
    replacement: str = "[REDACTED]"


DEFAULT_PII_PATTERNS = [
    PIIPattern("email", r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[EMAIL_REDACTED]"),
    PIIPattern("phone_vn", r"\b(0|\+84)[0-9]{9,10}\b", "[PHONE_REDACTED]"),
    PIIPattern("phone_intl", r"\b\+?[1-9][0-9]{7,14}\b", "[PHONE_REDACTED]"),
    PIIPattern("ssn", r"\b[0-9]{3}-[0-9]{2}-[0-9]{4}\b", "[SSN_REDACTED]"),
    PIIPattern("credit_card", r"\b[0-9]{4}[- ]?[0-9]{4}[- ]?[0-9]{4}[- ]?[0-9]{4}\b", "[CC_REDACTED]"),
]


class PIIRedactionMiddleware(BaseMiddleware):
    """
    Redacts PII from outward artifacts.

    Priority: 200 (early, before HITL sees data)

    Behavior:
    - Scans output content for PII patterns
    - Replaces matches with redaction tokens
    - Logs redactions for audit
    """

    def __init__(self, patterns: list[PIIPattern] | None = None):
        super().__init__(MiddlewarePriority.PII_REDACTION, "PIIRedactionMiddleware")
        self.patterns = patterns or DEFAULT_PII_PATTERNS

    def before_call(self, ctx: MiddlewareContext) -> MiddlewareResult:
        # PII redaction happens on output, not input
        return MiddlewareResult(proceed=True)

    def after_call(self, ctx: MiddlewareContext) -> MiddlewareResult:
        import re

        # Redact PII from output
        output_str = str(ctx.output_data)
        redacted = False

        for pii in self.patterns:
            if re.search(pii.pattern, output_str, re.IGNORECASE):
                output_str = re.sub(pii.pattern, pii.replacement, output_str, flags=re.IGNORECASE)
                redacted = True

        if redacted:
            ctx.pii_redacted = True
            ctx.metadata["pii_redacted_at"] = datetime.now().isoformat()
            # Note: In real impl, would parse and reconstruct output_data

        return MiddlewareResult(proceed=True, modified_context=ctx)


# -----------------------------------------------------------------------------
# 3. Human-In-The-Loop (HITL) Gate Middleware
# -----------------------------------------------------------------------------


@dataclass
class HITLConfig:
    """Configuration for HITL gates."""

    gate_unknown_domains: bool = True
    gate_external_plagiarism: bool = True
    approval_timeout_seconds: int = 600
    auto_approve_domains: list[str] = field(default_factory=list)
    deny_domains: list[str] = field(default_factory=list)


class HITLGateMiddleware(BaseMiddleware):
    """
    Interrupts workflow for human approval at designated checkpoints.

    Priority: 300 (after PII redaction)

    HITL Checkpoints:
    - web.fetch on unknown/low-trust domains
    - plagiarism.scan with external provider
    - publish action (always gated)

    Behavior:
    - Checks if action requires approval
    - If so, pauses workflow and requests approval
    - Resumes on approval, aborts on denial
    """

    def __init__(self, config: HITLConfig, approval_callback: Callable[[str, dict], tuple[bool, str]] | None = None):
        super().__init__(MiddlewarePriority.HITL_GATE, "HITLGateMiddleware")
        self.config = config
        # Callback signature: (action: str, data: dict) -> (approved: bool, rationale: str)
        self.approval_callback = approval_callback

    def before_call(self, ctx: MiddlewareContext) -> MiddlewareResult:
        # Check if this call requires HITL
        requires_hitl, reason = self._check_hitl_required(ctx)

        if not requires_hitl:
            return MiddlewareResult(proceed=True)

        # Mark as requiring HITL
        ctx.hitl_required = True

        # If we have a callback, use it; otherwise interrupt
        if self.approval_callback:
            approved, rationale = self.approval_callback(reason, ctx.input_data)
            ctx.hitl_approved = approved
            ctx.hitl_rationale = rationale

            if not approved:
                return MiddlewareResult(
                    proceed=False,
                    interrupt_reason="hitl_denied",
                    interrupt_data={
                        "action": reason,
                        "rationale": rationale,
                    },
                )
        else:
            # No callback - interrupt for external approval
            return MiddlewareResult(
                proceed=False,
                interrupt_reason="hitl_required",
                interrupt_data={
                    "action": reason,
                    "target": ctx.input_data,
                    "timeout_seconds": self.config.approval_timeout_seconds,
                },
            )

        return MiddlewareResult(proceed=True, modified_context=ctx)

    def after_call(self, ctx: MiddlewareContext) -> MiddlewareResult:
        return MiddlewareResult(proceed=True)

    def _check_hitl_required(self, ctx: MiddlewareContext) -> tuple[bool, str]:
        """Check if this call requires HITL approval."""
        # web.fetch on unknown domains
        if ctx.tool_name == "web.fetch" and self.config.gate_unknown_domains:
            url = ctx.input_data.get("url", "")
            domain = self._extract_domain(url)

            if domain in self.config.deny_domains:
                return True, f"fetch_denied_domain:{domain}"
            if domain not in self.config.auto_approve_domains:
                return True, f"fetch_unknown_domain:{domain}"

        # plagiarism.scan with external provider
        if ctx.tool_name == "plagiarism.scan" and self.config.gate_external_plagiarism:
            if ctx.input_data.get("provider") == "external":
                return True, "plagiarism_external_api"

        # publish action (always gated)
        if ctx.tool_name == "publish":
            return True, "publish_action"

        return False, ""

    @staticmethod
    def _extract_domain(url: str) -> str:
        """Extract domain from URL."""
        from urllib.parse import urlparse

        try:
            parsed = urlparse(url)
            return parsed.netloc.lower()
        except Exception:
            return ""


# -----------------------------------------------------------------------------
# 4. Tool Retry Middleware
# -----------------------------------------------------------------------------


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    max_retries: int = 3
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 30.0
    exponential_base: float = 2.0
    retryable_errors: list[str] = field(
        default_factory=lambda: [
            "TimeoutError",
            "ConnectionError",
            "HTTPError",
            "RateLimitError",
        ]
    )


class ToolRetryMiddleware(BaseMiddleware):
    """
    Implements exponential backoff retry for flaky tool calls.

    Priority: 400 (after HITL, so approvals aren't retried)

    Behavior:
    - Catches retryable errors
    - Waits with exponential backoff
    - Retries up to max_retries
    - Gives up and propagates error after exhausting retries
    """

    def __init__(self, config: RetryConfig):
        super().__init__(MiddlewarePriority.RETRY, "ToolRetryMiddleware")
        self.config = config
        self._retry_counts: dict[str, int] = {}

    def before_call(self, ctx: MiddlewareContext) -> MiddlewareResult:
        return MiddlewareResult(proceed=True)

    def after_call(self, ctx: MiddlewareContext) -> MiddlewareResult:
        # Reset retry count on success
        call_key = f"{ctx.run_id}:{ctx.tool_name}"
        self._retry_counts[call_key] = 0
        return MiddlewareResult(proceed=True)

    def on_error(self, ctx: MiddlewareContext, error: Exception) -> MiddlewareResult:
        import time

        error_type = type(error).__name__
        if error_type not in self.config.retryable_errors:
            raise error

        call_key = f"{ctx.run_id}:{ctx.tool_name}"
        retry_count = self._retry_counts.get(call_key, 0)

        if retry_count >= self.config.max_retries:
            raise error

        # Calculate delay with exponential backoff
        delay = min(self.config.base_delay_seconds * (self.config.exponential_base**retry_count), self.config.max_delay_seconds)

        # Wait and retry
        time.sleep(delay)
        self._retry_counts[call_key] = retry_count + 1

        # Return proceed=True to signal retry
        ctx.metadata["retry_attempt"] = retry_count + 1
        return MiddlewareResult(proceed=True, modified_context=ctx)


# -----------------------------------------------------------------------------
# 5. Model Fallback Middleware
# -----------------------------------------------------------------------------


@dataclass
class FallbackConfig:
    """Configuration for model fallback."""

    primary_model: str = "gpt-4o"
    secondary_model: str = "claude-sonnet-4-5-20250929"
    use_on_rate_limit: bool = True
    use_on_timeout: bool = True
    use_on_error: bool = True


class ModelFallbackMiddleware(BaseMiddleware):
    """
    Routes to backup model when primary fails.

    Priority: 500 (after retry, as last resort)

    Behavior:
    - Detects primary model failures
    - Switches to secondary model
    - Records fallback_used flag
    """

    def __init__(self, config: FallbackConfig):
        super().__init__(MiddlewarePriority.FALLBACK, "ModelFallbackMiddleware")
        self.config = config

    def before_call(self, ctx: MiddlewareContext) -> MiddlewareResult:
        return MiddlewareResult(proceed=True)

    def after_call(self, ctx: MiddlewareContext) -> MiddlewareResult:
        return MiddlewareResult(proceed=True)

    def on_error(self, ctx: MiddlewareContext, error: Exception) -> MiddlewareResult:
        error_type = type(error).__name__

        should_fallback = (
            (self.config.use_on_rate_limit and "RateLimit" in error_type)
            or (self.config.use_on_timeout and "Timeout" in error_type)
            or (self.config.use_on_error and ctx.model_name == self.config.primary_model)
        )

        if should_fallback and ctx.model_name == self.config.primary_model:
            # Switch to secondary model
            ctx.model_name = self.config.secondary_model
            ctx.fallback_used = True
            ctx.metadata["fallback_reason"] = str(error)
            return MiddlewareResult(proceed=True, modified_context=ctx)

        raise error


# -----------------------------------------------------------------------------
# 6. Summarization / Context Manager Middleware
# -----------------------------------------------------------------------------


@dataclass
class SummarizationConfig:
    """Configuration for context summarization."""

    target_context_tokens: int = 6000
    preserve_keys: list[str] = field(
        default_factory=lambda: [
            "claim_id",
            "source_id",
            "url",
        ]
    )
    summarization_model: str = "gpt-4o-mini"


class SummarizationMiddleware(BaseMiddleware):
    """
    Compresses context while preserving key anchors.

    Priority: 600 (after resilience middleware)

    Behavior:
    - Estimates token count of context
    - If over budget, summarizes while preserving anchor keys
    - Updates state with summarized content
    """

    def __init__(self, config: SummarizationConfig):
        super().__init__(MiddlewarePriority.SUMMARIZATION, "SummarizationMiddleware")
        self.config = config

    def before_call(self, ctx: MiddlewareContext) -> MiddlewareResult:
        # Estimate token count (rough: ~4 chars per token)
        context_str = str(ctx.state)
        estimated_tokens = len(context_str) // 4

        if estimated_tokens <= self.config.target_context_tokens:
            return MiddlewareResult(proceed=True)

        # Need to summarize
        ctx.summarized = True
        ctx.metadata["pre_summarization_tokens"] = estimated_tokens
        # Note: Actual summarization would call LLM here
        # For Phase 1, we define the hook signature

        return MiddlewareResult(proceed=True, modified_context=ctx)

    def after_call(self, ctx: MiddlewareContext) -> MiddlewareResult:
        return MiddlewareResult(proceed=True)


# -----------------------------------------------------------------------------
# 7. Style Profile Injector (Custom Middleware)
# -----------------------------------------------------------------------------


class StyleProfileMiddleware(BaseMiddleware):
    """
    Injects style profile into agent prompts at runtime.

    Priority: 700 (custom business logic)

    Behavior:
    - Loads style profile from state or config
    - Injects into prompt template placeholders
    - Ensures consistent style across all agents
    """

    def __init__(self, default_profile: dict[str, Any] | None = None):
        super().__init__(MiddlewarePriority.STYLE_PROFILE, "StyleProfileMiddleware")
        self.default_profile = default_profile or {
            "name": "default",
            "voice": "neutral, confident, helpful",
            "sentence_length": "12-20 words",
            "structure": ["hook", "summary", "sections", "key-takeaways", "CTA"],
            "do_not_use": ["sensational claims", "vague sources"],
            "citation_policy": ">=2 independent sources for non-trivial claims",
        }

    def before_call(self, ctx: MiddlewareContext) -> MiddlewareResult:
        # Inject style profile into state if not present
        if "style_profile" not in ctx.state:
            profile_id = ctx.state.get("style_profile_id")
            if profile_id:
                # Load profile by ID (would load from file/DB in real impl)
                ctx.state["style_profile"] = self._load_profile(profile_id)
            else:
                ctx.state["style_profile"] = self.default_profile

        return MiddlewareResult(proceed=True, modified_context=ctx)

    def after_call(self, ctx: MiddlewareContext) -> MiddlewareResult:
        return MiddlewareResult(proceed=True)

    def _load_profile(self, profile_id: str) -> dict[str, Any]:
        """Load style profile by ID. Override for custom loading."""
        # Phase 1: Return default. Phase 2: Load from config/DB
        return self.default_profile


# -----------------------------------------------------------------------------
# 8. Canonical Citations (Custom Middleware)
# -----------------------------------------------------------------------------


class CanonicalCitationsMiddleware(BaseMiddleware):
    """
    Normalizes web.fetch outputs and deduplicates citations.

    Priority: 800 (after style injection)

    Behavior:
    - Normalizes URLs (remove tracking params, etc.)
    - Deduplicates citations by normalized URL
    - Assigns canonical source_ids
    - Updates citation quality metadata
    """

    def __init__(self):
        super().__init__(MiddlewarePriority.CITATIONS, "CanonicalCitationsMiddleware")

    def before_call(self, ctx: MiddlewareContext) -> MiddlewareResult:
        return MiddlewareResult(proceed=True)

    def after_call(self, ctx: MiddlewareContext) -> MiddlewareResult:
        # Process web.fetch outputs
        if ctx.tool_name == "web.fetch":
            url = ctx.output_data.get("url", "")
            normalized_url = self._normalize_url(url)
            ctx.output_data["canonical_url"] = normalized_url
            ctx.output_data["source_id"] = self._generate_source_id(normalized_url)

        return MiddlewareResult(proceed=True, modified_context=ctx)

    @staticmethod
    def _normalize_url(url: str) -> str:
        """Normalize URL by removing tracking params, etc."""
        from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

        tracking_params = ["utm_source", "utm_medium", "utm_campaign", "ref", "source"]

        try:
            parsed = urlparse(url)
            query_params = parse_qs(parsed.query)

            # Remove tracking params
            cleaned_params = {k: v for k, v in query_params.items() if k.lower() not in tracking_params}

            cleaned_query = urlencode(cleaned_params, doseq=True)
            normalized = urlunparse(
                (
                    parsed.scheme,
                    parsed.netloc.lower(),
                    parsed.path.rstrip("/"),
                    parsed.params,
                    cleaned_query,
                    "",  # Remove fragment
                )
            )
            return normalized
        except Exception:
            return url

    @staticmethod
    def _generate_source_id(url: str) -> str:
        """Generate a stable source ID from URL."""
        import hashlib

        return f"SRC_{hashlib.md5(url.encode()).hexdigest()[:8].upper()}"


# -----------------------------------------------------------------------------
# Middleware Chain Manager
# -----------------------------------------------------------------------------


class MiddlewareChain:
    """
    Manages ordered execution of middleware.

    Usage:
        chain = MiddlewareChain()
        chain.add(CallLimitsMiddleware(config))
        chain.add(PIIRedactionMiddleware())
        chain.add(HITLGateMiddleware(config))
        # ...

        result = chain.execute(ctx, callable)
    """

    def __init__(self):
        self.middleware: list[BaseMiddleware] = []

    def add(self, mw: BaseMiddleware) -> "MiddlewareChain":
        """Add middleware to chain."""
        self.middleware.append(mw)
        # Sort by priority
        self.middleware.sort(key=lambda m: m.priority)
        return self

    def remove(self, name: str) -> "MiddlewareChain":
        """Remove middleware by name."""
        self.middleware = [m for m in self.middleware if m.name != name]
        return self

    def execute(self, ctx: MiddlewareContext, target_callable: Callable[..., Any]) -> tuple[Any, MiddlewareContext]:
        """
        Execute the middleware chain around a target callable.

        Returns:
            Tuple of (result, modified_context)
        """
        # Before phase
        for mw in self.middleware:
            if not mw.enabled:
                continue
            result = mw.before_call(ctx)
            if not result.proceed:
                raise MiddlewareInterrupt(result.interrupt_reason or "Unknown error", result.interrupt_data)
            if result.modified_context:
                ctx = result.modified_context

        # Execute target
        try:
            output = target_callable(ctx.input_data)
            ctx.output_data = output if isinstance(output, dict) else {"result": output}
        except Exception as e:
            # Error phase
            for mw in reversed(self.middleware):
                if not mw.enabled:
                    continue
                result = mw.on_error(ctx, e)
                if result.proceed:
                    # Retry signal
                    return self.execute(ctx, target_callable)
            raise

        # After phase
        for mw in reversed(self.middleware):
            if not mw.enabled:
                continue
            result = mw.after_call(ctx)
            if not result.proceed:
                raise MiddlewareInterrupt(result.interrupt_reason or "Unknown error", result.interrupt_data)
            if result.modified_context:
                ctx = result.modified_context

        return ctx.output_data, ctx


class MiddlewareInterrupt(Exception):
    """Raised when middleware interrupts execution."""

    def __init__(self, reason: str, data: dict[str, Any] | None = None):
        self.reason = reason
        self.data = data or {}
        super().__init__(f"Middleware interrupt: {reason}")


# -----------------------------------------------------------------------------
# Factory Function
# -----------------------------------------------------------------------------


def create_default_middleware_chain(
    limits_config: LimitsConfig | None = None,
    hitl_config: HITLConfig | None = None,
    retry_config: RetryConfig | None = None,
    fallback_config: FallbackConfig | None = None,
    summarization_config: SummarizationConfig | None = None,
) -> MiddlewareChain:
    """
    Create a middleware chain with default configuration.

    This is the recommended middleware stack order from PHASE_1.MD.
    """
    chain = MiddlewareChain()

    # 1. Limits (hard ceilings)
    chain.add(CallLimitsMiddleware(limits_config or LimitsConfig()))

    # 2. PII Redaction (egress filter)
    chain.add(PIIRedactionMiddleware())

    # 3. HITL Gate (approval interrupts)
    chain.add(HITLGateMiddleware(hitl_config or HITLConfig()))

    # 4. Tool Retry (exponential backoff)
    chain.add(ToolRetryMiddleware(retry_config or RetryConfig()))

    # 5. Model Fallback (route to backup)
    chain.add(ModelFallbackMiddleware(fallback_config or FallbackConfig()))

    # 6. Summarization (context compression)
    chain.add(SummarizationMiddleware(summarization_config or SummarizationConfig()))

    # 7. Style Profile Injector (custom)
    chain.add(StyleProfileMiddleware())

    # 8. Canonical Citations (custom)
    chain.add(CanonicalCitationsMiddleware())

    return chain
