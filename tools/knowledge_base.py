"""
Knowledge base search tool for retrieving BigData domain knowledge.
"""

import json
from typing import Dict, List, Any, Optional
from config.settings import KNOWLEDGE_BASE_PATH


class BigDataKnowledgeBase:
    """Local knowledge base for BigData topics."""

    def __init__(self, kb_path: str = KNOWLEDGE_BASE_PATH):
        """Initialize the knowledge base."""
        self.kb_path = kb_path
        self.data = self._load_knowledge_base()

    def _load_knowledge_base(self) -> Dict[str, Any]:
        """Load knowledge base from JSON file."""
        try:
            with open(self.kb_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Warning: Knowledge base not found at {self.kb_path}")
            return {"topics": {}, "trends": {}, "statistics": {}}
        except json.JSONDecodeError as e:
            print(f"Error parsing knowledge base: {e}")
            return {"topics": {}, "trends": {}, "statistics": {}}

    def search_topic(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Search for a specific topic in the knowledge base.

        Args:
            query: Topic name or keyword (e.g., "kafka", "apache kafka", "spark")

        Returns:
            Topic information if found, None otherwise
        """
        query_lower = query.lower().replace(" ", "_")

        # Direct lookup
        if query_lower in self.data.get("topics", {}):
            return self.data["topics"][query_lower]

        # Fuzzy search in topic names
        for topic_key, topic_data in self.data.get("topics", {}).items():
            topic_name = topic_data.get("name", "").lower()
            if query.lower() in topic_name or topic_name in query.lower():
                return topic_data

        return None

    def search_by_category(self, category: str) -> List[Dict[str, Any]]:
        """
        Search for topics by category.

        Args:
            category: Category name (e.g., "Stream Processing", "Data Storage")

        Returns:
            List of topics in that category
        """
        results = []
        for topic_data in self.data.get("topics", {}).values():
            if topic_data.get("category", "").lower() == category.lower():
                results.append(topic_data)
        return results

    def get_trends(self, year: Optional[str] = None) -> List[str]:
        """
        Get industry trends.

        Args:
            year: Specific year (e.g., "2025"), or None for latest

        Returns:
            List of trends
        """
        trends_data = self.data.get("trends", {})
        if year and year in trends_data:
            return trends_data[year]
        elif trends_data:
            # Return latest year's trends
            latest_year = max(trends_data.keys())
            return trends_data[latest_year]
        return []

    def get_statistics(self) -> Dict[str, str]:
        """Get industry statistics."""
        return self.data.get("statistics", {})

    def search_keywords(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """
        Search for topics containing any of the keywords.

        Args:
            keywords: List of keywords to search for

        Returns:
            List of matching topics
        """
        results = []
        keywords_lower = [k.lower() for k in keywords]

        for topic_data in self.data.get("topics", {}).values():
            # Search in name, description, and key features
            topic_text = json.dumps(topic_data).lower()
            if any(keyword in topic_text for keyword in keywords_lower):
                if topic_data not in results:
                    results.append(topic_data)

        return results


# Tool function for LangChain agents
def search_bigdata_knowledge(query: str) -> str:
    """
    Search the BigData knowledge base for information.

    Use this tool to find information about BigData technologies, best practices,
    use cases, and architectural patterns from a curated knowledge base.

    Args:
        query: The topic or keyword to search for (e.g., "Apache Kafka", "Data Lake", "Stream Processing")

    Returns:
        Formatted information about the topic
    """
    kb = BigDataKnowledgeBase()

    # Try direct topic search first
    topic = kb.search_topic(query)
    if topic:
        result = f"# {topic.get('name', query)}\n\n"
        result += f"**Category:** {topic.get('category', 'N/A')}\n\n"
        result += f"**Description:** {topic.get('description', 'N/A')}\n\n"

        if topic.get('key_features'):
            result += "**Key Features:**\n"
            for feature in topic['key_features']:
                result += f"- {feature}\n"
            result += "\n"

        if topic.get('use_cases'):
            result += "**Use Cases:**\n"
            for use_case in topic['use_cases']:
                result += f"- {use_case}\n"
            result += "\n"

        if topic.get('components'):
            result += f"**Components:** {', '.join(topic['components'])}\n\n"

        if topic.get('best_practices'):
            result += "**Best Practices:**\n"
            for practice in topic['best_practices']:
                result += f"- {practice}\n"
            result += "\n"

        if topic.get('technologies'):
            result += f"**Technologies:** {', '.join(topic['technologies'])}\n\n"

        return result

    # Try keyword search
    keywords = query.split()
    matches = kb.search_keywords(keywords)
    if matches:
        result = f"Found {len(matches)} related topics for '{query}':\n\n"
        for match in matches[:3]:  # Limit to top 3 matches
            result += f"**{match.get('name')}** ({match.get('category')})\n"
            result += f"{match.get('description')}\n\n"
        return result

    return f"No information found for '{query}' in the knowledge base. Consider using web search for this topic."


def get_industry_trends() -> str:
    """
    Get current BigData industry trends.

    Returns:
        Formatted list of current industry trends
    """
    kb = BigDataKnowledgeBase()
    trends = kb.get_trends()

    if trends:
        result = "**Current BigData Industry Trends:**\n\n"
        for i, trend in enumerate(trends, 1):
            result += f"{i}. {trend}\n"
        return result

    return "No trend information available."


def get_industry_statistics() -> str:
    """
    Get BigData industry statistics.

    Returns:
        Formatted industry statistics
    """
    kb = BigDataKnowledgeBase()
    stats = kb.get_statistics()

    if stats:
        result = "**BigData Industry Statistics:**\n\n"
        for key, value in stats.items():
            formatted_key = key.replace('_', ' ').title()
            result += f"**{formatted_key}:** {value}\n"
        return result

    return "No statistics available."
