"""
Token tracking and cost monitoring for LangChain multi-agent systems.

This module provides a callback handler to track token usage per agent,
calculate costs, and maintain session history.
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult


@dataclass
class TokenMetrics:
    """Structured token usage metrics."""

    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_cost: float = 0.0
    call_count: int = 0


@dataclass
class CallRecord:
    """Record of a single LLM call."""

    timestamp: datetime
    agent: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost: float


class AgentTokenTracker(BaseCallbackHandler):
    """
    Custom callback handler to track token usage per agent with cost calculation.

    Features:
    - Per-agent token tracking
    - Automatic cost calculation for GPT-4o
    - Session history with timestamps
    - Formatted reports and summaries

    Usage:
        tracker = AgentTokenTracker()
        config = {"callbacks": [tracker]}
        result = agent.invoke(input, config)
        print(tracker.get_formatted_report())
    """

    # GPT-4o pricing (as of January 2025, per 1K tokens)
    PRICING = {
        "gpt-4o": {
            "input": 0.0025,  # $2.50 per 1M input tokens :contentReference[oaicite:0]{index=0}
            "output": 0.01,  # $10.00 per 1M output tokens :contentReference[oaicite:1]{index=1}
        },
        "gpt-4o-mini": {
            "input": 0.00015,  # $0.15 per 1M input tokens :contentReference[oaicite:2]{index=2}
            "output": 0.0006,  # $0.60 per 1M output tokens :contentReference[oaicite:3]{index=3}
        },
        "claude-sonnet-4-5-20250929": {"input": 0.003, "output": 0.006},  # (no new official change found)  # (no new official change found)
    }

    def __init__(self, model_name: str = "gpt-4o"):
        """
        Initialize the token tracker.

        Args:
            model_name: The model being used for cost calculation
        """
        super().__init__()
        self.model_name = model_name
        self.agent_metrics: Dict[str, TokenMetrics] = {}
        self.call_history: List[CallRecord] = []
        self.session_start = datetime.now()

    def _calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """
        Calculate cost based on token usage and model pricing.

        Args:
            prompt_tokens: Number of input tokens
            completion_tokens: Number of output tokens

        Returns:
            Total cost in USD
        """
        pricing = self.PRICING.get(self.model_name, self.PRICING["gpt-4o"])

        input_cost = (prompt_tokens / 1000) * pricing["input"]
        output_cost = (completion_tokens / 1000) * pricing["output"]

        return input_cost + output_cost

    def _get_agent_name(self, kwargs: Dict[str, Any]) -> str:
        """
        Extract agent name from callback kwargs.

        Args:
            kwargs: Callback keyword arguments

        Returns:
            Agent name or 'unknown'
        """
        # Try to get from tags first
        tags = kwargs.get("tags", [])

        # Look for agent names in tags
        agent_names = ["alice", "bob"]
        for tag in tags:
            if tag.lower() in agent_names:
                return tag.lower()

        # Try to get from metadata
        metadata = kwargs.get("metadata", {})
        if "agent" in metadata:
            return metadata["agent"]

        return "unknown"

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """
        Called when LLM finishes running.

        Args:
            response: The LLM result
            **kwargs: Additional callback arguments
        """
        # Extract agent name
        agent_name = self._get_agent_name(kwargs)

        # Get token usage from response
        usage = None
        if response.llm_output and "token_usage" in response.llm_output:
            usage = response.llm_output["token_usage"]

        if not usage:
            return

        # Extract token counts
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        total_tokens = usage.get("total_tokens", 0)

        # Calculate cost
        cost = self._calculate_cost(prompt_tokens, completion_tokens)

        # Initialize agent metrics if needed
        if agent_name not in self.agent_metrics:
            self.agent_metrics[agent_name] = TokenMetrics()

        # Update agent metrics
        metrics = self.agent_metrics[agent_name]
        metrics.total_tokens += total_tokens
        metrics.prompt_tokens += prompt_tokens
        metrics.completion_tokens += completion_tokens
        metrics.total_cost += cost
        metrics.call_count += 1

        # Record call history
        call_record = CallRecord(
            timestamp=datetime.now(),
            agent=agent_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost=cost,
        )
        self.call_history.append(call_record)

    def get_total_metrics(self) -> TokenMetrics:
        """
        Get aggregated metrics across all agents.

        Returns:
            Total metrics for all agents combined
        """
        total = TokenMetrics()
        for metrics in self.agent_metrics.values():
            total.total_tokens += metrics.total_tokens
            total.prompt_tokens += metrics.prompt_tokens
            total.completion_tokens += metrics.completion_tokens
            total.total_cost += metrics.total_cost
            total.call_count += metrics.call_count
        return total

    def get_agent_summary(self, agent_name: str) -> Optional[TokenMetrics]:
        """
        Get metrics for a specific agent.

        Args:
            agent_name: Name of the agent

        Returns:
            Metrics for the agent, or None if not found
        """
        return self.agent_metrics.get(agent_name)

    def get_session_duration(self) -> float:
        """
        Get session duration in seconds.

        Returns:
            Duration since tracker initialization
        """
        return (datetime.now() - self.session_start).total_seconds()

    def get_formatted_report(self, detailed: bool = False) -> str:
        """
        Generate a formatted report of token usage.

        Args:
            detailed: Whether to include call-by-call history

        Returns:
            Formatted string report
        """
        total = self.get_total_metrics()
        duration = self.get_session_duration()

        # Header
        report = "\n" + "=" * 80 + "\n"
        report += "TOKEN USAGE REPORT\n"
        report += "=" * 80 + "\n"

        # Session info
        report += f"\nSession Duration: {duration:.2f}s\n"
        report += f"Model: {self.model_name}\n"

        # Total summary
        report += "\n📊 TOTAL USAGE:\n"
        report += f"   Total Tokens:      {total.total_tokens:,}\n"
        report += f"   Prompt Tokens:     {total.prompt_tokens:,}\n"
        report += f"   Completion Tokens: {total.completion_tokens:,}\n"
        report += f"   Total Cost:        ${total.total_cost:.6f}\n"
        report += f"   Total Calls:       {total.call_count}\n"

        # Per-agent breakdown
        if self.agent_metrics:
            report += "\n🤖 PER-AGENT BREAKDOWN:\n"
            for agent_name, metrics in sorted(self.agent_metrics.items()):
                pct = (metrics.total_tokens / total.total_tokens * 100) if total.total_tokens > 0 else 0
                avg_tokens = metrics.total_tokens / metrics.call_count if metrics.call_count > 0 else 0

                report += f"\n   {agent_name.upper()}:\n"
                report += f"      Total Tokens:      {metrics.total_tokens:,} ({pct:.1f}%)\n"
                report += f"      Prompt Tokens:     {metrics.prompt_tokens:,}\n"
                report += f"      Completion Tokens: {metrics.completion_tokens:,}\n"
                report += f"      Cost:              ${metrics.total_cost:.6f}\n"
                report += f"      Calls:             {metrics.call_count}\n"
                report += f"      Avg Tokens/Call:   {avg_tokens:.0f}\n"

        # Call history (if detailed)
        if detailed and self.call_history:
            report += "\n📜 CALL HISTORY:\n"
            for i, call in enumerate(self.call_history, 1):
                time_str = call.timestamp.strftime("%H:%M:%S")
                report += f"\n   Call {i} [{time_str}] - {call.agent.upper()}:\n"
                report += f"      Tokens: {call.total_tokens:,} (prompt: {call.prompt_tokens:,}, completion: {call.completion_tokens:,})\n"
                report += f"      Cost: ${call.cost:.6f}\n"

        report += "\n" + "=" * 80 + "\n"

        return report

    def get_compact_summary(self) -> str:
        """
        Generate a compact one-line summary.

        Returns:
            Compact summary string
        """
        total = self.get_total_metrics()
        return f"💰 Tokens: {total.total_tokens:,} | Cost: ${total.total_cost:.4f} | Calls: {total.call_count}"

    def reset(self):
        """Reset all tracking data."""
        self.agent_metrics.clear()
        self.call_history.clear()
        self.session_start = datetime.now()


def create_tracker(model_name: str = "gpt-4o") -> AgentTokenTracker:
    """
    Convenience function to create a token tracker.

    Args:
        model_name: The model being used

    Returns:
        Initialized AgentTokenTracker instance
    """
    return AgentTokenTracker(model_name=model_name)
