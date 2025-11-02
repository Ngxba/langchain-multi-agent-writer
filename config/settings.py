"""
Configuration settings for the BigData Newsletter Agent Swarm.
"""

import os
from typing import Dict, Any

# Model Configuration
DEFAULT_MODEL = "gpt-4o"
DEFAULT_MODEL_MINI = "gpt-4o-mini"  # For less critical tasks

# Agent Configuration
AGENT_CONFIG = {
    "researcher": {
        "model": DEFAULT_MODEL,
        "temperature": 0.7,
        "description": "BigData research specialist who gathers information from web and knowledge bases"
    },
    "planner": {
        "model": DEFAULT_MODEL,
        "temperature": 0.5,
        "description": "Content planning expert who structures newsletters for maximum engagement"
    },
    "writer": {
        "model": DEFAULT_MODEL,
        "temperature": 0.8,
        "description": "BigData technical writer who creates detailed, appealing content"
    },
    "editor": {
        "model": DEFAULT_MODEL,
        "temperature": 0.3,
        "description": "Quality review specialist who refines and improves content"
    },
    "diagram_creator": {
        "model": DEFAULT_MODEL_MINI,
        "temperature": 0.2,
        "description": "Technical diagram creator for DrawIO visualizations"
    }
}

# Web Search Configuration
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
SEARCH_MAX_RESULTS = 5

# Knowledge Base Configuration
KNOWLEDGE_BASE_PATH = "data/bigdata_knowledge.json"

# Output Configuration
OUTPUT_DIR = "outputs"
DIAGRAMS_DIR = os.path.join(OUTPUT_DIR, "diagrams")

# Token Tracking
ENABLE_TOKEN_TRACKING = True
TOKEN_BUDGET_WARNING_THRESHOLD = 0.05  # Warn at $0.05

# Newsletter Configuration
NEWSLETTER_CONFIG = {
    "default_sections": [
        "Introduction",
        "Key Highlights",
        "Deep Dive",
        "Industry Trends",
        "Best Practices",
        "Conclusion"
    ],
    "target_word_count": 800,
    "tone": "professional yet engaging",
    "audience": "data engineers and architects"
}

# BigData Topics (for knowledge base reference)
BIGDATA_TOPICS = [
    "Apache Kafka",
    "Apache Spark",
    "Apache Flink",
    "Hadoop",
    "Data Lakes",
    "Data Warehouses",
    "Stream Processing",
    "Batch Processing",
    "Delta Lake",
    "Apache Iceberg",
    "Data Mesh",
    "Data Quality",
    "ETL/ELT",
    "Real-time Analytics",
    "Data Governance"
]


def get_agent_config(agent_name: str) -> Dict[str, Any]:
    """Get configuration for a specific agent."""
    return AGENT_CONFIG.get(agent_name, {})


def ensure_output_dirs():
    """Ensure output directories exist."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(DIAGRAMS_DIR, exist_ok=True)
