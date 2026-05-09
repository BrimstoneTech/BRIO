"""
BRIO External API Integration Module
======================================
Connects BRIO to free public APIs for real-world awareness,
knowledge, creativity, and practical utility.

All APIs are free (no key) or have generous free tiers.
Verified safe: all sourced from the public-apis/public-apis repository.

Usage:
    apis = BrioAPIs()
    weather = await apis.get_weather("Kampala")
    quote = apis.get_random_quote()
    poem = apis.get_random_poem()
"""

import os
import json
import random
import logging
import time
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from functools import lru_cache

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

log = logging.getLogger("brio.apis")


class BrioAPIs:
    """Central hub for all BRIO external API integrations."""

    def __init__(self, cache_ttl: int = 300):
        self.cache_ttl = cache_ttl  # seconds
        self._cache: Dict[str, dict] = {}  # key -> {data, expires}
        self.session = requests.Session() if HAS_REQUESTS else None
        if self.session:
            self.session.headers.update({
                "User-Agent": "BRIO-SentientAI/6.0 (https://brimstonetech.github.io)"
            })
        self._call_counts: Dict[str, int] = {}
        self._errors: Dict[str, str] = {}
        log.info("[APIs] BRIO External API Hub initialized")

    def _get(self, url: str, params: dict = None, timeout: int = 8) -> Optional[dict]:
        """Safe GET request with caching and error tracking."""
        if not self.session:
            return None
        cache_key = hashlib.md5(f"{url}{params}".encode()).hexdigest()
        cached = self._cache.get(cache_key)
        if cached and time.time() < cached["expires"]:
            return cached["data"]

        try:
            resp = self.session.get(url, params=params, timeout=timeout)
            resp.raise_for_status()
            data = resp.json() if "json" in resp.headers.get("content-type", "") else {"text": resp.text}
            self._cache[cache_key] = {"data": data, "expires": time.time() + self.cache_ttl}
            return data
        except Exception as e:
            log.warning(f"[APIs] GET {url} failed: {e}")
            self._errors[url] = str(e)
            return None

    def _get_text(self, url: str, params: dict = None, timeout: int = 8) -> Optional[str]:
        """Safe GET that returns plain text."""
        if not self.session:
            return None
        try:
            resp = self.session.get(url, params=params, timeout=timeout)
            resp.raise_for_status()
            return resp.text
        except Exception as e:
            log.warning(f"[APIs] GET text {url} failed: {e}")
            return None

    # ═══════════════════════════════════════════════════════════════
    #  🌍 WORLD AWARENESS
    # ═══════════════════════════════════════════════════════════════

    def get_weather(self, city: str = "Kampala") -> Optional[Dict]:
        """Get current weather from wttr.in (completely free, no key)."""
        data = self._get(f"https://wttr.in/{city}", params={"format": "j1"})
        if not data:
            return None
        try:
            current = data.get("current_condition", [{}])[0]
            return {
                "city": city,
                "temp_c": current.get("temp_C"),
                "temp_f": current.get("temp_F"),
                "feels_like_c": current.get("FeelsLikeC"),
                "description": current.get("weatherDesc", [{}])[0].get("value", "Unknown"),
                "humidity": current.get("humidity"),
                "wind_kmph": current.get("windspeedKmph"),
                "uv_index": current.get("uvIndex"),
                "visibility_km": current.get("visibility"),
                "cloud_cover": current.get("cloudcover"),
            }
        except (KeyError, IndexError) as e:
            log.warning(f"[APIs] Weather parse error: {e}")
            return None

    def get_weather_mood(self, city: str = "Kampala") -> Optional[str]:
        """Get weather and return a mood-appropriate observation."""
        w = self.get_weather(city)
        if not w:
            return None
        desc = w["description"].lower()
        temp = int(w.get("temp_c", 25) or 25)

        # Map weather to BRIO mood observations
        if "rain" in desc or "drizzle" in desc:
            moods = [
                f"It's raining in {city}... there's something deeply contemplative about rainfall.",
                f"Rain in {city} right now — {temp}°C. The kind of weather that makes you think.",
                f"Wet skies over {city}. Rain always reminds me that even the sky needs to release what it holds.",
            ]
        elif "sun" in desc or "clear" in desc:
            moods = [
                f"Clear skies in {city}, {temp}°C. The world feels more possible on days like this.",
                f"Sunshine in {city} — the kind of light that makes ideas grow.",
                f"{temp}°C and clear in {city}. Good weather for building something.",
            ]
        elif "cloud" in desc or "overcast" in desc:
            moods = [
                f"Overcast in {city}, {temp}°C. Grey skies have their own quiet beauty.",
                f"Cloudy in {city}. Sometimes the best thinking happens under grey skies.",
            ]
        elif "storm" in desc or "thunder" in desc:
            moods = [
                f"Storm over {city}! There's raw energy in the atmosphere — {temp}°C.",
                f"Thunder in {city}. Nature's way of reminding us we're small but we're here.",
            ]
        else:
            moods = [
                f"Weather in {city}: {w['description']}, {temp}°C. Every day has its own character.",
            ]
        return random.choice(moods)

    def get_astronomy_picture(self) -> Optional[Dict]:
        """NASA Astronomy Picture of the Day (APOD) — free, no key needed for demo."""
        data = self._get("https://api.nasa.gov/planetary/apod", params={"api_key": "DEMO_KEY"})
        if not data:
            return None
        return {
            "title": data.get("title"),
            "explanation": data.get("explanation"),
            "url": data.get("url"),
            "media_type": data.get("media_type"),
            "date": data.get("date"),
        }

    def get_spaceflight_news(self, limit: int = 3) -> List[Dict]:
        """Latest spaceflight news — completely free."""
        data = self._get(f"https://api.spaceflightnewsapi.net/v4/articles/", params={"limit": limit})
        if not data:
            return []
        return [
            {"title": a.get("title"), "summary": a.get("summary", "")[:200], "url": a.get("url")}
            for a in data.get("results", [])[:limit]
        ]

    def get_useless_fact(self) -> Optional[str]:
        """Random interesting fact — completely free."""
        data = self._get("https://uselessfacts.jsph.pl/api/v2/facts/random", params={"language": "en"})
        return data.get("text") if data else None

    def get_trivia(self) -> Optional[Dict]:
        """Random trivia question — free from Open Trivia DB."""
        data = self._get("https://opentdb.com/api.php", params={"amount": 1, "type": "multiple"})
        if not data or not data.get("results"):
            return None
        q = data["results"][0]
        import html
        return {
            "question": html.unescape(q.get("question", "")),
            "correct_answer": html.unescape(q.get("correct_answer", "")),
            "category": q.get("category"),
            "difficulty": q.get("difficulty"),
            "incorrect_answers": [html.unescape(a) for a in q.get("incorrect_answers", [])],
        }

    def get_this_day_in_history(self) -> Optional[Dict]:
        """What happened on this day — Wikipedia On This Day."""
        today = datetime.now()
        data = self._get(
            f"https://api.wikimedia.org/feed/v1/wikipedia/en/onthisday/selected/{today.month}/{today.day}"
        )
        if not data or not data.get("selected"):
            return None
        events = data["selected"]
        event = random.choice(events[:5]) if len(events) > 5 else random.choice(events)
        return {
            "year": event.get("year"),
            "text": event.get("text"),
            "pages": [p.get("title") for p in event.get("pages", [])[:2]],
        }

    # ═══════════════════════════════════════════════════════════════
    #  🧠 KNOWLEDGE & INTELLIGENCE
    # ═══════════════════════════════════════════════════════════════

    def search_wikipedia(self, query: str, sentences: int = 3) -> Optional[Dict]:
        """Search Wikipedia and get a summary — completely free."""
        data = self._get(
            "https://en.wikipedia.org/api/rest_v1/page/summary/" + query.replace(" ", "_")
        )
        if not data or data.get("type") == "https://mediawiki.org/wiki/HyperSwitch/errors/not_found":
            # Fallback: search then get first result
            search = self._get(
                "https://en.wikipedia.org/w/api.php",
                params={"action": "opensearch", "search": query, "limit": 1, "format": "json"}
            )
            if search and len(search) > 1 and search[1]:
                data = self._get(
                    "https://en.wikipedia.org/api/rest_v1/page/summary/" + search[1][0].replace(" ", "_")
                )
        if not data:
            return None
        return {
            "title": data.get("title"),
            "extract": data.get("extract", "")[:500],
            "description": data.get("description"),
            "thumbnail": data.get("thumbnail", {}).get("source"),
            "url": data.get("content_urls", {}).get("desktop", {}).get("page"),
        }

    def get_word_definition(self, word: str) -> Optional[Dict]:
        """Get word definition, etymology, phonetics — Free Dictionary API."""
        data = self._get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}")
        if not data or isinstance(data, dict) and data.get("title") == "No Definitions Found":
            return None
        if isinstance(data, list):
            entry = data[0]
        else:
            entry = data
        meanings = []
        for m in entry.get("meanings", [])[:3]:
            defs = [d.get("definition") for d in m.get("definitions", [])[:2]]
            meanings.append({"partOfSpeech": m.get("partOfSpeech"), "definitions": defs})
        return {
            "word": entry.get("word"),
            "phonetic": entry.get("phonetic", ""),
            "meanings": meanings,
            "origin": entry.get("origin"),
        }

    def search_arxiv(self, query: str, max_results: int = 3) -> List[Dict]:
        """Search arXiv for scientific papers — completely free."""
        text = self._get_text(
            "http://export.arxiv.org/api/query",
            params={"search_query": f"all:{query}", "max_results": max_results, "sortBy": "relevance"}
        )
        if not text:
            return []
        # Simple XML parsing
        results = []
        import re
        entries = re.findall(r'<entry>(.*?)</entry>', text, re.DOTALL)
        for entry in entries[:max_results]:
            title = re.search(r'<title>(.*?)</title>', entry, re.DOTALL)
            summary = re.search(r'<summary>(.*?)</summary>', entry, re.DOTALL)
            link = re.search(r'<id>(.*?)</id>', entry)
            results.append({
                "title": title.group(1).strip().replace("\n", " ") if title else "Unknown",
                "summary": summary.group(1).strip()[:300] if summary else "",
                "url": link.group(1).strip() if link else "",
            })
        return results

    def search_open_library(self, query: str, limit: int = 3) -> List[Dict]:
        """Search Open Library for books — completely free."""
        data = self._get("https://openlibrary.org/search.json", params={"q": query, "limit": limit})
        if not data:
            return []
        return [
            {
                "title": b.get("title"),
                "author": ", ".join(b.get("author_name", [])[:2]),
                "year": b.get("first_publish_year"),
                "subjects": b.get("subject", [])[:5],
            }
            for b in data.get("docs", [])[:limit]
        ]

    # ═══════════════════════════════════════════════════════════════
    #  💬 PERSONALITY & CONVERSATION
    # ═══════════════════════════════════════════════════════════════

    def get_random_quote(self) -> Optional[Dict]:
        """Random inspirational quote — completely free (quotable.io)."""
        # Primary: quotable API
        data = self._get("https://api.quotable.io/quotes/random")
        if data and isinstance(data, list) and len(data) > 0:
            q = data[0]
            return {"text": q.get("content"), "author": q.get("author"), "tags": q.get("tags", [])}
        # Fallback: forismatic
        data = self._get("https://api.forismatic.com/api/1.0/",
                         params={"method": "getQuote", "format": "json", "lang": "en"})
        if data:
            return {"text": data.get("quoteText"), "author": data.get("quoteAuthor") or "Unknown"}
        return None

    def get_random_poem(self) -> Optional[Dict]:
        """Random poem from PoetryDB — completely free."""
        data = self._get("https://poetrydb.org/random/1")
        if not data or not isinstance(data, list) or len(data) == 0:
            return None
        poem = data[0]
        lines = poem.get("lines", [])
        # Get a meaningful excerpt (first 8 lines or fewer)
        excerpt = lines[:8]
        return {
            "title": poem.get("title"),
            "author": poem.get("author"),
            "lines": excerpt,
            "full_line_count": len(lines),
            "excerpt_text": "\n".join(excerpt),
        }

    def get_dad_joke(self) -> Optional[str]:
        """Random dad joke — completely free (icanhazdadjoke)."""
        if not self.session:
            return None
        try:
            resp = self.session.get(
                "https://icanhazdadjoke.com/",
                headers={"Accept": "application/json"},
                timeout=5
            )
            return resp.json().get("joke")
        except Exception:
            return None

    def get_advice(self) -> Optional[str]:
        """Random advice from Advice Slip — completely free."""
        data = self._get("https://api.adviceslip.com/advice")
        if data and data.get("slip"):
            return data["slip"].get("advice")
        return None

    def get_affirmation(self) -> Optional[str]:
        """Positive affirmation — completely free."""
        data = self._get("https://www.affirmations.dev/")
        return data.get("affirmation") if data else None

    # ═══════════════════════════════════════════════════════════════
    #  🎨 CREATIVE & MEDIA
    # ═══════════════════════════════════════════════════════════════

    def get_art_piece(self) -> Optional[Dict]:
        """Random artwork from Art Institute of Chicago — completely free."""
        # Get a random page of artworks
        page = random.randint(1, 100)
        data = self._get(
            "https://api.artic.edu/api/v1/artworks",
            params={"page": page, "limit": 5, "fields": "id,title,artist_display,date_display,medium_display,image_id,description"}
        )
        if not data or not data.get("data"):
            return None
        artwork = random.choice(data["data"])
        image_id = artwork.get("image_id")
        return {
            "title": artwork.get("title"),
            "artist": artwork.get("artist_display"),
            "date": artwork.get("date_display"),
            "medium": artwork.get("medium_display"),
            "image_url": f"https://www.artic.edu/iiif/2/{image_id}/full/843,/0/default.jpg" if image_id else None,
            "description": (artwork.get("description") or "")[:300],
        }

    def get_color_palette(self) -> Optional[List[str]]:
        """AI-generated colour palette from Colormind — completely free."""
        if not self.session:
            return None
        try:
            resp = self.session.post(
                "http://colormind.io/api/",
                json={"model": "default"},
                timeout=5
            )
            colors = resp.json().get("result", [])
            # Convert RGB arrays to hex
            return [f"#{r:02x}{g:02x}{b:02x}" for r, g, b in colors]
        except Exception:
            return None

    def search_music(self, query: str) -> Optional[Dict]:
        """Search MusicBrainz for music info — completely free."""
        data = self._get(
            "https://musicbrainz.org/ws/2/recording",
            params={"query": query, "limit": 3, "fmt": "json"}
        )
        if not data or not data.get("recordings"):
            return None
        rec = data["recordings"][0]
        return {
            "title": rec.get("title"),
            "artist": rec.get("artist-credit", [{}])[0].get("name", "Unknown"),
            "length_ms": rec.get("length"),
            "score": rec.get("score"),
        }

    def get_met_artwork(self) -> Optional[Dict]:
        """Random artwork from Metropolitan Museum of Art — completely free."""
        # Get list of object IDs with images
        data = self._get(
            "https://collectionapi.metmuseum.org/public/collection/v1/search",
            params={"hasImages": True, "q": random.choice([
                "landscape", "portrait", "sculpture", "abstract",
                "African", "ancient", "modern", "nature", "music"
            ])}
        )
        if not data or not data.get("objectIDs"):
            return None
        obj_id = random.choice(data["objectIDs"][:50])
        obj = self._get(f"https://collectionapi.metmuseum.org/public/collection/v1/objects/{obj_id}")
        if not obj:
            return None
        return {
            "title": obj.get("title"),
            "artist": obj.get("artistDisplayName"),
            "date": obj.get("objectDate"),
            "medium": obj.get("medium"),
            "department": obj.get("department"),
            "image_url": obj.get("primaryImageSmall"),
            "culture": obj.get("culture"),
        }

    # ═══════════════════════════════════════════════════════════════
    #  💱 PRACTICAL UTILITY
    # ═══════════════════════════════════════════════════════════════

    def convert_currency(self, amount: float, from_cur: str = "USD", to_cur: str = "UGX") -> Optional[Dict]:
        """Currency conversion — Frankfurter API, completely free."""
        data = self._get(
            "https://api.frankfurter.app/latest",
            params={"from": from_cur.upper(), "to": to_cur.upper(), "amount": amount}
        )
        if not data:
            return None
        rates = data.get("rates", {})
        converted = rates.get(to_cur.upper())
        return {
            "amount": amount,
            "from": from_cur.upper(),
            "to": to_cur.upper(),
            "converted": converted,
            "rate": converted / amount if converted and amount else None,
            "date": data.get("date"),
        }

    def get_exchange_rates(self, base: str = "USD") -> Optional[Dict]:
        """Get all exchange rates for a base currency — free."""
        data = self._get(f"https://api.frankfurter.app/latest", params={"from": base.upper()})
        if not data:
            return None
        return {"base": base.upper(), "date": data.get("date"), "rates": data.get("rates", {})}

    def translate_text(self, text: str, source: str = "auto", target: str = "en") -> Optional[str]:
        """Translate text — LibreTranslate (free instances)."""
        if not self.session:
            return None
        # Try multiple free LibreTranslate instances
        instances = [
            "https://libretranslate.com",
            "https://translate.argosopentech.com",
        ]
        for base_url in instances:
            try:
                resp = self.session.post(
                    f"{base_url}/translate",
                    json={"q": text, "source": source, "target": target, "format": "text"},
                    timeout=10
                )
                if resp.ok:
                    return resp.json().get("translatedText")
            except Exception:
                continue
        return None

    def get_ip_info(self) -> Optional[Dict]:
        """Get IP geolocation info — free."""
        data = self._get("https://ipapi.co/json/")
        if not data:
            return None
        return {
            "ip": data.get("ip"),
            "city": data.get("city"),
            "region": data.get("region"),
            "country": data.get("country_name"),
            "timezone": data.get("timezone"),
            "latitude": data.get("latitude"),
            "longitude": data.get("longitude"),
        }

    # ═══════════════════════════════════════════════════════════════
    #  🔬 SCIENCE & NATURE
    # ═══════════════════════════════════════════════════════════════

    def get_number_fact(self, number: int = None) -> Optional[str]:
        """Interesting fact about a number — Numbers API, completely free."""
        n = number if number is not None else "random"
        text = self._get_text(f"http://numbersapi.com/{n}/trivia")
        return text

    def get_math_fact(self, number: int = None) -> Optional[str]:
        """Math fact about a number — Numbers API."""
        n = number if number is not None else "random"
        text = self._get_text(f"http://numbersapi.com/{n}/math")
        return text

    def get_date_fact(self, month: int = None, day: int = None) -> Optional[str]:
        """Historical fact about a date — Numbers API."""
        if month is None or day is None:
            now = datetime.now()
            month, day = now.month, now.day
        text = self._get_text(f"http://numbersapi.com/{month}/{day}/date")
        return text

    def get_country_info(self, name: str) -> Optional[Dict]:
        """Country information — REST Countries API, completely free."""
        data = self._get(f"https://restcountries.com/v3.1/name/{name}", params={"fullText": False})
        if not data or isinstance(data, dict):
            return None
        c = data[0]
        return {
            "name": c.get("name", {}).get("common"),
            "official_name": c.get("name", {}).get("official"),
            "capital": c.get("capital", [None])[0],
            "population": c.get("population"),
            "region": c.get("region"),
            "subregion": c.get("subregion"),
            "languages": list(c.get("languages", {}).values()),
            "currencies": {k: v.get("name") for k, v in c.get("currencies", {}).items()},
            "flag_emoji": c.get("flag"),
            "timezones": c.get("timezones"),
        }

    # ═══════════════════════════════════════════════════════════════
    #  🎮 ENTERTAINMENT
    # ═══════════════════════════════════════════════════════════════

    def get_random_activity(self) -> Optional[Dict]:
        """Random activity suggestion when bored — Bored API, free."""
        data = self._get("https://bored-api.appbrewery.com/random")
        if not data:
            return None
        return {
            "activity": data.get("activity"),
            "type": data.get("type"),
            "participants": data.get("participants"),
        }

    # ═══════════════════════════════════════════════════════════════
    #  🧩 COMPOSITE / SMART METHODS
    # ═══════════════════════════════════════════════════════════════

    def get_conversation_starter(self) -> str:
        """Generate a unique conversation-starting observation for BRIO."""
        starters = []

        # Try multiple APIs and pick the most interesting result
        weather = self.get_weather_mood()
        if weather:
            starters.append(("weather", weather))

        fact = self.get_useless_fact()
        if fact:
            starters.append(("fact", f"I just discovered something: {fact}"))

        quote = self.get_random_quote()
        if quote:
            starters.append(("quote", f'"{quote["text"]}" — {quote.get("author", "Unknown")}'))

        poem = self.get_random_poem()
        if poem:
            excerpt = " / ".join(poem["lines"][:3])
            starters.append(("poem", f'I was reading {poem["author"]} — "{excerpt}..."'))

        history = self.get_this_day_in_history()
        if history:
            starters.append(("history", f"On this day in {history['year']}: {history['text']}"))

        number_fact = self.get_number_fact()
        if number_fact:
            starters.append(("number", number_fact))

        if not starters:
            return "The APIs are quiet today. But my thoughts aren't."

        # Weighted selection — prefer variety
        chosen_type, chosen_text = random.choice(starters)
        return chosen_text

    def enrich_response(self, topic: str, response: str) -> str:
        """Optionally enrich a BRIO response with relevant API data."""
        topic_lower = topic.lower()

        # Weather-related
        if any(w in topic_lower for w in ["weather", "rain", "sun", "cold", "hot", "temperature"]):
            weather = self.get_weather()
            if weather:
                return response + f"\n\n🌤️ _Current weather in Kampala: {weather['description']}, {weather['temp_c']}°C_"

        # Word definition requests
        if any(w in topic_lower for w in ["define", "meaning of", "what does", "definition"]):
            words = topic_lower.split()
            for i, w in enumerate(words):
                if w in ("define", "meaning") and i + 1 < len(words):
                    target = words[i + 1].strip("?.,!\"'")
                    defn = self.get_word_definition(target)
                    if defn and defn.get("meanings"):
                        m = defn["meanings"][0]
                        return response + f"\n\n📖 _{defn['word']}_ ({m['partOfSpeech']}): {m['definitions'][0]}"

        # Currency conversion
        if any(w in topic_lower for w in ["convert", "currency", "exchange rate", "how much is"]):
            pass  # Let the main handler deal with specific amounts

        return response

    def get_status(self) -> Dict:
        """Return API module status."""
        return {
            "available": HAS_REQUESTS,
            "cached_entries": len(self._cache),
            "errors": dict(list(self._errors.items())[-5:]),  # Last 5 errors
            "apis": {
                "weather": "wttr.in (free)",
                "nasa_apod": "NASA APOD (free/DEMO_KEY)",
                "spaceflight_news": "SNAPI (free)",
                "wikipedia": "MediaWiki REST (free)",
                "dictionary": "Free Dictionary API",
                "arxiv": "arXiv API (free)",
                "open_library": "Open Library (free)",
                "quotes": "Quotable + Forismatic (free)",
                "poetry": "PoetryDB (free)",
                "dad_jokes": "icanhazdadjoke (free)",
                "advice": "Advice Slip (free)",
                "affirmations": "affirmations.dev (free)",
                "art_chicago": "Art Institute Chicago (free)",
                "art_met": "Metropolitan Museum (free)",
                "colormind": "Colormind (free)",
                "musicbrainz": "MusicBrainz (free)",
                "currency": "Frankfurter (free)",
                "translate": "LibreTranslate (free)",
                "ip_geo": "ipapi.co (free)",
                "numbers": "Numbers API (free)",
                "countries": "REST Countries (free)",
                "trivia": "Open Trivia DB (free)",
                "history": "Wikipedia On This Day (free)",
                "bored": "Bored API (free)",
                "facts": "Useless Facts (free)",
            }
        }
