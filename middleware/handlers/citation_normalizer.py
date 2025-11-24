"""
Citation Normalizer Handler - Normalizes and deduplicates citations.

Priority: 800 (last in chain)

Phase 2 Implementation.
"""

import hashlib
import logging
from datetime import datetime
from typing import Any, Optional
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

from middleware.chain import MiddlewareHandler, ExecutionContext

logger = logging.getLogger(__name__)


# Default tracking parameters to strip
DEFAULT_TRACKING_PARAMS = [
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_content",
    "utm_term",
    "ref",
    "source",
    "fbclid",
    "gclid",
    "msclkid",
    "dclid",
    "_ga",
    "_gl",
]


class CitationNormalizerHandler(MiddlewareHandler):
    """
    Normalizes web.fetch outputs into canonical citations.

    - Normalizes URLs (removes tracking params)
    - Generates stable source_id from URL hash
    - Deduplicates citations by URL
    - Updates state.citations[] automatically
    """

    def __init__(self, config: dict[str, Any], priority: int = 800):
        super().__init__(name="CitationNormalizerHandler", priority=priority)

        self.normalize_urls = config.get("normalize_urls", True)
        self.dedupe_by_url = config.get("dedupe_by_url", True)
        self.strip_tracking_params = config.get("strip_tracking_params", DEFAULT_TRACKING_PARAMS)
        self.source_id_method = config.get("source_id_method", "sha1")
        self.prefer_first_seen = config.get("prefer_first_seen", True)

        # Track seen URLs for deduplication
        self._seen_urls: dict[str, str] = {}  # normalized_url -> source_id

        logger.info(f"CitationNormalizerHandler initialized: normalize={self.normalize_urls}, dedupe={self.dedupe_by_url}")

    def before_call(self, ctx: ExecutionContext) -> ExecutionContext:
        """Pass through."""
        return ctx

    def after_call(self, ctx: ExecutionContext, result: Any) -> tuple[ExecutionContext, Any]:
        """Process web.fetch outputs into canonical citations."""

        # Only process web.fetch outputs
        if ctx.tool_name != "web.fetch":
            return ctx, result

        # Get URL from output
        output = ctx.output_data if isinstance(ctx.output_data, dict) else {}
        url = output.get("url", ctx.input_data.get("url", ""))

        if not url:
            return ctx, result

        # Normalize URL
        if self.normalize_urls:
            canonical_url = self._normalize_url(url)
        else:
            canonical_url = url

        # Generate source_id
        source_id = self._generate_source_id(canonical_url)

        # Check for duplicates
        is_duplicate = False
        existing_source_id = None

        if self.dedupe_by_url and canonical_url in self._seen_urls:
            is_duplicate = True
            existing_source_id = self._seen_urls[canonical_url]

            if self.prefer_first_seen:
                source_id = existing_source_id
                logger.debug(f"Duplicate URL, using existing source_id: {source_id}")

        # Track this URL
        if not is_duplicate:
            self._seen_urls[canonical_url] = source_id

        # Create canonical citation
        citation = {
            "source_id": source_id,
            "url": url,
            "canonical_url": canonical_url,
            "title": output.get("title", ""),
            "snippet": self._extract_snippet(output),
            "domain": self._extract_domain(canonical_url),
            "accessed_at": datetime.now().isoformat(),
            "is_duplicate": is_duplicate,
        }

        # Add domain trust if available
        if "domain_trust" in output:
            citation["domain_trust"] = output["domain_trust"]

        # Update output with canonical data
        output["canonical_url"] = canonical_url
        output["source_id"] = source_id
        output["is_duplicate"] = is_duplicate

        # Add citation to state
        if not is_duplicate:
            if "citations" not in ctx.state:
                ctx.state["citations"] = []

            # Check if already exists in state
            existing_ids = {c.get("source_id") for c in ctx.state["citations"]}
            if source_id not in existing_ids:
                ctx.state["citations"].append(citation)
                logger.debug(f"Added citation: {source_id} - {citation['title'][:50]}")

        ctx.output_data = output

        return ctx, result

    def on_error(self, ctx: ExecutionContext, error: Exception) -> tuple[ExecutionContext, Optional[Exception]]:
        """Pass through errors."""
        return ctx, error

    def _normalize_url(self, url: str) -> str:
        """
        Normalize URL by:
        - Converting to lowercase domain
        - Removing tracking parameters
        - Removing trailing slashes
        - Removing fragments
        """
        try:
            parsed = urlparse(url)

            # Parse and filter query params
            query_params = parse_qs(parsed.query)
            filtered_params = {k: v for k, v in query_params.items() if k.lower() not in [p.lower() for p in self.strip_tracking_params]}
            cleaned_query = urlencode(filtered_params, doseq=True)

            # Reconstruct URL
            normalized = urlunparse(
                (
                    parsed.scheme.lower(),
                    parsed.netloc.lower(),
                    parsed.path.rstrip("/") or "/",
                    parsed.params,
                    cleaned_query,
                    "",  # Remove fragment
                )
            )

            return normalized

        except Exception as e:
            logger.warning(f"URL normalization failed: {e}")
            return url

    def _generate_source_id(self, url: str) -> str:
        """Generate a stable source_id from URL."""
        if self.source_id_method == "sha1":
            hash_bytes = hashlib.sha1(url.encode()).hexdigest()[:8]
            return f"SRC_{hash_bytes.upper()}"
        elif self.source_id_method == "md5":
            hash_bytes = hashlib.md5(url.encode()).hexdigest()[:8]
            return f"SRC_{hash_bytes.upper()}"
        elif self.source_id_method == "incremental":
            count = len(self._seen_urls) + 1
            return f"SRC_{count:04d}"
        else:
            # Default to sha1
            hash_bytes = hashlib.sha1(url.encode()).hexdigest()[:8]
            return f"SRC_{hash_bytes.upper()}"

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            parsed = urlparse(url)
            return parsed.netloc.lower()
        except Exception:
            return ""

    def _extract_snippet(self, output: dict, max_length: int = 500) -> str:
        """Extract snippet from output."""
        # Try various fields
        for field in ["snippet", "content", "text", "description"]:
            if field in output:
                text = str(output[field])
                if len(text) > max_length:
                    # Truncate at sentence boundary if possible
                    truncate_at = max_length
                    last_period = text.rfind(".", 0, max_length)
                    if last_period > max_length // 2:
                        truncate_at = last_period + 1
                    return text[:truncate_at]
                return text
        return ""

    def clear_seen_urls(self) -> None:
        """Clear seen URLs (for testing or new run)."""
        self._seen_urls.clear()

    def get_citation_by_url(self, url: str) -> Optional[str]:
        """Get source_id for a URL if seen."""
        normalized = self._normalize_url(url) if self.normalize_urls else url
        return self._seen_urls.get(normalized)

    def pre_process(self, state: dict[str, Any]) -> dict[str, Any]:
        """Pre-process state (no-op for citation normalizer)."""
        return state

    def post_process(self, state: dict[str, Any]) -> dict[str, Any]:
        """
        Post-process state for citation normalization.

        Normalizes raw citations into canonical format.
        """
        raw_citations = state.get("raw_citations", [])
        if not raw_citations:
            return state

        normalized = []
        seen_urls = set()

        for citation in raw_citations:
            url = citation.get("url", "")

            # Normalize URL
            normalized_url = self._normalize_url(url) if hasattr(self, "_normalize_url") else url

            # Skip duplicates
            if normalized_url in seen_urls:
                continue
            seen_urls.add(normalized_url)

            # Generate source_id
            source_id = f"SRC_{hash(normalized_url) % 100000000:08X}"

            normalized.append(
                {
                    "source_id": source_id,
                    "url": normalized_url,
                    "title": citation.get("title", ""),
                    "snippet": citation.get("snippet", ""),
                    "domain": citation.get("domain", ""),
                }
            )

        if "citations" not in state:
            state["citations"] = []
        state["citations"].extend(normalized)

        return state
