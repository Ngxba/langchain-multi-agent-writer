"""
Style Injector Handler - Injects style profile into prompts at runtime.

Priority: 700 (custom middleware)

Phase 2 Implementation.
"""

import json
import logging
from pathlib import Path
from typing import Any, Optional

from middleware.chain import MiddlewareHandler, ExecutionContext

logger = logging.getLogger(__name__)


class StyleInjectorHandler(MiddlewareHandler):
    """
    Injects style profile into agent prompts at runtime.

    Ensures consistent style across all agents.
    Falls back to default profile if specified profile not found.
    """

    DEFAULT_PROFILE = {
        "name": "Neutral-Concise",
        "voice": "neutral, confident, helpful",
        "sentence_length": "12-20 words",
        "structure": ["hook", "summary", "sections", "key-takeaways", "CTA"],
        "do_not_use": ["sensational claims", "vague sources"],
        "citation_policy": ">=2 independent sources for non-trivial claims; primary preferred",
    }

    def __init__(self, config: dict[str, Any] | None = None, priority: int = 700):
        super().__init__(name="StyleInjectorHandler", priority=priority)

        config = config or {}

        # Profile directory
        self.profile_dir = config.get("profile_dir", Path(__file__).parent.parent.parent / "config" / "style_profiles")
        if isinstance(self.profile_dir, str):
            self.profile_dir = Path(self.profile_dir)

        # Cache loaded profiles
        self._profile_cache: dict[str, dict] = {}

        logger.info(f"StyleInjectorHandler initialized: profile_dir={self.profile_dir}")

    def before_call(self, ctx: ExecutionContext) -> ExecutionContext:
        """Inject style profile into state before call."""

        # Check if style profile is already loaded
        if "style_profile" in ctx.state and ctx.state["style_profile"]:
            return ctx

        # Get profile ID from state or use default
        profile_id = ctx.state.get("style_profile_id", "neutral-concise")

        # Load profile
        profile = self._load_profile(profile_id)

        if profile:
            ctx.state["style_profile"] = profile
            ctx.metadata["style_profile_loaded"] = profile_id
            logger.debug(f"Loaded style profile: {profile_id}")
        else:
            # Use default
            ctx.state["style_profile"] = self.DEFAULT_PROFILE
            ctx.state["style_profile_used"] = "default"
            ctx.metadata["style_profile_fallback"] = True
            logger.warning(f"Profile {profile_id} not found, using default")

        return ctx

    def after_call(self, ctx: ExecutionContext, result: Any) -> tuple[ExecutionContext, Any]:
        """Pass through."""
        return ctx, result

    def on_error(self, ctx: ExecutionContext, error: Exception) -> tuple[ExecutionContext, Optional[Exception]]:
        """Pass through errors."""
        return ctx, error

    def _load_profile(self, profile_id: str) -> Optional[dict]:
        """Load a style profile by ID."""

        # Check cache
        if profile_id in self._profile_cache:
            return self._profile_cache[profile_id]

        # Try loading from file
        profile_path = self.profile_dir / f"{profile_id.replace('-', '_')}.json"

        if not profile_path.exists():
            # Try with original ID
            profile_path = self.profile_dir / f"{profile_id}.json"

        if profile_path.exists():
            try:
                with open(profile_path) as f:
                    profile = json.load(f)
                    self._profile_cache[profile_id] = profile
                    return profile
            except Exception as e:
                logger.error(f"Failed to load profile {profile_id}: {e}")
                return None

        # Try loading from __init__.py
        try:
            from config.style_profiles import get_profile

            profile = get_profile(profile_id)
            if profile:
                profile_dict = profile.model_dump() if hasattr(profile, "model_dump") else dict(profile)
                self._profile_cache[profile_id] = profile_dict
                return profile_dict
        except Exception as e:
            logger.debug(f"Could not load profile from module: {e}")

        return None

    def get_profile_for_prompt(self, profile: dict) -> str:
        """
        Convert profile to string for prompt injection.

        Returns a formatted string suitable for {STYLE_PROFILE} placeholder.
        """
        parts = []

        parts.append(f"## Style Profile: {profile.get('name', 'Default')}")
        parts.append("")

        # Voice & Tone
        if "voice" in profile:
            parts.append(f"**Voice**: {profile['voice']}")

        # Structure
        if "structure" in profile:
            structure = profile["structure"]
            if isinstance(structure, dict) and "sections" in structure:
                sections = structure["sections"]
            elif isinstance(structure, list):
                sections = structure
            else:
                sections = []

            if sections:
                parts.append(f"**Structure**: {' -> '.join(sections)}")

        # Sentence length
        if "sentence_length" in profile:
            parts.append(f"**Sentence Length**: {profile['sentence_length']}")

        # Do not use
        if "do_not_use" in profile:
            parts.append("")
            parts.append("**DO NOT USE:**")
            for item in profile["do_not_use"]:
                parts.append(f"- {item}")

        # Citation policy
        if "citation_policy" in profile:
            policy = profile["citation_policy"]
            if isinstance(policy, dict):
                min_sources = policy.get("min_sources_per_claim", 2)
                parts.append(f"**Citation Policy**: >={min_sources} independent sources per claim")
            else:
                parts.append(f"**Citation Policy**: {policy}")

        return "\n".join(parts)

    def clear_cache(self) -> None:
        """Clear profile cache."""
        self._profile_cache.clear()

    def pre_process(self, state: dict[str, Any]) -> dict[str, Any]:
        """
        Pre-process state for style profile injection.

        Ensures a style profile is available in state.
        """
        if "style_profile" not in state or state["style_profile"] is None:
            state["style_profile"] = self.DEFAULT_PROFILE
            state["style_profile_used"] = "default"

        return state

    def post_process(self, state: dict[str, Any]) -> dict[str, Any]:
        """Post-process state (no-op for style injector)."""
        return state
