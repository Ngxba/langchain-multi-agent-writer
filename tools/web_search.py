"""
Web search tool for retrieving latest BigData information from the internet.
"""

import os
from typing import Any, Optional

try:
    from langchain_tavily import TavilySearch
    TAVILY_AVAILABLE = True
except ImportError:
    TAVILY_AVAILABLE = False
    print("Warning: Tavily not installed. Web search will use mock mode.")


class WebSearchTool:
    """Web search functionality for BigData research."""

    def __init__(self, api_key: Optional[str] = None, max_results: int = 5):
        """
        Initialize web search tool.

        Args:
            api_key: Tavily API key (or from environment)
            max_results: Maximum number of search results
        """
        self.api_key = api_key or os.getenv("TAVILY_API_KEY", "")
        self.max_results = max_results
        self.use_mock = not self.api_key or not TAVILY_AVAILABLE

        if not self.use_mock:
            try:
                self.search_tool = TavilySearch(
                    max_results=max_results,
                    api_key=self.api_key
                )
            except Exception as e:
                print(f"Failed to initialize Tavily: {e}. Using mock mode.")
                self.use_mock = True

    def search(self, query: str) -> str:
        """
        Search the web for information.

        Args:
            query: Search query

        Returns:
            Formatted search results
        """
        if self.use_mock:
            return self._mock_search(query)

        try:
            results = self.search_tool.invoke(query)
            # TavilySearch returns a string directly, not a list
            if isinstance(results, str):
                return f"**Web Search Results:**\n\n{results}"
            else:
                return self._format_results(results)
        except Exception as e:
            print(f"Search error: {e}. Falling back to mock results.")
            return self._mock_search(query)

    def _format_results(self, results: Any) -> str:
        """Format search results into readable text."""
        # Handle string results (TavilySearch returns strings)
        if isinstance(results, str):
            return f"**Web Search Results:**\n\n{results}"

        # Handle list results (other search tools)
        if not results:
            return "No search results found."

        formatted = f"**Web Search Results:**\n\n"
        for i, result in enumerate(results, 1):
            if isinstance(result, dict):
                title = result.get("title", "No title")
                url = result.get("url", "")
                content = result.get("content", "No content available")

                formatted += f"**{i}. {title}**\n"
                formatted += f"   {content[:300]}...\n"  # Limit content length
                formatted += f"   Source: {url}\n\n"
            else:
                # Handle non-dict results
                formatted += f"{i}. {str(result)}\n\n"

        return formatted

    def _mock_search(self, query: str) -> str:
        """
        Provide mock search results when Tavily is unavailable.

        Args:
            query: Search query

        Returns:
            Mock search results
        """
        query_lower = query.lower()

        # Mock results based on query keywords
        if "kafka" in query_lower:
            return """**Web Search Results (Mock Mode):**

**1. Apache Kafka Reaches 3.7 Release with Major Improvements**
   Apache Kafka 3.7 introduces KRaft mode as the default, eliminating ZooKeeper dependency. The release includes improved performance, better observability, and enhanced security features. Organizations report 30% latency reduction with KRaft.
   Source: https://kafka.apache.org/releases

**2. Kafka Adoption Continues to Grow in 2025**
   Recent survey shows 80% of Fortune 100 companies now use Apache Kafka for real-time data streaming. Primary use cases include event sourcing, log aggregation, and microservices communication.
   Source: https://confluent.io/blog/kafka-adoption-2025

**3. Best Practices for Kafka in Production**
   Key recommendations include proper partitioning strategies, monitoring consumer lag, implementing idempotent producers, and configuring appropriate retention policies. Expert guidance on scaling Kafka clusters.
   Source: https://engineering.linkedin.com/blog/kafka-best-practices

Note: Using mock search results. For real-time information, configure TAVILY_API_KEY environment variable."""

        elif "spark" in query_lower:
            return """**Web Search Results (Mock Mode):**

**1. Apache Spark 3.5 Brings Performance Enhancements**
   Latest Spark release delivers 2x performance improvements for certain workloads through improved adaptive query execution and better memory management. New features include enhanced Python support and improved ML capabilities.
   Source: https://spark.apache.org/news

**2. Spark vs Flink: Choosing the Right Processing Engine**
   Comprehensive comparison of Apache Spark and Apache Flink for stream and batch processing. Spark excels in batch processing and ML workflows, while Flink offers true stream processing with lower latency.
   Source: https://databricks.com/blog/spark-flink-comparison

**3. Production Spark: Lessons from Scale**
   Real-world experiences scaling Spark clusters to petabyte-scale data processing. Covers optimization techniques, cost management, and operational best practices from industry leaders.
   Source: https://medium.com/netflix-techblog/spark-at-scale

Note: Using mock search results. For real-time information, configure TAVILY_API_KEY environment variable."""

        elif "data lake" in query_lower or "lakehouse" in query_lower:
            return """**Web Search Results (Mock Mode):**

**1. Data Lakehouse Architecture Gains Mainstream Adoption**
   The lakehouse pattern combining data lake flexibility with data warehouse structure is now industry standard. Delta Lake, Apache Iceberg, and Apache Hudi lead implementations with ACID guarantees.
   Source: https://databricks.com/blog/lakehouse-architecture

**2. Best Practices for Data Lake Implementation**
   Key success factors include data cataloging, proper partitioning, governance policies, and optimized file formats. Organizations achieve 60% cost reduction vs traditional data warehouses.
   Source: https://aws.amazon.com/blogs/big-data/data-lake-best-practices

**3. Open Table Formats Revolution: Delta, Iceberg, and Hudi**
   Comparison of leading open table formats. Each offers ACID transactions, time travel, and schema evolution but with different tradeoffs in performance and ecosystem support.
   Source: https://www.onehouse.ai/blog/table-formats-comparison

Note: Using mock search results. For real-time information, configure TAVILY_API_KEY environment variable."""

        else:
            return f"""**Web Search Results (Mock Mode):**

**1. BigData Trends in 2025**
   The data engineering landscape evolves with AI-powered tools, real-time processing dominance, and increased focus on data quality and governance. Organizations prioritize scalable, cost-effective solutions.
   Source: https://example.com/bigdata-trends-2025

**2. Modern Data Stack Evolution**
   Latest developments in data engineering include serverless architectures, improved observability, and DataOps practices. Focus shifts to developer experience and operational efficiency.
   Source: https://example.com/modern-data-stack

**3. Industry Report: Big Data Market Growth**
   Big Data market expected to reach $450 billion by 2028. Key drivers include IoT expansion, AI/ML adoption, and real-time analytics requirements across industries.
   Source: https://example.com/market-research

Note: Using mock search results. Configure TAVILY_API_KEY environment variable for real-time web search. Query: "{query}"
"""


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
    search_tool = WebSearchTool(max_results=5)
    return search_tool.search(query)
