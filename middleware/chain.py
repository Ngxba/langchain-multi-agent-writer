"""
Middleware Chain Orchestrator.

This module provides the chain of responsibility pattern for executing
middleware in the correct order with proper error handling.

Phase 2 Implementation.
"""

import logging
import yaml  # type: ignore
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Execution Context
# -----------------------------------------------------------------------------


@dataclass
class ExecutionContext:
    """
    Context passed through the middleware chain.

    Contains all information needed for middleware decisions and tracking.
    """

    # Identity
    run_id: str
    agent_name: str

    # Call info
    tool_name: Optional[str] = None
    model_name: Optional[str] = None
    input_data: dict[str, Any] = field(default_factory=dict)
    output_data: dict[str, Any] = field(default_factory=dict)

    # State reference
    state: dict[str, Any] = field(default_factory=dict)

    # Counters
    model_calls: int = 0
    tool_calls: int = 0
    depth: int = 0
    iteration: int = 0

    # Flags
    hitl_required: bool = False
    hitl_approved: Optional[bool] = None
    hitl_rationale: Optional[str] = None
    fallback_used: bool = False
    pii_redacted: bool = False
    summarized: bool = False
    aborted: bool = False
    abort_reason: Optional[str] = None

    # Metadata
    metadata: dict[str, Any] = field(default_factory=dict)
    started_at: datetime = field(default_factory=datetime.now)

    def increment_model_calls(self) -> None:
        """Increment model call counter."""
        self.model_calls += 1

    def increment_tool_calls(self) -> None:
        """Increment tool call counter."""
        self.tool_calls += 1

    def abort(self, reason: str) -> None:
        """Abort execution with reason."""
        self.aborted = True
        self.abort_reason = reason
        logger.warning(f"Execution aborted: {reason}")


@dataclass
class ExecutionResult:
    """Result from middleware chain execution."""

    success: bool
    output: Any = None
    context: Optional[ExecutionContext] = None
    error: Optional[Exception] = None
    error_message: Optional[str] = None


# -----------------------------------------------------------------------------
# Handler Protocol
# -----------------------------------------------------------------------------


class MiddlewareHandler:
    """
    Base class for middleware handlers.

    Handlers implement before_call, after_call, and on_error hooks.
    """

    def __init__(self, name: str, priority: int, enabled: bool = True):
        self.name = name
        self.priority = priority
        self.enabled = enabled

    def before_call(self, ctx: ExecutionContext) -> ExecutionContext:
        """
        Called before the target function.

        Can modify context or abort execution.
        """
        return ctx

    def after_call(self, ctx: ExecutionContext, result: Any) -> tuple[ExecutionContext, Any]:
        """
        Called after the target function.

        Can modify context and result.
        """
        return ctx, result

    def on_error(self, ctx: ExecutionContext, error: Exception) -> tuple[ExecutionContext, Optional[Exception]]:
        """
        Called when an error occurs.

        Can handle error (return None) or propagate (return error).
        """
        return ctx, error


# -----------------------------------------------------------------------------
# Middleware Chain
# -----------------------------------------------------------------------------


