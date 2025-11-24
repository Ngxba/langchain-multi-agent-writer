"""
Fallback Handler - Routes to backup model on primary failure.

Priority: 500 (after retry)

Phase 2 Implementation.
"""

import logging
from typing import Any, Optional

from middleware.chain import MiddlewareHandler, ExecutionContext

logger = logging.getLogger(__name__)


class FallbackHandler(MiddlewareHandler):
    """
    Routes to backup model when primary model fails.

    Detects rate limits, timeouts, and errors, then switches to secondary.
    """

    def __init__(self, config: dict[str, Any], priority: int = 500):
        super().__init__(name="FallbackHandler", priority=priority)

        self.primary_model = config.get("primary_model", "gpt-4o")
        self.secondary_model = config.get("secondary_model", "claude-sonnet-4-5-20250929")
        self.use_on_rate_limit = config.get("use_on_rate_limit", True)
        self.use_on_timeout = config.get("use_on_timeout", True)
        self.use_on_error = config.get("use_on_error", True)
        self.record_usage = config.get("record_fallback_usage", True)

        # Track which runs have already used fallback
        self._fallback_used: set[str] = set()

        logger.info(f"FallbackHandler initialized: primary={self.primary_model}, secondary={self.secondary_model}")

    def before_call(self, ctx: ExecutionContext) -> ExecutionContext:
        """Check if we should use fallback model preemptively."""
        # If this run already triggered fallback, use secondary
        if ctx.run_id in self._fallback_used:
            if ctx.model_name == self.primary_model:
                ctx.model_name = self.secondary_model
                ctx.metadata["using_fallback_model"] = True
                logger.debug(f"Using fallback model for run {ctx.run_id}")

        return ctx

    def after_call(self, ctx: ExecutionContext, result: Any) -> tuple[ExecutionContext, Any]:
        """Record fallback usage in state if enabled."""
        if self.record_usage and ctx.fallback_used:
            ctx.state["fallback_used"] = True
            ctx.state["fallback_model"] = self.secondary_model

        return ctx, result

    def on_error(self, ctx: ExecutionContext, error: Exception) -> tuple[ExecutionContext, Optional[Exception]]:
        """Handle model errors by switching to fallback."""

        # Only handle model errors
        if not ctx.model_name:
            return ctx, error

        # Check if we're already using the secondary
        if ctx.model_name == self.secondary_model:
            logger.warning("Secondary model also failed")
            return ctx, error

        # Check if we should use fallback for this error type
        if not self._should_fallback(error):
            return ctx, error

        # Switch to secondary model
        logger.info(f"Switching from {self.primary_model} to {self.secondary_model} due to: {type(error).__name__}")

        ctx.model_name = self.secondary_model
        ctx.fallback_used = True
        ctx.metadata["fallback_reason"] = str(error)
        ctx.metadata["original_model"] = self.primary_model

        # Track this run as using fallback
        self._fallback_used.add(ctx.run_id)

        # Return None to signal retry with new model
        return ctx, None

    def _should_fallback(self, error: Exception) -> bool:
        """Determine if we should fallback for this error."""
        error_type = type(error).__name__
        error_msg = str(error).lower()

        # Rate limit errors
        if self.use_on_rate_limit:
            if "ratelimit" in error_type.lower() or "rate limit" in error_msg:
                return True
            if "429" in error_msg or "quota" in error_msg:
                return True

        # Timeout errors
        if self.use_on_timeout:
            if "timeout" in error_type.lower() or "timeout" in error_msg:
                return True

        # General errors
        if self.use_on_error:
            # API errors that might be provider-specific
            if any(
                pattern in error_msg
                for pattern in [
                    "service unavailable",
                    "internal error",
                    "bad gateway",
                    "overloaded",
                    "capacity",
                ]
            ):
                return True

        return False

    def reset_fallback_tracking(self) -> None:
        """Reset fallback tracking (for testing)."""
        self._fallback_used.clear()

    def pre_process(self, state: dict[str, Any]) -> dict[str, Any]:
        """Pre-process state (no-op for fallback handler)."""
        return state

    def post_process(self, state: dict[str, Any]) -> dict[str, Any]:
        """Post-process state (no-op for fallback handler)."""
        return state

    def handle_failure(self, state: dict[str, Any]) -> dict[str, Any]:
        """Handle failure by switching to secondary model."""
        state["model_name"] = self.secondary_model
        state["fallback_used"] = True
        state["fallback_reason"] = state.get("model_error", "Unknown error")
        return state
