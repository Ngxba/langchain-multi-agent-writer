"""
Web Fetch Adapter - Wraps web fetch with middleware and strict schemas.

HITL GATED for unknown/low-trust domains.

Phase 2 Implementation.
"""

import logging
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

from tools.contracts import WebFetchInput, WebFetchOutput

logger = logging.getLogger(__name__)


class WebFetchAdapter:
    """
    Adapter for web fetch functionality.

    Wraps URL fetching with:
    - Input validation
    - Domain trust evaluation
    - HITL integration (via middleware)
    - Content extraction
    - Output normalization
    """

    # Known high-trust domains
    HIGH_TRUST_DOMAINS = {
        "kafka.apache.org",
        "spark.apache.org",
        "flink.apache.org",
        "databricks.com",
        "docs.databricks.com",
        "confluent.io",
        "docs.confluent.io",
        "aws.amazon.com",
        "docs.aws.amazon.com",
        "cloud.google.com",
        "github.com",
        "arxiv.org",
        "wikipedia.org",
        "langchain.com",
        "docs.langchain.com",
    }

    def __init__(self):
        self._http_client = None

    def fetch(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Fetch content from a URL.

        Args:
            input_data: Dict matching WebFetchInput schema

        Returns:
            Dict matching WebFetchOutput schema
        """
        # Validate input
        try:
            validated_input = WebFetchInput(**input_data)
        except Exception as e:
            logger.error(f"Invalid fetch input: {e}")
            raise ValueError(f"Invalid fetch input: {e}")

        url = validated_input.url
        domain = self._extract_domain(url)
        domain_trust = self._evaluate_domain_trust(domain)

        logger.info(f"Fetching: {url} (domain_trust: {domain_trust})")

        # Note: HITL gating is handled by middleware, not here
        # This adapter just does the actual fetch

        try:
            # Fetch content
            content, title, status = self._fetch_url(url, validated_input.max_length)

            # Create snippet
            snippet = content[:500] if content else ""

            # Create output
            output = WebFetchOutput(
                url=url,
                title=title,
                content=content,
                snippet=snippet,
                status=status,
                domain=domain,
                domain_trust=domain_trust,
                fetched_at=datetime.now(),
                hitl_required=domain_trust in ("unknown", "low"),
            )

            return output.model_dump()

        except Exception as e:
            logger.error(f"Fetch failed for {url}: {e}")
            # Return error output
            return {
                "url": url,
                "title": "",
                "content": "",
                "snippet": "",
                "status": 0,
                "domain": domain,
                "domain_trust": domain_trust,
                "error": str(e),
                "fetched_at": datetime.now().isoformat(),
            }

    def _fetch_url(self, url: str, max_length: int) -> tuple[str, str, int]:
        """
        Actually fetch the URL content.

        Returns: (content, title, status_code)
        """
        import urllib.request
        import urllib.error
        from html.parser import HTMLParser

        class TitleParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.in_title = False
                self.title = ""

            def handle_starttag(self, tag, attrs):
                if tag.lower() == "title":
                    self.in_title = True

            def handle_endtag(self, tag):
                if tag.lower() == "title":
                    self.in_title = False

            def handle_data(self, data):
                if self.in_title:
                    self.title += data

        try:
            # Create request with user agent
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; NewsletterBot/1.0)"})

            # Fetch with timeout
            with urllib.request.urlopen(req, timeout=30) as response:
                status = response.status
                content_type = response.headers.get("Content-Type", "")

                # Read content
                raw_content = response.read(max_length)

                # Decode
                encoding = "utf-8"
                if "charset=" in content_type:
                    encoding = content_type.split("charset=")[-1].split(";")[0].strip()

                try:
                    content = raw_content.decode(encoding)
                except (UnicodeDecodeError, LookupError):
                    content = raw_content.decode("utf-8", errors="replace")

                # Extract title
                title = ""
                if "text/html" in content_type:
                    parser = TitleParser()
                    try:
                        parser.feed(content[:10000])
                        title = parser.title.strip()
                    except Exception:
                        pass

                # Extract text if HTML
                if "text/html" in content_type:
                    content = self._extract_text_from_html(content)

                return content[:max_length], title, status

        except urllib.error.HTTPError as e:
            logger.warning(f"HTTP error {e.code} for {url}")
            return "", "", e.code

        except urllib.error.URLError as e:
            logger.error(f"URL error for {url}: {e}")
            raise

        except Exception as e:
            logger.error(f"Fetch error for {url}: {e}")
            raise

    def _extract_text_from_html(self, html: str) -> str:
        """Extract readable text from HTML."""
        import re

        # Remove script and style elements
        html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)

        # Remove HTML tags
        text = re.sub(r"<[^>]+>", " ", html)

        # Decode HTML entities
        import html as html_module

        text = html_module.unescape(text)

        # Normalize whitespace
        text = re.sub(r"\s+", " ", text)

        return text.strip()

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            return urlparse(url).netloc.lower()
        except Exception:
            return ""

    def _evaluate_domain_trust(self, domain: str) -> str:
        """Evaluate trust level for a domain."""
        if not domain:
            return "unknown"

        # Check direct match
        if domain in self.HIGH_TRUST_DOMAINS:
            return "high"

        # Check parent domains
        parts = domain.split(".")
        for i in range(len(parts) - 1):
            parent = ".".join(parts[i:])
            if parent in self.HIGH_TRUST_DOMAINS:
                return "high"

        # Check common trusted TLDs/patterns
        if any(domain.endswith(tld) for tld in [".gov", ".edu", ".org"]):
            return "medium"

        return "unknown"


# Singleton instance
_adapter = WebFetchAdapter()


def fetch_url(url: str, max_length: int = 10000, **kwargs) -> dict[str, Any]:
    """
    Fetch content from a URL.

    Note: This function should be called through middleware for HITL gating.

    Args:
        url: URL to fetch
        max_length: Maximum content length
        **kwargs: Additional options

    Returns:
        Dict with fetched content
    """
    input_data = {
        "url": url,
        "max_length": max_length,
        **kwargs,
    }
    return _adapter.fetch(input_data)