class MiddlewareChain:
    """
    Manages ordered execution of middleware handlers.

    Handlers are executed in priority order (lower = earlier).
    """

    def __init__(self):
        self.handlers: list[MiddlewareHandler] = []
        self._sorted = False

    def add(self, handler: MiddlewareHandler) -> "MiddlewareChain":
        """Add a handler to the chain."""
        self.handlers.append(handler)
        self._sorted = False
        return self

    def remove(self, name: str) -> "MiddlewareChain":
        """Remove a handler by name."""
        self.handlers = [h for h in self.handlers if h.name != name]
        return self

    def get(self, name: str) -> Optional[MiddlewareHandler]:
        """Get a handler by name."""
        for h in self.handlers:
            if h.name == name:
                return h
        return None

    def _ensure_sorted(self) -> None:
        """Ensure handlers are sorted by priority."""
        if not self._sorted:
            self.handlers.sort(key=lambda h: h.priority)
            self._sorted = True

    def execute(
        self,
        ctx: ExecutionContext,
        target: Callable[..., Any],
    ) -> ExecutionResult:
        """
        Execute the middleware chain around a target function.

        Args:
            ctx: Execution context
            target: Target function to wrap

        Returns:
            ExecutionResult with output and modified context
        """
        self._ensure_sorted()

        # Before phase
        for handler in self.handlers:
            if not handler.enabled:
                continue

            try:
                ctx = handler.before_call(ctx)
                if ctx.aborted:
                    return ExecutionResult(
                        success=False,
                        context=ctx,
                        error_message=ctx.abort_reason,
                    )
            except Exception as e:
                logger.error(f"Middleware {handler.name} before_call failed: {e}")
                return ExecutionResult(
                    success=False,
                    context=ctx,
                    error=e,
                    error_message=str(e),
                )

        # Execute target
        result = None
        error = None

        try:
            result = target(ctx.input_data)
            ctx.output_data = result if isinstance(result, dict) else {"result": result}
        except Exception as e:
            error = e
            logger.error(f"Target execution failed: {e}")

        # Error handling phase
        if error is not None:
            current_error: Exception | None = error
            for handler in reversed(self.handlers):
                if not handler.enabled:
                    continue
                if current_error is None:
                    break

                try:
                    ctx, current_error = handler.on_error(ctx, current_error)
                    if current_error is None:
                        # Error was handled, retry
                        try:
                            result = target(ctx.input_data)
                            ctx.output_data = result if isinstance(result, dict) else {"result": result}
                            break
                        except Exception as retry_error:
                            current_error = retry_error
                except Exception as handler_error:
                    logger.error(f"Middleware {handler.name} on_error failed: {handler_error}")
            error = current_error

            if error:
                return ExecutionResult(
                    success=False,
                    context=ctx,
                    error=error,
                    error_message=str(error),
                )

        # After phase
        for handler in reversed(self.handlers):
            if not handler.enabled:
                continue

            try:
                ctx, result = handler.after_call(ctx, result)
                if ctx.aborted:
                    return ExecutionResult(
                        success=False,
                        output=result,
                        context=ctx,
                        error_message=ctx.abort_reason,
                    )
            except Exception as e:
                logger.error(f"Middleware {handler.name} after_call failed: {e}")
                return ExecutionResult(
                    success=False,
                    output=result,
                    context=ctx,
                    error=e,
                    error_message=str(e),
                )

        return ExecutionResult(
            success=True,
            output=result,
            context=ctx,
        )

    def process_request(self, state: dict[str, Any], agent_name: str) -> dict[str, Any]:
        """
        Process a request through pre-processing middleware.

        Args:
            state: Current agent state
            agent_name: Name of the agent

        Returns:
            Processed state
        """
        self._ensure_sorted()
        for handler in self.handlers:
            if not handler.enabled:
                continue
            if hasattr(handler, "pre_process"):
                try:
                    state = handler.pre_process(state)
                except Exception as e:
                    logger.error(f"Pre-process failed for {handler.name}: {e}")
        return state

    def process_response(self, state: dict[str, Any], agent_name: str) -> dict[str, Any]:
        """
        Process a response through post-processing middleware.

        Args:
            state: Current agent state
            agent_name: Name of the agent

        Returns:
            Processed state
        """
        self._ensure_sorted()
        for handler in reversed(self.handlers):
            if not handler.enabled:
                continue
            if hasattr(handler, "post_process"):
                try:
                    state = handler.post_process(state)
                except Exception as e:
                    logger.error(f"Post-process failed for {handler.name}: {e}")
        return state


# -----------------------------------------------------------------------------
# Middleware Executor
# -----------------------------------------------------------------------------


class MiddlewareExecutor:
    """
    High-level executor that loads policy and creates middleware chain.
    """

    def __init__(self, policy_path: Optional[str] = None):
        self.policy = self._load_policy(policy_path)
        self.chain = MiddlewareChain()
        self._setup_chain()

    def _load_policy(self, policy_path: Optional[str]) -> dict[str, Any]:
        """Load policy configuration from YAML."""
        if policy_path is None:
            # Default path
            default_path = Path(__file__).parent.parent / "config" / "policy.yaml"
            if default_path.exists():
                policy_path = str(default_path)
            else:
                logger.warning("No policy.yaml found, using defaults")
                return {}

        try:
            with open(policy_path) as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.error(f"Failed to load policy: {e}")
            return {}

    def _setup_chain(self) -> None:
        """Set up middleware chain from policy."""
        from .handlers import (
            LimitsHandler,
            PIIHandler,
            HITLHandler,
            RetryHandler,
            FallbackHandler,
            SummarizationHandler,
            StyleInjectorHandler,
            CitationNormalizerHandler,
        )

        # Priority order from Phase 2 spec
        handlers = [
            (100, LimitsHandler, "limits"),
            (200, PIIHandler, "pii"),
            (300, HITLHandler, "hitl"),
            (400, RetryHandler, "retry"),
            (500, FallbackHandler, "fallback"),
            (600, SummarizationHandler, "summarization"),
            (700, StyleInjectorHandler, None),  # No policy section
            (800, CitationNormalizerHandler, "citations"),
        ]

        for priority, handler_class, policy_key in handlers:
            config = self.policy.get(policy_key, {}) if policy_key else {}
            try:
                handler = handler_class(config=config, priority=priority)
                self.chain.add(handler)
            except Exception as e:
                logger.error(f"Failed to create {handler_class.__name__}: {e}")

    def execute(
        self,
        run_id: str,
        agent_name: str,
        target: Callable[..., Any],
        input_data: dict[str, Any],
        tool_name: Optional[str] = None,
        model_name: Optional[str] = None,
        state: Optional[dict[str, Any]] = None,
    ) -> ExecutionResult:
        """
        Execute a function through the middleware chain.

        Args:
            run_id: Unique run identifier
            agent_name: Name of the calling agent
            target: Function to execute
            input_data: Input data for the function
            tool_name: Name of tool being called (if any)
            model_name: Name of model being called (if any)
            state: Current agent state

        Returns:
            ExecutionResult with output and context
        """
        ctx = ExecutionContext(
            run_id=run_id,
            agent_name=agent_name,
            tool_name=tool_name,
            model_name=model_name,
            input_data=input_data,
            state=state or {},
        )

        return self.chain.execute(ctx, target)

    def get_policy(self, section: str) -> dict[str, Any]:
        """Get a policy section."""
        return self.policy.get(section, {})

    def process_request(self, state: dict[str, Any], agent_name: str) -> dict[str, Any]:
        """
        Process a request through pre-processing middleware.

        Args:
            state: Current agent state
            agent_name: Name of the agent

        Returns:
            Processed state
        """
        for handler in self.chain.handlers:
            if not handler.enabled:
                continue
            if hasattr(handler, "pre_process"):
                try:
                    state = handler.pre_process(state)
                except Exception as e:
                    logger.error(f"Pre-process failed for {handler.name}: {e}")
        return state

    def process_response(self, state: dict[str, Any], agent_name: str) -> dict[str, Any]:
        """
        Process a response through post-processing middleware.

        Args:
            state: Current agent state
            agent_name: Name of the agent

        Returns:
            Processed state
        """
        for handler in reversed(self.chain.handlers):
            if not handler.enabled:
                continue
            if hasattr(handler, "post_process"):
                try:
                    state = handler.post_process(state)
                except Exception as e:
                    logger.error(f"Post-process failed for {handler.name}: {e}")
        return state


