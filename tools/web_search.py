"""
Web search tool for retrieving latest BigData information from the internet.
"""

import os
from typing import Any, Optional
from langchain.tools import tool, ToolRuntime

try:
    from langchain_tavily import TavilySearch

    TAVILY_AVAILABLE = True
except ImportError:
    TAVILY_AVAILABLE = False
    print("ERROR: Tavily is not installed. Install with: pip install langchain-tavily")


class WebSearchTool:
    """Web search functionality for BigData research using Tavily."""

    def __init__(self, api_key: Optional[str] = None, max_results: int = 5):
        """
        Initialize web search tool.

        Args:
            api_key: Tavily API key (or from environment)
            max_results: Maximum number of search results

        Raises:
            ValueError: If Tavily is not available or API key is missing
        """
        self.api_key = api_key or os.getenv("TAVILY_API_KEY", "")
        self.max_results = max_results

        if not TAVILY_AVAILABLE:
            raise ValueError("Tavily is not installed. Install with: pip install langchain-tavily")

        if not self.api_key:
            raise ValueError("TAVILY_API_KEY not found. Set it in .env file or environment variables.")

        self.search_tool = TavilySearch(max_results=max_results, tavily_api_key=self.api_key)

    def search(self, query: str) -> str:
        """
        Search the web for information.

        Args:
            query: Search query

        Returns:
            Formatted search results
        """
        results = self.search_tool.invoke(query)
        # TavilySearch returns a string directly, not a list
        if isinstance(results, str):
            return f"**Web Search Results:**\n\n{results}"
        else:
            return self._format_results(results)

    def _format_results(self, results: Any) -> str:
        """Format search results into readable text."""
        # Handle Tavily dict response
        if isinstance(results, dict):
            # Extract the actual results array
            if "results" in results:
                search_results = results["results"]
                if not search_results:
                    return "No search results found."

                formatted = "**Web Search Results:**\n\n"
                for i, result in enumerate(search_results[:5], 1):  # Limit to 5
                    title = result.get("title", "No title")
                    url = result.get("url", "")
                    content = result.get("content", "No content available")
                    formatted += f"**{i}. {title}**\n"
                    formatted += f"   {content[:400]}...\n"  # Show more content
                    formatted += f"   Source: {url}\n\n"
                return formatted
            # If 'answer' is provided, use that
            elif "answer" in results and results["answer"]:
                return f"**Web Search Results:**\n\n{results['answer']}"

        # Handle string results (some APIs return strings directly)
        if isinstance(results, str):
            return f"**Web Search Results:**\n\n{results}"

        # Handle list results (other search tools)
        if isinstance(results, list):
            if not results:
                return "No search results found."

            formatted = "**Web Search Results:**\n\n"
            for i, result in enumerate(results, 1):
                if isinstance(result, dict):
                    title = result.get("title", "No title")
                    url = result.get("url", "")
                    content = result.get("content", "No content available")

                    formatted += f"**{i}. {title}**\n"
                    formatted += f"   {content[:400]}...\n"  # Limit content length
                    formatted += f"   Source: {url}\n\n"
                else:
                    # Handle non-dict results
                    formatted += f"{i}. {str(result)}\n\n"

            return formatted

        return "No search results found."


# Tool function for LangChain agents
@tool
def search_web(query: str, runtime: ToolRuntime) -> str:
    """
    Search the web for latest BigData information, news, and trends.

    Use this tool when you need:
    - Latest news and announcements
    - Recent product releases or updates
    - Current industry trends
    - Real-world case studies
    - Statistics and market data

    Args:
        query: Search query (e.g., "Apache Kafka 2025 updates", "Data Mesh best practices")

    Returns:
        Formatted search results with titles, summaries, and sources
    """
    writer = runtime.stream_writer
    writer(f"Looking up internet data for : {query}")
    search_tool = WebSearchTool(max_results=5)
    return search_tool.search(query)
