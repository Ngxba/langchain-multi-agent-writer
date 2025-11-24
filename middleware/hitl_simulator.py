"""
HITL Simulator - Simulates human-in-the-loop approval for testing.

Provides configurable approval/denial policies for automated testing
and interactive mode for manual testing.

Phase 2 Implementation.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class HITLDecision(str, Enum):
    """HITL decision types."""

    APPROVE = "approve"
    DENY = "deny"
    TIMEOUT = "timeout"


class SimulatorMode(str, Enum):
    """HITL simulator modes."""

    AUTO_APPROVE = "auto_approve"
    AUTO_DENY = "auto_deny"
    POLICY = "policy"
    INTERACTIVE = "interactive"
    CALLBACK = "callback"


@dataclass
class HITLRequest:
    """A HITL approval request."""

    checkpoint_id: str
    agent: str
    tool: str
    args: dict[str, Any]
    risk: dict[str, Any]
    state_preview: dict[str, Any]
    suggested_decision: str
    timeout_s: int
    reason: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class HITLResponse:
    """A HITL approval response."""

    checkpoint_id: str
    decision: HITLDecision
    rationale: str
    constraints: dict[str, Any] = field(default_factory=dict)
    decided_at: datetime = field(default_factory=datetime.now)
    decided_by: str = "simulator"


class HITLSimulator:
    """
    Simulates HITL approval for testing.

    Modes:
    - auto_approve: Approve all requests
    - auto_deny: Deny all requests
    - policy: Apply configurable rules
    - interactive: Prompt for manual decision
    - callback: Use custom callback function
    """

    def __init__(
        self,
        mode: str | SimulatorMode = "policy",
        allow_domains: list[str] | None = None,
        deny_domains: list[str] | None = None,
        default_decision: HITLDecision = HITLDecision.APPROVE,
        log_decisions: bool = True,
    ):
        """
        Initialize HITL simulator.

        Args:
            mode: Simulation mode (auto_approve, auto_deny, policy, interactive, callback)
                  Can be a string or SimulatorMode enum
            allow_domains: Domains to auto-approve
            deny_domains: Domains to auto-deny
            default_decision: Default when no policy matches
            log_decisions: Whether to log all decisions
        """
        # Convert SimulatorMode enum to string if needed
        if isinstance(mode, SimulatorMode):
            self.mode = mode.value
        else:
            self.mode = mode
        self.allow_domains = set(allow_domains or [])
        self.deny_domains = set(deny_domains or [])
        self.default_decision = default_decision
        self.log_decisions = log_decisions

        # Decision history
        self.history: list[tuple[HITLRequest, HITLResponse]] = []

        # Custom callback
        self._callback: Optional[Callable[[HITLRequest], HITLResponse]] = None

        logger.info(f"HITLSimulator initialized in {mode} mode")

    def set_callback(self, callback: Callable[[HITLRequest], HITLResponse]) -> None:
        """Set custom callback for 'callback' mode."""
        self._callback = callback

    def process(self, request: dict[str, Any]) -> dict[str, Any]:
        """
        Process a HITL request (alias for decide).

        Args:
            request: HITL request dict

        Returns:
            Response dict with decision and rationale
        """
        return self.decide(request)

    def decide(self, request: dict[str, Any]) -> dict[str, Any]:
        """
        Make a HITL decision.

        This is the main entry point, compatible with HITLHandler's callback signature.

        Args:
            request: HITL request dict

        Returns:
            Response dict with decision and rationale
        """
        # Convert dict to HITLRequest
        hitl_request = HITLRequest(
            checkpoint_id=request.get("checkpoint_id", ""),
            agent=request.get("agent", ""),
            tool=request.get("tool", ""),
            args=request.get("args", {}),
            risk=request.get("risk", {}),
            state_preview=request.get("state_preview", {}),
            suggested_decision=request.get("suggested_decision", "approve"),
            timeout_s=request.get("timeout_s", 600),
            reason=request.get("reason", ""),
        )

        # Get response based on mode
        if self.mode == "auto_approve":
            response = self._auto_approve(hitl_request)
        elif self.mode == "auto_deny":
            response = self._auto_deny(hitl_request)
        elif self.mode == "policy":
            response = self._apply_policy(hitl_request)
        elif self.mode == "interactive":
            response = self._interactive_decision(hitl_request)
        elif self.mode == "callback" and self._callback:
            response = self._callback(hitl_request)
        else:
            response = self._apply_policy(hitl_request)

        # Log decision
        if self.log_decisions:
            logger.info(f"HITL decision: {response.decision.value} for {hitl_request.tool} ({hitl_request.reason}) - {response.rationale}")

        # Record history
        self.history.append((hitl_request, response))

        # Convert response to dict
        return {
            "checkpoint_id": response.checkpoint_id,
            "decision": response.decision.value,
            "rationale": response.rationale,
            "constraints": response.constraints,
        }

    def _auto_approve(self, request: HITLRequest) -> HITLResponse:
        """Auto-approve all requests."""
        return HITLResponse(
            checkpoint_id=request.checkpoint_id,
            decision=HITLDecision.APPROVE,
            rationale="Auto-approved by simulator",
        )

    def _auto_deny(self, request: HITLRequest) -> HITLResponse:
        """Auto-deny all requests."""
        return HITLResponse(
            checkpoint_id=request.checkpoint_id,
            decision=HITLDecision.DENY,
            rationale="Auto-denied by simulator",
        )

    def _apply_policy(self, request: HITLRequest) -> HITLResponse:
        """Apply policy-based decision."""
        risk = request.risk
        domain = risk.get("domain", "")

        # Check deny list first
        if domain and self._domain_matches(domain, self.deny_domains):
            return HITLResponse(
                checkpoint_id=request.checkpoint_id,
                decision=HITLDecision.DENY,
                rationale=f"Domain {domain} is in deny list",
            )

        # Check allow list
        if domain and self._domain_matches(domain, self.allow_domains):
            return HITLResponse(
                checkpoint_id=request.checkpoint_id,
                decision=HITLDecision.APPROVE,
                rationale=f"Domain {domain} is in allow list",
            )

        # Check domain trust level
        trust = risk.get("domain_trust", "unknown")
        if trust == "high":
            return HITLResponse(
                checkpoint_id=request.checkpoint_id,
                decision=HITLDecision.APPROVE,
                rationale="Domain has high trust level",
            )
        elif trust == "denied":
            return HITLResponse(
                checkpoint_id=request.checkpoint_id,
                decision=HITLDecision.DENY,
                rationale="Domain is explicitly denied",
            )

        # Domain not in allow list - deny by default in POLICY mode
        if domain:
            return HITLResponse(
                checkpoint_id=request.checkpoint_id,
                decision=HITLDecision.DENY,
                rationale=f"Domain {domain} is not in allow list",
            )

        # No domain info - use suggested decision or default
        suggested = request.suggested_decision.lower()
        if suggested in ("approve", "deny"):
            decision = HITLDecision.APPROVE if suggested == "approve" else HITLDecision.DENY
            return HITLResponse(
                checkpoint_id=request.checkpoint_id,
                decision=decision,
                rationale=f"Following suggested decision: {suggested}",
            )

        # Default
        return HITLResponse(
            checkpoint_id=request.checkpoint_id,
            decision=self.default_decision,
            rationale="Default decision (no domain info)",
        )

    def _interactive_decision(self, request: HITLRequest) -> HITLResponse:
        """Prompt for interactive decision."""
        print("\n" + "=" * 60)
        print("HITL APPROVAL REQUIRED")
        print("=" * 60)
        print(f"Agent: {request.agent}")
        print(f"Tool: {request.tool}")
        print(f"Reason: {request.reason}")
        print("\nRisk Assessment:")
        for key, value in request.risk.items():
            print(f"  {key}: {value}")
        print(f"\nArgs: {request.args}")
        print(f"\nSuggested: {request.suggested_decision}")
        print("-" * 60)

        while True:
            choice = input("Decision (a=approve, d=deny, r=rationale): ").strip().lower()

            if choice == "a":
                rationale = input("Rationale (optional): ").strip() or "Manually approved"
                return HITLResponse(
                    checkpoint_id=request.checkpoint_id,
                    decision=HITLDecision.APPROVE,
                    rationale=rationale,
                    decided_by="human",
                )
            elif choice == "d":
                rationale = input("Rationale (required): ").strip() or "Manually denied"
                return HITLResponse(
                    checkpoint_id=request.checkpoint_id,
                    decision=HITLDecision.DENY,
                    rationale=rationale,
                    decided_by="human",
                )
            else:
                print("Invalid choice. Enter 'a' for approve or 'd' for deny.")

    def _domain_matches(self, domain: str, domain_set: set[str]) -> bool:
        """Check if domain matches any in the set (including parent domains)."""
        domain = domain.lower()

        # Direct match
        if domain in domain_set:
            return True

        # Check parent domains
        parts = domain.split(".")
        for i in range(len(parts) - 1):
            parent = ".".join(parts[i:])
            if parent in domain_set:
                return True

        return False

    def get_history(self) -> list[tuple[HITLRequest, HITLResponse]]:
        """Get decision history."""
        return self.history

    def get_approval_count(self) -> int:
        """Get count of approved requests."""
        return sum(1 for _, r in self.history if r.decision == HITLDecision.APPROVE)

    def get_denial_count(self) -> int:
        """Get count of denied requests."""
        return sum(1 for _, r in self.history if r.decision == HITLDecision.DENY)

    def clear_history(self) -> None:
        """Clear decision history."""
        self.history.clear()

    def add_allow_domain(self, domain: str) -> None:
        """Add domain to allow list."""
        self.allow_domains.add(domain.lower())

    def add_deny_domain(self, domain: str) -> None:
        """Add domain to deny list."""
        self.deny_domains.add(domain.lower())


def create_auto_approve_simulator() -> HITLSimulator:
    """Create a simulator that auto-approves everything."""
    return HITLSimulator(mode="auto_approve")


def create_auto_deny_simulator() -> HITLSimulator:
    """Create a simulator that auto-denies everything."""
    return HITLSimulator(mode="auto_deny")


def create_policy_simulator(
    allow_domains: list[str] | None = None,
    deny_domains: list[str] | None = None,
) -> HITLSimulator:
    """Create a policy-based simulator."""
    return HITLSimulator(
        mode="policy",
        allow_domains=allow_domains,
        deny_domains=deny_domains,
    )


def create_interactive_simulator() -> HITLSimulator:
    """Create an interactive simulator for manual testing."""
    return HITLSimulator(mode="interactive")
