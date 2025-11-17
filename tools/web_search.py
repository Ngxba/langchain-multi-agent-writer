"""
Web search tool for retrieving latest BigData information from the internet.
"""

import os
import logging
from typing import Any, Optional

# Configure logger
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

try:
    from langchain_tavily import TavilySearch

    TAVILY_AVAILABLE = True
    logger.debug("Tavily library is available")
except ImportError:
    TAVILY_AVAILABLE = False
    logger.error("Tavily is not installed. Install with: pip install langchain-tavily")


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
        logger.info(f"Initializing WebSearchTool with max_results={max_results}")
        self.api_key = api_key or os.getenv("TAVILY_API_KEY", "")
        self.max_results = max_results

        if not TAVILY_AVAILABLE:
            logger.error("Tavily library is not available")
            raise ValueError("Tavily is not installed. Install with: pip install langchain-tavily")

        if not self.api_key:
            logger.error("TAVILY_API_KEY not found in environment")
            raise ValueError("TAVILY_API_KEY not found. Set it in .env file or environment variables.")

        logger.debug("Creating TavilySearch instance")
        self.search_tool = TavilySearch(max_results=max_results, tavily_api_key=self.api_key)
        logger.info("WebSearchTool initialized successfully")

    def search(self, query: str) -> str:
        """
        Search the web for information.

        Args:
            query: Search query

        Returns:
            Formatted search results
        """
        logger.info(f"Executing web search: query='{query}'")
        try:
            results = self.search_tool.invoke(query)
            logger.debug(f"Search completed: result type={type(results).__name__}")

            # TavilySearch returns a string directly, not a list
            if isinstance(results, str):
                logger.info(f"Search returned string result: {len(results)} chars")
                return f"**Web Search Results:**\n\n{results}"
            else:
                logger.debug("Formatting search results")
                formatted = self._format_results(results)
                logger.info(f"Search results formatted: {len(formatted)} chars")
                return formatted
        except Exception as e:
            logger.error(f"Web search failed: {e}")
            raise

    def _format_results(self, results: Any) -> str:
        """Format search results into readable text."""
        logger.debug(f"Formatting results: type={type(results).__name__}")

        # Handle Tavily dict response
        if isinstance(results, dict):
            # Extract the actual results array
            if "results" in results:
                search_results = results["results"]
                if not search_results:
                    logger.warning("No search results found in response")
                    return "No search results found."

                logger.info(f"Formatting {len(search_results)} search results")
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
                logger.debug("Using 'answer' field from results")
                return f"**Web Search Results:**\n\n{results['answer']}"

        # Handle string results (some APIs return strings directly)
        if isinstance(results, str):
            logger.debug("Results are already formatted as string")
            return f"**Web Search Results:**\n\n{results}"

        # Handle list results (other search tools)
        if isinstance(results, list):
            if not results:
                logger.warning("Empty results list")
                return "No search results found."

            logger.info(f"Formatting {len(results)} list results")
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

        logger.warning(f"Unexpected result format: {type(results)}")
        return "No search results found."


# Tool function for LangChain agents
def search_web(query: str) -> str:
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
    logger.info(f"search_web function called with query: '{query}'")
    try:
        search_tool = WebSearchTool(max_results=5)
        result = search_tool.search(query)
        logger.info("search_web completed successfully")
        return result
    except Exception as e:
        logger.error(f"search_web failed: {e}")
        raise
