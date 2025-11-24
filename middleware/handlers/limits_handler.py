"""
Limits Handler - Enforces hard ceilings on calls and depth.

Priority: 100 (first in chain)

Phase 2 Implementation.
"""

import logging
from typing import Any, Optional

from middleware.chain import MiddlewareHandler, ExecutionContext

logger = logging.getLogger(__name__)


class LimitsHandler(MiddlewareHandler):
    """
    Enforces hard ceilings on model/tool calls and recursion depth.

    Aborts the run if any limit is exceeded.
    """

    def __init__(self, config: dict[str, Any], priority: int = 100):
        super().__init__(name="LimitsHandler", priority=priority)

        # Load limits from config
        self.max_model_calls = config.get("max_model_calls_per_run", 30)
        self.max_tool_calls = config.get("max_tool_calls_per_run", 50)
        self.max_depth = config.get("max_depth_per_run", 8)
        self.max_iterations = config.get("max_iterations", 5)

        logger.info(
            f"LimitsHandler initialized: "
            f"model={self.max_model_calls}, tool={self.max_tool_calls}, "
            f"depth={self.max_depth}, iterations={self.max_iterations}"
        )

    def before_call(self, ctx: ExecutionContext) -> ExecutionContext:
        """Check limits before allowing the call."""

        # Check model call limit
        if ctx.model_name and ctx.model_calls >= self.max_model_calls:
            ctx.abort(f"Model call limit exceeded: {ctx.model_calls}/{self.max_model_calls}")
            ctx.metadata["limit_exceeded"] = "model_calls"
            logger.warning(f"Model call limit exceeded for run {ctx.run_id}")
            return ctx

        # Check tool call limit
        if ctx.tool_name and ctx.tool_calls >= self.max_tool_calls:
            ctx.abort(f"Tool call limit exceeded: {ctx.tool_calls}/{self.max_tool_calls}")
            ctx.metadata["limit_exceeded"] = "tool_calls"
            logger.warning(f"Tool call limit exceeded for run {ctx.run_id}")
            return ctx

        # Check depth limit
        if ctx.depth >= self.max_depth:
            ctx.abort(f"Depth limit exceeded: {ctx.depth}/{self.max_depth}")
            ctx.metadata["limit_exceeded"] = "depth"
            logger.warning(f"Depth limit exceeded for run {ctx.run_id}")
            return ctx

        # Check iteration limit
        if ctx.iteration >= self.max_iterations:
            ctx.abort(f"Iteration limit exceeded: {ctx.iteration}/{self.max_iterations}")
            ctx.metadata["limit_exceeded"] = "iterations"
            logger.warning(f"Iteration limit exceeded for run {ctx.run_id}")
            return ctx

        return ctx

    def after_call(self, ctx: ExecutionContext, result: Any) -> tuple[ExecutionContext, Any]:
        """Increment counters after successful call."""

        # Increment appropriate counter
        if ctx.model_name:
            ctx.increment_model_calls()
            logger.debug(f"Model calls: {ctx.model_calls}/{self.max_model_calls}")

        if ctx.tool_name:
            ctx.increment_tool_calls()
            logger.debug(f"Tool calls: {ctx.tool_calls}/{self.max_tool_calls}")

        return ctx, result

    def on_error(self, ctx: ExecutionContext, error: Exception) -> tuple[ExecutionContext, Optional[Exception]]:
        """Pass through errors (limits handler doesn't handle errors)."""
        return ctx, error

    def pre_process(self, state: dict[str, Any]) -> dict[str, Any]:
        """
        Pre-process state for limits checking.

        This is the simplified interface for direct state processing.
        """
        model_calls = state.get("model_calls", 0)
        tool_calls = state.get("tool_calls", 0)
        depth = state.get("depth", 0)
        iteration = state.get("iteration_count", 0)

        # Check model call limit
        if model_calls >= self.max_model_calls:
            raise ValueError(f"Model call limit exceeded: {model_calls}/{self.max_model_calls}")

        # Check tool call limit
        if tool_calls >= self.max_tool_calls:
            raise ValueError(f"Tool call limit exceeded: {tool_calls}/{self.max_tool_calls}")

        # Check depth limit
        if depth >= self.max_depth:
            raise ValueError(f"Depth limit exceeded: {depth}/{self.max_depth}")

        # Check iteration limit
        if iteration >= self.max_iterations:
            raise ValueError(f"Iteration limit exceeded: {iteration}/{self.max_iterations}")

        state["_limits_checked"] = True
        return state

    def post_process(self, state: dict[str, Any]) -> dict[str, Any]:
        """Post-process state (no-op for limits handler)."""
        return state
