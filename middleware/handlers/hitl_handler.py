"""
HITL Handler - Human-in-the-Loop checkpoint management.

Priority: 300 (after PII redaction)

Phase 2 Implementation.
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Callable, Optional
from urllib.parse import urlparse

from middleware.chain import MiddlewareHandler, ExecutionContext

logger = logging.getLogger(__name__)


class HITLHandler(MiddlewareHandler):
    """
    Interrupts workflow for human approval at designated checkpoints.

    HITL Checkpoints:
    - web.fetch on unknown/low-trust domains
    - plagiarism.scan with external provider
    - publish action (always gated)
    """

    def __init__(self, config: dict[str, Any], priority: int = 300):
        super().__init__(name="HITLHandler", priority=priority)

        # Gate configuration
        self.gate_web_fetch_unknown = config.get("gate_web_fetch_unknown_domain", True)
        self.gate_plagiarism_external = config.get("gate_plagiarism_external", True)
        self.gate_publish = config.get("gate_publish", True)

        # Domain trust configuration
        self.allow_domains = set(config.get("allow_domains", []))
        self.deny_domains = set(config.get("deny_domains", []))

        # Timeout configuration
        self.approval_timeout = config.get("approval_timeout_seconds", 600)
        self.timeout_default = config.get("timeout_default_decision", "deny")

        # Approval callback (set externally)
        self._approval_callback: Optional[Callable[[dict], dict]] = None

        logger.info(f"HITLHandler initialized: allow_domains={len(self.allow_domains)}, deny_domains={len(self.deny_domains)}")

    def set_approval_callback(self, callback: Callable[[dict], dict]) -> None:
        """
        Set the approval callback function.

        Callback signature: (request: dict) -> {"decision": "approve"|"deny", "rationale": str}
        """
        self._approval_callback = callback

    def before_call(self, ctx: ExecutionContext) -> ExecutionContext:
        """Check if HITL approval is required."""

        # Check if this call requires HITL
        requires_hitl, reason, risk_data = self._check_hitl_required(ctx)

        if not requires_hitl:
            return ctx

        # Create HITL request
        checkpoint_id = str(uuid.uuid4())
        request = {
            "checkpoint_id": checkpoint_id,
            "agent": ctx.agent_name,
            "tool": ctx.tool_name,
            "args": ctx.input_data,
            "risk": risk_data,
            "state_preview": self._create_state_preview(ctx),
            "suggested_decision": self._suggest_decision(risk_data),
            "timeout_s": self.approval_timeout,
            "reason": reason,
        }

        ctx.hitl_required = True
        ctx.metadata["hitl_checkpoint_id"] = checkpoint_id
        ctx.metadata["hitl_request"] = request

        logger.info(f"HITL checkpoint triggered: {reason}")

        # Get approval
        if self._approval_callback:
            try:
                response = self._approval_callback(request)
                decision = response.get("decision", self.timeout_default)
                rationale = response.get("rationale", "")

                ctx.hitl_approved = decision == "approve"
                ctx.hitl_rationale = rationale

                # Record approval in state
                approval_record = {
                    "checkpoint_id": checkpoint_id,
                    "tool": ctx.tool_name,
                    "decision": decision,
                    "rationale": rationale,
                    "decided_at": datetime.now().isoformat(),
                    "risk": risk_data,
                }

                if "approvals" not in ctx.state:
                    ctx.state["approvals"] = []
                ctx.state["approvals"].append(approval_record)

                if not ctx.hitl_approved:
                    ctx.abort(f"HITL denied: {rationale or reason}")
                    logger.warning(f"HITL denied for {ctx.tool_name}: {rationale}")

            except Exception as e:
                logger.error(f"HITL callback failed: {e}")
                ctx.abort(f"HITL callback error: {e}")
        else:
            # No callback - abort with pending approval
            ctx.abort(f"HITL approval required: {reason}")
            logger.warning("HITL approval required but no callback set")

        return ctx

    def after_call(self, ctx: ExecutionContext, result: Any) -> tuple[ExecutionContext, Any]:
        """Log successful calls that required HITL."""
        if ctx.hitl_required and ctx.hitl_approved:
            logger.info(f"HITL-approved call completed: {ctx.tool_name}")
        return ctx, result

    def on_error(self, ctx: ExecutionContext, error: Exception) -> tuple[ExecutionContext, Optional[Exception]]:
        """Pass through errors."""
        return ctx, error

    def _check_hitl_required(self, ctx: ExecutionContext) -> tuple[bool, str, dict[str, Any]]:
        """
        Check if this call requires HITL approval.

        Returns: (requires_hitl, reason, risk_data)
        """
        # Check web.fetch
        if ctx.tool_name == "web.fetch" and self.gate_web_fetch_unknown:
            url = ctx.input_data.get("url", "")
            domain = self._extract_domain(url)
            trust_level = self._get_domain_trust(domain)

            if trust_level == "denied":
                return (
                    True,
                    f"Domain {domain} is in deny list",
                    {
                        "domain": domain,
                        "domain_trust": "denied",
                        "reason": "in-deny-list",
                    },
                )

            if trust_level in ("unknown", "low"):
                return (
                    True,
                    f"Domain {domain} is not in allow list",
                    {
                        "domain": domain,
                        "domain_trust": trust_level,
                        "reason": "not-in-allowlist",
                    },
                )

        # Check plagiarism.scan with external provider
        if ctx.tool_name == "plagiarism.scan" and self.gate_plagiarism_external:
            provider = ctx.input_data.get("provider", "internal")
            if provider == "external":
                return (
                    True,
                    "External plagiarism scan exposes draft content",
                    {
                        "provider": provider,
                        "reason": "external-api-exposure",
                    },
                )

        # Check publish action
        if ctx.tool_name == "publish" and self.gate_publish:
            return (
                True,
                "Publish action requires approval",
                {
                    "action": "publish",
                    "reason": "public-action",
                },
            )

        return False, "", {}

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            parsed = urlparse(url)
            return parsed.netloc.lower()
        except Exception:
            return ""

    def _get_domain_trust(self, domain: str) -> str:
        """Get trust level for a domain."""
        if domain in self.deny_domains:
            return "denied"
        if domain in self.allow_domains:
            return "high"
        # Check parent domains
        parts = domain.split(".")
        for i in range(len(parts) - 1):
            parent = ".".join(parts[i:])
            if parent in self.allow_domains:
                return "high"
            if parent in self.deny_domains:
                return "denied"
        return "unknown"

    def _create_state_preview(self, ctx: ExecutionContext) -> dict[str, Any]:
        """Create a preview of current state for HITL decision."""
        preview = {}

        state = ctx.state
        if "tasks" in state and state["tasks"]:
            task = state["tasks"][0] if isinstance(state["tasks"], list) else state["tasks"]
            if isinstance(task, dict):
                preview["topic"] = task.get("topic", "")

        if "citations" in state:
            preview["current_sources"] = len(state["citations"])

        if "facts" in state:
            preview["current_facts"] = len(state["facts"])

        preview["agent"] = ctx.agent_name
        preview["model_calls"] = ctx.model_calls
        preview["tool_calls"] = ctx.tool_calls

        return preview

    def _suggest_decision(self, risk_data: dict[str, Any]) -> str:
        """Suggest a decision based on risk data."""
        trust = risk_data.get("domain_trust", "unknown")

        if trust == "denied":
            return "deny"
        if trust == "high":
            return "approve"

        # Default to approve for unknown but log warning
        return "approve"

    def pre_process(self, state: dict[str, Any]) -> dict[str, Any]:
        """
        Pre-process state for HITL checking.

        This is the simplified interface for direct state processing.
        """
        tool_name = state.get("tool_name")
        tool_args = state.get("tool_args", {})

        # Check web.fetch
        if tool_name == "web.fetch" and self.gate_web_fetch_unknown:
            url = tool_args.get("url", "")
            domain = self._extract_domain(url)
            trust_level = self._get_domain_trust(domain)

            if trust_level in ("denied", "unknown", "low"):
                state["hitl_required"] = True
                state["hitl_reason"] = f"Domain {domain} is not in allow list (trust: {trust_level})"
                state["hitl_risk"] = {
                    "domain": domain,
                    "domain_trust": trust_level,
                }
            else:
                state["hitl_required"] = False
                state["hitl_reason"] = f"Domain {domain} is in allow list (trust: {trust_level})"
                state["hitl_risk"] = {
                    "domain": domain,
                    "domain_trust": trust_level,
                }

        return state

    def post_process(self, state: dict[str, Any]) -> dict[str, Any]:
        """Post-process state (no-op for HITL handler)."""
        return state