# -----------------------------------------------------------------------------
# Simple Middleware Chain for State Processing
# -----------------------------------------------------------------------------


class SimpleMiddlewareChain:
    """
    Simplified middleware chain for direct state processing.

    This is used when you don't need the full execute() flow
    and just want to process state through pre/post handlers.
    """

    def __init__(self, policy_path: Optional[str] = None):
        self.policy = self._load_policy(policy_path)
        self.handlers: list = []
        self._setup_handlers()

    def _load_policy(self, policy_path: Optional[str]) -> dict[str, Any]:
        """Load policy configuration from YAML."""
        if policy_path is None:
            default_path = Path(__file__).parent.parent / "config" / "policy.yaml"
            if default_path.exists():
                policy_path = str(default_path)
            else:
                return {}

        try:
            with open(policy_path) as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.error(f"Failed to load policy: {e}")
            return {}

    def _setup_handlers(self) -> None:
        """Set up handlers from policy."""
        from .handlers import (
            LimitsHandler,
            PIIHandler,
            HITLHandler,
            RetryHandler,
            FallbackHandler,
            SummarizationHandler,
            StyleInjectorHandler,
            CitationNormalizerHandler,
        )

        handler_configs = [
            (LimitsHandler, self.policy.get("limits", {})),
            (PIIHandler, {}),
            (HITLHandler, self.policy.get("hitl", {})),
            (RetryHandler, self.policy.get("retry", {})),
            (FallbackHandler, self.policy.get("fallback", {})),
            (SummarizationHandler, self.policy.get("summarization", {})),
            (StyleInjectorHandler, {}),
            (CitationNormalizerHandler, self.policy.get("citations", {})),
        ]

        for handler_class, config in handler_configs:
            try:
                handler = handler_class(config)
                self.handlers.append(handler)
            except Exception as e:
                logger.warning(f"Failed to create {handler_class.__name__}: {e}")

    def process_request(self, state: dict[str, Any], agent_name: str) -> dict[str, Any]:
        """Process state through pre-processing handlers."""
        for handler in self.handlers:
            if hasattr(handler, "pre_process"):
                try:
                    state = handler.pre_process(state)
                except Exception as e:
                    logger.warning(f"Pre-process failed for {handler.__class__.__name__}: {e}")
        return state

    def process_response(self, state: dict[str, Any], agent_name: str) -> dict[str, Any]:
        """Process state through post-processing handlers."""
        for handler in reversed(self.handlers):
            if hasattr(handler, "post_process"):
                try:
                    state = handler.post_process(state)
                except Exception as e:
                    logger.warning(f"Post-process failed for {handler.__class__.__name__}: {e}")
        return state


# -----------------------------------------------------------------------------
# Global Instance
# -----------------------------------------------------------------------------

_middleware_chain: Optional[SimpleMiddlewareChain] = None


def get_middleware_chain(policy_path: Optional[str] = None) -> SimpleMiddlewareChain:
    """
    Get the global middleware chain instance.

    Args:
        policy_path: Optional path to policy.yaml

    Returns:
        SimpleMiddlewareChain instance
    """
    global _middleware_chain
    if _middleware_chain is None:
        _middleware_chain = SimpleMiddlewareChain(policy_path)
    return _middleware_chain


def reset_middleware_chain() -> None:
    """Reset the global middleware chain (useful for testing)."""
    global _middleware_chain
    _middleware_chain = None
