"""
Brio Web Sifter (brio_web_sifter.py)

Purpose: Targeted fact extraction to expand Brio's internal Engram base.

v5.0 — Real web scraping via requests + BeautifulSoup.
        Reads actual pages, extracts facts, stores as engrams.
        Integrates with the SearchEngine for discovery.
"""

import re
import logging
import time
from typing import List, Optional, Dict
from datetime import datetime

log = logging.getLogger("BrioSifter")


class WebSifter:
    """
    Sifts the web for knowledge and crystallizes it into Brio's engram memory.
    
    Flow: Query → Search → Read top pages → Extract key facts → Store as engrams
    """

    def __init__(self, system_ref):
        self.system = system_ref
        self.sift_history: List[dict] = []
        self.max_history = 100

    def search_and_ingest(self, query: str, max_pages: int = 3) -> str:
        """
        Perform a real web search, read top pages, extract facts, store as engrams.
        Returns a summary of what was learned.
        """
        log.info(f"[Sifter] Sifting web for: {query}")

        if not self.system.search:
            return "Search engine offline — cannot sift the web."

        # 1. Search
        results = self.system.search.quick_search(query)
        if not results:
            return f"No results found for '{query}'. The web gave me nothing today."

        # 2. Read top pages
        facts_collected = []
        pages_read = 0

        for result in results[:max_pages]:
            try:
                page_text = self.system.search.read_page(result.url, max_chars=3000)
                if not page_text or "Could not read" in page_text:
                    continue

                pages_read += 1

                # 3. Extract key facts using Ollama
                facts = self._extract_facts(query, result.title, page_text)
                if facts:
                    facts_collected.extend(facts)

                # Be polite — small delay between page reads
                time.sleep(0.5)

            except Exception as e:
                log.warning(f"[Sifter] Failed to read {result.url}: {e}")
                continue

        # 4. Store as engrams
        engrams_created = 0
        for fact in facts_collected:
            if fact and len(fact) > 20:  # Skip tiny fragments
                self.system.knowledge.learn(
                    content=fact,
                    emotion="curiosity",
                    importance=0.8,
                )
                engrams_created += 1

        # 5. Record in history
        record = {
            "query": query,
            "timestamp": datetime.now().isoformat(),
            "pages_read": pages_read,
            "facts_extracted": len(facts_collected),
            "engrams_created": engrams_created,
            "sources": [r.url for r in results[:max_pages]],
        }
        self.sift_history.append(record)
        if len(self.sift_history) > self.max_history:
            self.sift_history.pop(0)

        # 6. Summary
        summary = (
            f"Sifting complete for '{query}'.\n"
            f"📖 Read {pages_read} pages | "
            f"💡 Extracted {len(facts_collected)} facts | "
            f"🧠 Crystallized {engrams_created} new engrams."
        )
        log.info(f"[Sifter] {summary}")
        return summary

    def _extract_facts(self, query: str, title: str, page_text: str) -> List[str]:
        """
        Extract key facts from page text.
        Uses Ollama if available, falls back to heuristic extraction.
        """
        # Try Ollama-powered extraction first
        if self.system.mind:
            return self._extract_with_ollama(query, title, page_text)
        else:
            return self._extract_heuristic(query, page_text)

    def _extract_with_ollama(self, query: str, title: str, page_text: str) -> List[str]:
        """Use Ollama to intelligently extract relevant facts."""
        # Truncate page text for the prompt
        truncated = page_text[:2000]

        extraction_prompt = (
            f"You are a knowledge extraction system. Read this web page content about '{query}' "
            f"from '{title}' and extract 3-5 key facts. Each fact should be a single, clear, "
            f"self-contained sentence that would be useful to remember.\n\n"
            f"Page content:\n{truncated}\n\n"
            f"Return ONLY the facts, one per line, numbered 1-5. No commentary."
        )

        try:
            response, _ = self.system.mind.think(
                extraction_prompt,
                override_prompt="You are a precise fact extractor. Return only numbered facts."
            )

            # Parse numbered lines
            facts = []
            for line in response.split("\n"):
                line = line.strip()
                # Match lines starting with numbers: "1.", "1)", "1:"
                cleaned = re.sub(r'^[\d]+[.):\-]\s*', '', line).strip()
                if cleaned and len(cleaned) > 15:
                    facts.append(cleaned)

            return facts[:5]

        except Exception as e:
            log.warning(f"[Sifter] Ollama extraction failed: {e}")
            return self._extract_heuristic(query, page_text)

    def _extract_heuristic(self, query: str, page_text: str) -> List[str]:
        """
        Fallback: extract sentences that contain query keywords.
        Simple but effective when Ollama is unavailable.
        """
        keywords = [w.lower() for w in query.split() if len(w) > 3]

        # Split into sentences
        sentences = re.split(r'[.!?]+', page_text)
        scored = []

        for sent in sentences:
            sent = sent.strip()
            if len(sent) < 30 or len(sent) > 300:
                continue

            # Score by keyword matches
            score = sum(1 for kw in keywords if kw in sent.lower())
            if score > 0:
                scored.append((score, sent))

        # Top 5 by relevance
        scored.sort(key=lambda x: x[0], reverse=True)
        return [s + "." for _, s in scored[:5]]

    def get_learning_report(self) -> str:
        """Generate a summary of everything BRIO has learned from the web."""
        if not self.sift_history:
            return "I haven't explored the web yet. Send me on a quest!"

        total_pages = sum(r["pages_read"] for r in self.sift_history)
        total_facts = sum(r["facts_extracted"] for r in self.sift_history)
        total_engrams = sum(r["engrams_created"] for r in self.sift_history)
        queries = [r["query"] for r in self.sift_history]

        report = (
            f"📚 *Brio's Learning Report*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔍 Searches: {len(self.sift_history)}\n"
            f"📖 Pages read: {total_pages}\n"
            f"💡 Facts extracted: {total_facts}\n"
            f"🧠 Engrams crystallized: {total_engrams}\n"
            f"\nTopics explored:\n"
        )
        for q in queries[-10:]:
            report += f"  • {q}\n"

        return report


if __name__ == "__main__":
    # Mock system for testing
    class MockKnowledge:
        def learn(self, content, emotion, importance):
            print(f"  [Engram] {content[:80]}...")

    class MockSearch:
        def quick_search(self, query):
            from brio_search import SearchResult
            return [SearchResult(
                title="Test", url="https://example.com", snippet="test"
            )]
        def read_page(self, url, max_chars=3000):
            return "Python is a versatile programming language. It is widely used in AI and web development."

    class MockSystem:
        knowledge = MockKnowledge()
        search = MockSearch()
        mind = None

    ws = WebSifter(MockSystem())
    result = ws.search_and_ingest("Python programming")
    print(result)
