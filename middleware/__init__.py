"""
Middleware Module for Newsletter Generation System.

This module provides the production middleware stack for:
- Call limits enforcement
- PII redaction
- Human-in-the-loop checkpoints
- Retry with exponential backoff
- Model fallback
- Context summarization
- Style profile injection
- Citation normalization

Phase 2 Implementation.
"""

from .chain import (
    MiddlewareChain,
    MiddlewareExecutor,
    SimpleMiddlewareChain,
    get_middleware_chain,
    reset_middleware_chain,
    ExecutionContext,
)
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
from .hitl_simulator import HITLSimulator, HITLDecision, SimulatorMode

__all__ = [
    # Chain
    "MiddlewareChain",
    "MiddlewareExecutor",
    "SimpleMiddlewareChain",
    "get_middleware_chain",
    "reset_middleware_chain",
    "ExecutionContext",
    # Handlers
    "LimitsHandler",
    "PIIHandler",
    "HITLHandler",
    "RetryHandler",
    "FallbackHandler",
    "SummarizationHandler",
    "StyleInjectorHandler",
    "CitationNormalizerHandler",
    # HITL
    "HITLSimulator",
    "HITLDecision",
    "SimulatorMode",
]
