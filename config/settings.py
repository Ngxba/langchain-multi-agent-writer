"""
Non-agent configuration settings.

Agent-related configs are in config/__init__.py and config/agents.yaml.
This file only contains application-level settings.
"""

import os

# =============================================================================
# MODEL PRESETS
# =============================================================================

DEFAULT_MODEL = "gpt-4o"
DEFAULT_MODEL_MINI = "gpt-4o-mini"
CLAUDE_MODEL_4_DOT_5 = "claude-sonnet-4-5-20250929"


# =============================================================================
# WEB SEARCH
# =============================================================================

SEARCH_MAX_RESULTS = 5


# =============================================================================
# OUTPUT PATHS
# =============================================================================

OUTPUT_DIR = "outputs"
DIAGRAMS_DIR = os.path.join(OUTPUT_DIR, "diagrams")


def ensure_output_dirs():
    """Ensure output directories exist."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(DIAGRAMS_DIR, exist_ok=True)


# =============================================================================
# TOKEN TRACKING
# =============================================================================

ENABLE_TOKEN_TRACKING = True
TOKEN_BUDGET_WARNING_THRESHOLD = 0.05  # Warn at $0.05


# =============================================================================
# NEWSLETTER DEFAULTS
# =============================================================================

NEWSLETTER_CONFIG = {
    "default_sections": [
        "Introduction",
        "Key Highlights",
        "Deep Dive",
        "Industry Trends",
        "Best Practices",
        "Conclusion",
    ],
    "target_word_count": 800,
    "tone": "professional yet engaging",
    "audience": "data engineers and architects",
}
