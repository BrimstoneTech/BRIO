"""
Brio Search Module (brio_search.py)

Purpose: Hybrid Search Engine (Online/Offline) with User Approval Gating.
         Wires DuckDuckGo search + web scraping for real results.
         
v5.0 — Real web search via DuckDuckGo (free, no API key, no limits).
        Preserves the existing approval gate and Subjective Logic verification.

Dependencies: requests, beautifulsoup4 (both free, pip install)
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import re
import json
import logging
import time
import random

log = logging.getLogger("BrioSearch")


class SearchStatus(Enum):
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    DENIED = "denied"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED_BY_PROTOCOL = "blocked_by_protocol"


@dataclass
class SearchRequest:
    query: str
    is_online: bool = False
    timestamp: datetime = field(default_factory=datetime.now)
    status: SearchStatus = SearchStatus.PENDING_APPROVAL
    result: Optional[str] = None
    justification: str = ""


@dataclass
class SearchResult:
    """A single search result."""
    title: str
    url: str
    snippet: str
    source: str = "duckduckgo"
    confidence: float = 0.7


from brio_cognition import SubjectiveOpinion


class SearchEngine:
    """
    Manages information retrieval — local index + real DuckDuckGo search.
    Preserves approval gating for online searches.
    """

    def __init__(self, watchdog=None):
        self.history: List[SearchRequest] = []
        self.pending_requests: Dict[str, SearchRequest] = {}
        self.watchdog = watchdog
        self.auto_approve_online = False  # Set True for autonomous mode

        # Local Knowledge Base
        self.offline_index = {
            "brio": "Brio is a sentient AI companion designed to learn, grow, and assist.",
            "protocol": "The Master Protocol ensures the user's safety and well-being.",
            "emotion": "Emotions in Brio are vector-based states in R^6.",
            "engram": "Engrams are Brio's memory units — crystallized knowledge from experience.",
            "search": "Brio can search the web using DuckDuckGo (free, no API key needed).",
        }

        # Search cache (avoid repeat queries)
        self._cache: Dict[str, List[SearchResult]] = {}
        self._cache_ttl = 3600  # 1 hour

        # Import web tools
        self._requests = None
        self._bs4 = None
        self._init_web_tools()

    def _init_web_tools(self):
        """Import requests and BeautifulSoup (graceful fallback)."""
        try:
            import requests
            self._requests = requests
        except ImportError:
            log.warning("[Search] `requests` not installed. Online search disabled.")

        try:
            from bs4 import BeautifulSoup
            self._bs4 = BeautifulSoup
        except ImportError:
            log.warning("[Search] `beautifulsoup4` not installed. Page reading disabled.")

    def _report_heartbeat(self):
        if self.watchdog:
            self.watchdog.heartbeat("SearchEngine")

    # ─── PUBLIC API ──────────────────────────────────────────────────

    def request_search(self, query: str, is_online: bool = False, justification: str = "") -> str:
        """
        Initiate a search request. Offline searches execute immediately.
        Online searches require approval unless auto_approve_online is True.
        """
        self._report_heartbeat()

        # Protocol check — block harmful queries
        blocked_terms = {"harm", "malware", "exploit", "hack", "illegal"}
        if any(term in query.lower() for term in blocked_terms):
            if self.watchdog:
                self.watchdog.log_error("SearchEngine", f"Blocked Malicious Query: {query}")
            return "BLOCKED_Protocol_Violation"

        request_id = f"REQ_{int(datetime.now().timestamp())}_{len(self.history)}"

        req = SearchRequest(
            query=query,
            is_online=is_online,
            justification=justification,
            status=SearchStatus.PENDING_APPROVAL,
        )

        if not is_online:
            # Offline search — immediate
            req.status = SearchStatus.APPROVED
            req.result = self._execute_offline(query)
            req.status = SearchStatus.COMPLETED
            self.history.append(req)
            return req.result
        elif self.auto_approve_online:
            # Autonomous mode — auto-approve
            req.status = SearchStatus.APPROVED
            results = self._execute_online(query)
            req.result = self._format_results(results)
            req.status = SearchStatus.COMPLETED
            self.history.append(req)
            return req.result
        else:
            # Needs user approval
            self.pending_requests[request_id] = req
            self.history.append(req)
            return request_id

    def approve_request(self, request_id: str) -> str:
        """User grants permission for a pending online search."""
        self._report_heartbeat()
        if request_id not in self.pending_requests:
            return "Error: Request ID not found."

        req = self.pending_requests[request_id]
        req.status = SearchStatus.APPROVED

        try:
            results = self._execute_online(req.query)
            req.result = self._format_results(results)
            req.status = SearchStatus.COMPLETED
            return req.result
        except Exception as e:
            req.status = SearchStatus.FAILED
            if self.watchdog:
                self.watchdog.log_error("SearchEngine", f"Online Search Failed: {e}", "CRITICAL")
            return f"Search failed: {e}"
        finally:
            self.pending_requests.pop(request_id, None)

    def deny_request(self, request_id: str) -> str:
        """User denies permission."""
        self._report_heartbeat()
        if request_id not in self.pending_requests:
            return "Error: Request ID not found."

        req = self.pending_requests[request_id]
        req.status = SearchStatus.DENIED
        self.pending_requests.pop(request_id, None)
        return "Search denied."

    def quick_search(self, query: str) -> List[SearchResult]:
        """
        Direct search — skips approval gate. Used by the curiosity loop
        when auto_approve_online is True.
        Returns raw SearchResult objects.
        """
        # Check cache first
        cache_key = query.lower().strip()
        if cache_key in self._cache:
            log.info(f"[Search] Cache hit for: {query}")
            return self._cache[cache_key]

        results = self._execute_online(query)
        self._cache[cache_key] = results
        return results

    def read_page(self, url: str, max_chars: int = 5000) -> str:
        """
        Fetch and extract readable text from a web page.
        Returns clean text content (no HTML).
        """
        if not self._requests or not self._bs4:
            return "Web reading unavailable — missing requests or beautifulsoup4."

        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (compatible; BrioBot/1.0; +https://brimstonetech.github.io)"
            }
            resp = self._requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()

            soup = self._bs4(resp.text, "html.parser")

            # Remove scripts, styles, nav, footer
            for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
                tag.decompose()

            # Extract text
            text = soup.get_text(separator="\n", strip=True)

            # Clean up whitespace
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            clean = "\n".join(lines)

            # Truncate
            if len(clean) > max_chars:
                clean = clean[:max_chars] + "\n\n[... content truncated ...]"

            return clean

        except Exception as e:
            log.error(f"[Search] Failed to read {url}: {e}")
            return f"Could not read page: {e}"

    def get_pending_count(self) -> int:
        return len(self.pending_requests)

    def get_search_history(self, limit: int = 10) -> List[dict]:
        """Return recent search history."""
        recent = self.history[-limit:]
        return [
            {
                "query": r.query,
                "online": r.is_online,
                "status": r.status.value,
                "result_preview": (r.result or "")[:200],
                "timestamp": r.timestamp.isoformat(),
            }
            for r in recent
        ]

    # ─── PRIVATE — Search Execution ─────────────────────────────────

    def _execute_offline(self, query: str) -> str:
        """Search local index."""
        query_lower = query.lower()
        results = []
        for key, content in self.offline_index.items():
            if key in query_lower or query_lower in content.lower():
                results.append(content)

        if not results:
            return "No local records found."
        return "\n".join(results)

    def _execute_online(self, query: str) -> List[SearchResult]:
        """
        Real DuckDuckGo search via HTML scraping.
        Free, no API key, no rate limits (be polite with delays).
        """
        if not self._requests or not self._bs4:
            log.warning("[Search] Web tools not available")
            return []

        results = []

        try:
            # DuckDuckGo HTML search
            url = "https://html.duckduckgo.com/html/"
            params = {"q": query}
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }

            resp = self._requests.post(url, data=params, headers=headers, timeout=15)
            resp.raise_for_status()

            soup = self._bs4(resp.text, "html.parser")

            # Parse results
            for result_div in soup.select(".result"):
                title_tag = result_div.select_one(".result__a")
                snippet_tag = result_div.select_one(".result__snippet")

                if not title_tag:
                    continue

                title = title_tag.get_text(strip=True)
                href = title_tag.get("href", "")
                snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""

                # DuckDuckGo wraps URLs — extract the real one
                real_url = self._extract_ddg_url(href)

                if title and real_url:
                    results.append(SearchResult(
                        title=title,
                        url=real_url,
                        snippet=snippet,
                        source="duckduckgo",
                        confidence=0.7,
                    ))

                if len(results) >= 8:  # Top 8 results
                    break

            # Small delay to be polite
            time.sleep(0.5)

        except Exception as e:
            log.error(f"[Search] DuckDuckGo search failed: {e}")

        # If DDG fails, try a simple fallback
        if not results:
            results = self._fallback_search(query)

        # Apply Subjective Logic confidence scoring
        results = self._score_with_logic(results, query)

        log.info(f"[Search] Found {len(results)} results for: {query}")
        return results

    def _extract_ddg_url(self, href: str) -> str:
        """Extract real URL from DuckDuckGo redirect wrapper."""
        if not href:
            return ""
        # DDG format: //duckduckgo.com/l/?uddg=ENCODED_URL&rut=...
        if "uddg=" in href:
            try:
                from urllib.parse import unquote, urlparse, parse_qs
                parsed = urlparse(href)
                params = parse_qs(parsed.query)
                if "uddg" in params:
                    return unquote(params["uddg"][0])
            except Exception:
                pass
        # Sometimes it's a direct URL
        if href.startswith("http"):
            return href
        if href.startswith("//"):
            return "https:" + href
        return href

    def _fallback_search(self, query: str) -> List[SearchResult]:
        """Fallback: return a helpful message if DDG fails."""
        return [SearchResult(
            title=f"Search for: {query}",
            url=f"https://duckduckgo.com/?q={query.replace(' ', '+')}",
            snippet=f"DuckDuckGo direct search link for '{query}'. Click to view results.",
            source="fallback",
            confidence=0.3,
        )]

    def _score_with_logic(self, results: List[SearchResult], query: str) -> List[SearchResult]:
        """Apply Subjective Logic confidence scoring to results."""
        query_words = set(query.lower().split())

        for r in results:
            # Base confidence from source
            belief = 0.5
            disbelief = 0.1
            uncertainty = 0.4

            # Boost if title/snippet match query words
            combined = (r.title + " " + r.snippet).lower()
            matches = sum(1 for w in query_words if w in combined and len(w) > 2)
            belief = min(0.9, belief + matches * 0.1)
            uncertainty = max(0.05, uncertainty - matches * 0.1)

            try:
                opinion = SubjectiveOpinion(belief, disbelief, uncertainty)
                r.confidence = round(opinion.get_probability_expectation(), 3)
            except Exception:
                r.confidence = round(belief, 3)

        # Sort by confidence
        results.sort(key=lambda r: r.confidence, reverse=True)
        return results

    def _format_results(self, results: List[SearchResult]) -> str:
        """Format search results as readable text."""
        if not results:
            return "No results found."

        lines = []
        for i, r in enumerate(results, 1):
            conf_label = "HIGH" if r.confidence > 0.7 else "MED" if r.confidence > 0.5 else "LOW"
            lines.append(f"{i}. [{conf_label}] {r.title}")
            lines.append(f"   {r.snippet}")
            lines.append(f"   Source: {r.url}")
            lines.append("")

        return "\n".join(lines)
