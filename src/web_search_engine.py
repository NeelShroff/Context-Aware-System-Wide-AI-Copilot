"""
Web Search Engine Module.
Performs real-time web search queries (via DuckDuckGo HTML/API scraping)
to fetch search result snippets for LLM context enrichment.
"""
import re
import json
import logging
import urllib.request
import urllib.parse
from typing import Dict, Any, List

logger = logging.getLogger("WebSearchEngine")
logger.setLevel(logging.INFO)


class WebSearchEngine:
    """Provides fast web search snippet retrieval."""

    @staticmethod
    def search(query: str, max_results: int = 3) -> List[Dict[str, str]]:
        """Searches DuckDuckGo HTML and extracts clean title, snippet, and link dicts."""
        clean_query = query.strip()
        if not clean_query:
            return []

        # Remove search preambles if present
        clean_query = re.sub(r'^(search\s+the\s+web\s+for\s+|search\s+for\s+|look\s+up\s+)', '', clean_query, flags=re.IGNORECASE).strip()

        encoded_q = urllib.parse.quote_plus(clean_query)
        url = f"https://html.duckduckgo.com/html/?q={encoded_q}"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9"
        }

        results = []
        try:
            req = urllib.request.Request(url, headers=headers, method="GET")
            with urllib.request.urlopen(req, timeout=6.0) as resp:
                html = resp.read().decode("utf-8", errors="ignore")

            # Extract result snippets using regex on DuckDuckGo HTML output
            raw_blocks = re.findall(r'<a class="result__snippet[^>]*>(.*?)</a>', html, flags=re.DOTALL)
            raw_titles = re.findall(r'<a class="result__url[^>]*>(.*?)</a>', html, flags=re.DOTALL)

            for i in range(min(len(raw_blocks), max_results)):
                snippet = re.sub(r'<[^>]+>', '', raw_blocks[i]).strip()
                title = re.sub(r'<[^>]+>', '', raw_titles[i]).strip() if i < len(raw_titles) else f"Result #{i+1}"
                if snippet:
                    results.append({
                        "title": title,
                        "snippet": snippet
                    })
        except Exception as e:
            logger.warning(f"Web search request failed: {e}")

        return results

    @staticmethod
    def format_search_context(query: str) -> str:
        """Runs search and formats results into an XML block for LLM prompt insertion."""
        results = WebSearchEngine.search(query, max_results=3)
        if not results:
            return ""

        xml_items = "\n".join([
            f"  <web_result title=\"{r['title']}\">\n    {r['snippet']}\n  </web_result>"
            for r in results
        ])
        return f"<web_search_context query=\"{query}\">\n{xml_items}\n</web_search_context>"
