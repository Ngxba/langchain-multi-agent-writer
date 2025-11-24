"""
Web Search Adapter - Wraps web search with middleware and strict schemas.

Not HITL gated - search queries are considered safe.

Phase 2 Implementation.
"""

import logging
from typing import Any

from tools.contracts import WebSearchInput, WebSearchOutput, WebSearchResult

logger = logging.getLogger(__name__)


class WebSearchAdapter:
    """
    Adapter for web search functionality.

    Wraps the underlying search tool with:
    - Input validation
    - Output normalization
    - Error handling
    - Logging
    """

    def __init__(self, max_results: int = 5):
        self.max_results = max_results
        self._search_tool = None

    def _get_search_tool(self):
        """Lazy initialization of search tool."""
        if self._search_tool is None:
            try:
                from tools.web_search import WebSearchTool

                self._search_tool = WebSearchTool(max_results=self.max_results)
            except Exception as e:
                logger.warning(f"Could not initialize WebSearchTool: {e}")
                self._search_tool = None
        return self._search_tool

    def search(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Execute a web search.

        Args:
            input_data: Dict matching WebSearchInput schema

        Returns:
            Dict matching WebSearchOutput schema
        """
        # Validate input
        try:
            validated_input = WebSearchInput(**input_data)
        except Exception as e:
            logger.error(f"Invalid search input: {e}")
            raise ValueError(f"Invalid search input: {e}")

        logger.info(f"Searching: {validated_input.query}")

        # Get search tool
        search_tool = self._get_search_tool()

        if search_tool is None:
            # Return mock results for testing
            return self._mock_search(validated_input)

        try:
            # Execute search
            raw_results = search_tool.search(validated_input.query)

            # Parse and normalize results
            results = self._parse_results(raw_results, validated_input)

            # Create output
            output = WebSearchOutput(
                query=validated_input.query,
                results=results,
                total_results=len(results),
            )

            return output.model_dump()

        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise

    def _parse_results(
        self,
        raw_results: Any,
        input_data: WebSearchInput,
    ) -> list[WebSearchResult]:
        """Parse raw search results into normalized format."""
        results = []

        # Handle string results
        if isinstance(raw_results, str):
            # Try to extract structured data from string
            # For now, return as single result
            results.append(
                WebSearchResult(
                    title="Search Results",
                    url="",
                    snippet=raw_results[:500],
                    domain="",
                )
            )
            return results

        # Handle dict with 'results' key
        if isinstance(raw_results, dict) and "results" in raw_results:
            raw_results = raw_results["results"]

        # Handle list of results
        if isinstance(raw_results, list):
            for item in raw_results[: input_data.k]:
                if isinstance(item, dict):
                    snippet_content = item.get("content") or item.get("snippet") or ""
                    result = WebSearchResult(
                        title=item.get("title", "No title"),
                        url=item.get("url", ""),
                        snippet=snippet_content[:500],
                        domain=self._extract_domain(item.get("url", "")),
                    )
                    results.append(result)

        return results

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            from urllib.parse import urlparse

            return urlparse(url).netloc.lower()
        except Exception:
            return ""

    def _mock_search(self, input_data: WebSearchInput) -> dict[str, Any]:
        """Return mock results for testing when no API is available."""
        logger.warning("Using mock search results")

        mock_results = [
            WebSearchResult(
                title=f"Mock Result for: {input_data.query}",
                url="https://example.com/mock",
                snippet=f"This is a mock search result for '{input_data.query}'. Use a real search API for production.",
                domain="example.com",
            ),
        ]

        output = WebSearchOutput(
            query=input_data.query,
            results=mock_results,
            total_results=1,
        )

        return output.model_dump()


# Singleton instance
_adapter = WebSearchAdapter()


def search_web(query: str, k: int = 5, **kwargs) -> dict[str, Any]:
    """
    Search the web for information.

    Args:
        query: Search query string
        k: Number of results to return
        **kwargs: Additional options

    Returns:
        Dict with search results
    """
    input_data = {
        "query": query,
        "k": k,
        **kwargs,
    }
    return _adapter.search(input_data)
