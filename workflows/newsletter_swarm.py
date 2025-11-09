"""
Newsletter Swarm Workflow - Orchestrates all agents for newsletter generation.
"""

from typing import Any
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore
from langgraph_swarm import create_swarm

from agents.archive.researcher import create_researcher_agent
from agents.archive.planner import create_planner_agent
from agents.archive.writer import create_writer_agent
from agents.archive.editor import create_editor_agent
from agents.archive.diagram_creator import create_diagram_creator_agent
from utils.token_tracker import AgentTokenTracker


class NewsletterSwarm:
    """
    Multi-agent swarm for BigData newsletter generation.

    Agents can collaborate and hand off to each other:
    - Researcher: Gathers information
    - Planner: Structures content
    - Writer: Drafts newsletter
    - Editor: Reviews and refines
    - Diagram Creator: Creates visualizations
    """

    def __init__(self, enable_token_tracking: bool = True):
        """
        Initialize the newsletter swarm.

        Args:
            enable_token_tracking: Whether to track token usage
        """
        self.enable_token_tracking = enable_token_tracking

        # Create all agents
        print("🤖 Initializing agents.archive...")
        self.researcher = create_researcher_agent()
        self.planner = create_planner_agent()
        self.writer = create_writer_agent()
        self.editor = create_editor_agent()
        self.diagram_creator = create_diagram_creator_agent()

        # Create swarm
        print("🔗 Creating agent swarm...")
        self.workflow = create_swarm(
            [
                self.researcher,
                self.planner,
                self.writer,
                self.editor,
                self.diagram_creator,
            ],
            default_active_agent=self.planner.name,  # Start with planner
        )

        # Memory components
        self.checkpointer = InMemorySaver()
        self.store = InMemoryStore()

        # Compile workflow
        self.app = self.workflow.compile(checkpointer=self.checkpointer, store=self.store)

        # Token tracker
        self.tracker = None
        if self.enable_token_tracking:
            self.tracker = AgentTokenTracker(model_name="gpt-4o")

        print("✅ Newsletter swarm ready!")

    def generate_newsletter(
        self,
        topic: str,
        thread_id: str = "newsletter-1",
        additional_instructions: str = "",
        max_retries: int = 3,
    ) -> dict:
        """
        Generate a newsletter about a BigData topic.

        Args:
            topic: The BigData topic to write about
            additional_instructions: Optional additional instructions for the agents
            thread_id: Thread ID for conversation history
            max_retries: Maximum number of retries on validation errors (default: 3)

        Returns:
            Final result with messages and active agent
        """
        # Prepare the user message
        user_message = f"Write a detailed, appealing newsletter about {topic}."

        if additional_instructions:
            user_message += f"\n\nAdditional instructions: {additional_instructions}"

        print(f"\n📝 Starting newsletter generation for topic: {topic}")
        print("=" * 80)

        # Retry logic for intermittent langgraph-swarm validation errors
        for attempt in range(max_retries):
            try:
                # Use unique thread_id for each attempt to avoid state conflicts
                current_thread_id = f"{thread_id}-attempt-{attempt + 1}" if attempt > 0 else thread_id

                # Configure
                config: dict[str, Any] = {"configurable": {"thread_id": current_thread_id}}

                # Add token tracker if enabled
                if self.tracker:
                    config["callbacks"] = [self.tracker]

                # Invoke the swarm
                result = self.app.invoke({"messages": [{"role": "user", "content": user_message}]}, config)

                return result

            except ValueError as e:
                error_msg = str(e)
                # Check if it's the known validation error
                if "Found AIMessages with tool_calls that do not have a corresponding ToolMessage" in error_msg:
                    if attempt < max_retries - 1:
                        print(f"\n⚠️  Known validation error occurred (attempt {attempt + 1}/{max_retries})")
                        print("    Retrying with fresh state...")
                        continue
                    else:
                        print(f"\n❌ Maximum retries ({max_retries}) reached.")
                        print("    This is a known issue with langgraph-swarm 0.0.14")
                        raise
                else:
                    # Different error, re-raise immediately
                    raise

        # Should never reach here, but just in case
        raise RuntimeError("Failed to generate newsletter after all retries")

    def get_token_report(self) -> str:
        """Get token usage report."""
        if self.tracker:
            return self.tracker.get_formatted_report(detailed=True)
        return "Token tracking is disabled."

    def get_compact_summary(self) -> str:
        """Get compact token usage summary."""
        if self.tracker:
            return self.tracker.get_compact_summary()
        return "Token tracking is disabled."

    def reset_tracker(self):
        """Reset token tracking."""
        if self.tracker:
            self.tracker.reset()


def create_newsletter_swarm(enable_token_tracking: bool = True) -> NewsletterSwarm:
    """
    Create a newsletter generation swarm.

    Args:
        enable_token_tracking: Whether to track token usage

    Returns:
        Initialized NewsletterSwarm instance
    """
    return NewsletterSwarm(enable_token_tracking=enable_token_tracking)
