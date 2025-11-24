"""
Retry Handler - Implements exponential backoff for transient errors.

Priority: 400 (after HITL)

Phase 2 Implementation.
"""

import logging
import time
from typing import Any, Optional

from middleware.chain import MiddlewareHandler, ExecutionContext

logger = logging.getLogger(__name__)


# Default retryable errors
DEFAULT_RETRYABLE_ERRORS = [
    "TimeoutError",
    "ConnectionError",
    "HTTPError",
    "RateLimitError",
    "ServiceUnavailable",
    "BadGateway",
]


class RetryHandler(MiddlewareHandler):
    """
    Implements exponential backoff retry for transient errors.

    Catches retryable errors, waits with backoff, and retries.
    """

    def __init__(self, config: dict[str, Any], priority: int = 400):
        super().__init__(name="RetryHandler", priority=priority)

        self.max_retries = config.get("max_retries", 3)
        self.base_delay = config.get("base_delay_seconds", 1.0)
        self.max_delay = config.get("max_delay_seconds", 30.0)
        self.exponential_base = config.get("exponential_base", 2.0)
        self.retryable_errors = config.get("retryable_errors", DEFAULT_RETRYABLE_ERRORS)

        # Track retry counts per call
        self._retry_counts: dict[str, int] = {}

        logger.info(f"RetryHandler initialized: max_retries={self.max_retries}, base_delay={self.base_delay}s")

    def before_call(self, ctx: ExecutionContext) -> ExecutionContext:
        """Initialize retry tracking for this call."""
        call_key = self._get_call_key(ctx)

        # Initialize retry count if not exists
        if call_key not in self._retry_counts:
            self._retry_counts[call_key] = 0

        return ctx

    def after_call(self, ctx: ExecutionContext, result: Any) -> tuple[ExecutionContext, Any]:
        """Reset retry count on success."""
        call_key = self._get_call_key(ctx)

        # Reset retry count on success
        if call_key in self._retry_counts:
            if self._retry_counts[call_key] > 0:
                logger.info(f"Call succeeded after {self._retry_counts[call_key]} retries")
            self._retry_counts[call_key] = 0

        return ctx, result

    def on_error(self, ctx: ExecutionContext, error: Exception) -> tuple[ExecutionContext, Optional[Exception]]:
        """Handle errors with retry logic."""
        error_type = type(error).__name__

        # Check if error is retryable
        if not self._is_retryable(error):
            logger.debug(f"Error {error_type} is not retryable")
            return ctx, error

        call_key = self._get_call_key(ctx)
        retry_count = self._retry_counts.get(call_key, 0)

        # Check if we've exceeded max retries
        if retry_count >= self.max_retries:
            logger.warning(f"Max retries ({self.max_retries}) exceeded for {ctx.tool_name or ctx.model_name}")
            ctx.metadata["retry_exhausted"] = True
            ctx.metadata["retry_count"] = retry_count
            return ctx, error

        # Calculate delay with exponential backoff
        delay = self._calculate_delay(retry_count)

        logger.info(f"Retrying {ctx.tool_name or ctx.model_name} (attempt {retry_count + 1}/{self.max_retries}) after {delay:.2f}s delay")

        # Wait
        time.sleep(delay)

        # Increment retry count
        self._retry_counts[call_key] = retry_count + 1
        ctx.metadata["retry_attempt"] = retry_count + 1

        # Return None to signal retry
        return ctx, None

    def _get_call_key(self, ctx: ExecutionContext) -> str:
        """Generate unique key for this call."""
        return f"{ctx.run_id}:{ctx.tool_name or ctx.model_name}"

    def _is_retryable(self, error: Exception) -> bool:
        """Check if error is retryable."""
        error_type = type(error).__name__

        # Direct match
        if error_type in self.retryable_errors:
            return True

        # Check error message for patterns
        error_msg = str(error).lower()
        retryable_patterns = [
            "timeout",
            "connection",
            "rate limit",
            "service unavailable",
            "bad gateway",
            "502",
            "503",
            "504",
            "429",
        ]

        for pattern in retryable_patterns:
            if pattern in error_msg:
                return True

        return False

    def _calculate_delay(self, retry_count: int) -> float:
        """Calculate delay with exponential backoff and jitter."""
        import random

        # Exponential backoff
        delay = self.base_delay * (self.exponential_base**retry_count)

        # Add jitter (±10%)
        jitter = delay * 0.1 * (2 * random.random() - 1)
        delay += jitter

        # Cap at max delay
        delay = min(delay, self.max_delay)

        return delay

    def clear_retry_counts(self) -> None:
        """Clear all retry counts (for testing)."""
        self._retry_counts.clear()

    def pre_process(self, state: dict[str, Any]) -> dict[str, Any]:
        """Pre-process state (no-op for retry handler)."""
        return state

    def post_process(self, state: dict[str, Any]) -> dict[str, Any]:
        """Post-process state (no-op for retry handler)."""
        return state

    def should_retry(self, state: dict[str, Any]) -> bool:
        """Check if a retry should be attempted based on state."""
        retry_count = state.get("retry_count", 0)
        return retry_count < self.max_retries
