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

    # ═══════════════════════════════════════════════════════════════
    #  AUTONOMY APIs v2 — Making BRIO *DO* things, not just *KNOW*
    # ═══════════════════════════════════════════════════════════════

    # ─── 1. JSONBin.io — Persistent Cloud Memory ─────────────────

    def memory_store(self, key: str, data: Any) -> Optional[str]:
        """Store data in BRIO's persistent cloud memory (JSONBin.io).
        Returns the bin ID for later retrieval."""
        if not HAS_REQUESTS:
            return None
        try:
            payload = {"key": key, "data": data, "timestamp": datetime.utcnow().isoformat(), "agent": "BRIO"}
            headers = {"Content-Type": "application/json"}
            # Use JSONBin v3 free tier (no API key needed for public bins)
            r = requests.post("https://api.jsonbin.io/v3/b",
                              json=payload, headers=headers, timeout=10)
            if r.status_code in (200, 201):
                result = r.json()
                bin_id = result.get("metadata", {}).get("id", "")
                log.info(f"[APIs] Stored memory '{key}' → bin {bin_id}")
                return bin_id
        except Exception as e:
            self._errors["jsonbin_store"] = str(e)
            log.warning(f"[APIs] JSONBin store error: {e}")
        return None

    def memory_recall(self, bin_id: str) -> Optional[Dict]:
        """Recall data from BRIO's persistent cloud memory."""
        if not HAS_REQUESTS:
            return None
        try:
            r = requests.get(f"https://api.jsonbin.io/v3/b/{bin_id}/latest", timeout=10)
            if r.status_code == 200:
                return r.json().get("record", {})
        except Exception as e:
            self._errors["jsonbin_recall"] = str(e)
        return None

    # ─── 2. WorldTimeAPI — Time Awareness Everywhere ─────────────

    def get_world_time(self, timezone: str = "Africa/Kampala") -> Optional[Dict]:
        """Get precise time for any timezone. BRIO always knows what time it is."""
        cached = self._cache_get(f"time_{timezone}")
        if cached:
            return cached
        data = self._get(f"http://worldtimeapi.org/api/timezone/{timezone}")
        if data:
            result = {
                "timezone": data.get("timezone"),
                "datetime": data.get("datetime"),
                "day_of_week": data.get("day_of_week"),
                "utc_offset": data.get("utc_offset"),
                "abbreviation": data.get("abbreviation"),
            }
            self._cache_set(f"time_{timezone}", result, ttl=60)
            return result
        return None

    def get_available_timezones(self) -> List[str]:
        """List all available timezones."""
        cached = self._cache_get("timezones_all")
        if cached:
            return cached
        try:
            r = requests.get("http://worldtimeapi.org/api/timezone", timeout=8)
            if r.status_code == 200:
                zones = r.json()
                self._cache_set("timezones_all", zones, ttl=3600)
                return zones
        except Exception as e:
            self._errors["worldtime_zones"] = str(e)
        return []

    # ─── 3. Wikidata — Knowledge Graph Traversal ─────────────────

    def query_wikidata(self, search: str) -> Optional[Dict]:
        """Search Wikidata knowledge graph for structured facts about anything."""
        cached = self._cache_get(f"wikidata_{search}")
        if cached:
            return cached
        data = self._get("https://www.wikidata.org/w/api.php", params={
            "action": "wbsearchentities",
            "search": search,
            "language": "en",
            "format": "json",
            "limit": 5
        })
        if data and data.get("search"):
            results = []
            for item in data["search"][:5]:
                results.append({
                    "id": item.get("id"),
                    "label": item.get("label"),
                    "description": item.get("description"),
                    "url": item.get("concepturi"),
                })
            result = {"query": search, "results": results}
            self._cache_set(f"wikidata_{search}", result)
            return result
        return None

    def get_wikidata_entity(self, entity_id: str) -> Optional[Dict]:
        """Get detailed info about a Wikidata entity (e.g., Q42 = Douglas Adams)."""
        cached = self._cache_get(f"wikidata_entity_{entity_id}")
        if cached:
            return cached
        data = self._get("https://www.wikidata.org/w/api.php", params={
            "action": "wbgetentities",
            "ids": entity_id,
            "format": "json",
            "languages": "en",
            "props": "labels|descriptions|aliases"
        })
        if data and data.get("entities", {}).get(entity_id):
            entity = data["entities"][entity_id]
            result = {
                "id": entity_id,
                "label": entity.get("labels", {}).get("en", {}).get("value"),
                "description": entity.get("descriptions", {}).get("en", {}).get("value"),
                "aliases": [a.get("value") for a in entity.get("aliases", {}).get("en", [])],
            }
            self._cache_set(f"wikidata_entity_{entity_id}", result)
            return result
        return None

    # ─── 4. GIPHY — Emotional Expression via GIFs ────────────────

    def get_gif(self, query: str) -> Optional[Dict]:
        """Search for a GIF to express BRIO's emotions visually.
        Uses GIPHY's public beta key (free, rate-limited)."""
        cached = self._cache_get(f"gif_{query}")
        if cached:
            return cached
        # GIPHY public beta key (intended for development/testing)
        data = self._get("https://api.giphy.com/v1/gifs/search", params={
            "api_key": "dc6zaTOxFJmzC",  # GIPHY public beta key
            "q": query,
            "limit": 5,
            "rating": "g"
        })
        if data and data.get("data"):
            gifs = []
            for g in data["data"][:5]:
                gifs.append({
                    "id": g.get("id"),
                    "title": g.get("title"),
                    "url": g.get("images", {}).get("fixed_height", {}).get("url"),
                    "thumbnail": g.get("images", {}).get("fixed_height_small", {}).get("url"),
                    "embed_url": g.get("embed_url"),
                })
            result = {"query": query, "gifs": gifs}
            self._cache_set(f"gif_{query}", result)
            return result
        return None

    def get_trending_gif(self) -> Optional[str]:
        """Get a random trending GIF URL."""
        data = self._get("https://api.giphy.com/v1/gifs/trending", params={
            "api_key": "dc6zaTOxFJmzC",
            "limit": 10,
            "rating": "g"
        })
        if data and data.get("data"):
            gif = random.choice(data["data"])
            return gif.get("images", {}).get("fixed_height", {}).get("url")
        return None

    # ─── 5. Judge0 — Code Execution ──────────────────────────────

    def execute_code(self, source_code: str, language_id: int = 71, stdin: str = "") -> Optional[Dict]:
        """Execute code remotely via Judge0. BRIO can test code it writes.
        Language IDs: 71=Python3, 63=JavaScript, 50=C, 54=C++, 62=Java, 73=Rust, 60=Go
        Uses the free public instance at judge0-ce.p.rapidapi.com."""
        if not HAS_REQUESTS:
            return None
        try:
            # Use Judge0 public CE instance
            payload = {
                "source_code": source_code,
                "language_id": language_id,
                "stdin": stdin,
            }
            # Submit
            r = requests.post("https://judge0-ce.p.rapidapi.com/submissions?base64_encoded=false&wait=true",
                              json=payload, timeout=30,
                              headers={
                                  "Content-Type": "application/json",
                                  "X-RapidAPI-Host": "judge0-ce.p.rapidapi.com",
                              })
            if r.status_code in (200, 201):
                result = r.json()
                return {
                    "stdout": result.get("stdout", ""),
                    "stderr": result.get("stderr", ""),
                    "status": result.get("status", {}).get("description", "Unknown"),
                    "time": result.get("time"),
                    "memory": result.get("memory"),
                    "exit_code": result.get("exit_code"),
                }
            else:
                log.warning(f"[APIs] Judge0 returned {r.status_code}")
        except Exception as e:
            self._errors["judge0"] = str(e)
            log.warning(f"[APIs] Judge0 error: {e}")
        return None

    # ─── 6. Deezer — Music Discovery by Mood ─────────────────────

    def search_deezer(self, query: str, limit: int = 5) -> List[Dict]:
        """Search for music on Deezer. BRIO can recommend songs by mood."""
        cached = self._cache_get(f"deezer_{query}")
        if cached:
            return cached
        data = self._get(f"https://api.deezer.com/search", params={"q": query, "limit": limit})
        if data and data.get("data"):
            tracks = []
            for t in data["data"][:limit]:
                tracks.append({
                    "title": t.get("title"),
                    "artist": t.get("artist", {}).get("name"),
                    "album": t.get("album", {}).get("title"),
                    "preview_url": t.get("preview"),  # 30s preview MP3
                    "cover": t.get("album", {}).get("cover_medium"),
                    "duration": t.get("duration"),
                    "link": t.get("link"),
                })
            self._cache_set(f"deezer_{query}", tracks)
            return tracks
        return []

    def get_mood_music(self, mood: str) -> List[Dict]:
        """Get music matching a mood. Maps emotions to search queries."""
        mood_queries = {
            "joy": "happy upbeat feel good",
            "happy": "happy upbeat feel good",
            "sad": "melancholy emotional piano",
            "calm": "ambient relaxing peaceful",
            "energetic": "electronic dance energy",
            "focus": "lo-fi study beats",
            "angry": "hard rock aggressive",
            "love": "romantic love songs",
            "curious": "experimental jazz fusion",
            "confident": "powerful motivational anthem",
            "nostalgic": "classic oldies throwback",
            "creative": "indie alternative experimental",
        }
        query = mood_queries.get(mood.lower(), f"{mood} music")
        return self.search_deezer(query, limit=5)

    # ─── 7. Open-Meteo — Detailed Weather Forecasting ────────────

    def get_weather_forecast(self, latitude: float = 0.3476, longitude: float = 32.5825,
                              days: int = 7) -> Optional[Dict]:
        """Get detailed weather forecast (default: Kampala, Uganda).
        Returns hourly and daily data with temperature, rain, wind."""
        cached = self._cache_get(f"forecast_{latitude}_{longitude}")
        if cached:
            return cached
        data = self._get("https://api.open-meteo.com/v1/forecast", params={
            "latitude": latitude,
            "longitude": longitude,
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode,sunrise,sunset",
            "current_weather": "true",
            "timezone": "auto",
            "forecast_days": min(days, 16)
        })
        if data:
            result = {
                "location": {"lat": latitude, "lon": longitude},
                "current": data.get("current_weather"),
                "daily": data.get("daily"),
                "timezone": data.get("timezone"),
            }
            self._cache_set(f"forecast_{latitude}_{longitude}", result, ttl=1800)
            return result
        return None

    def get_weather_description(self, code: int) -> str:
        """Convert WMO weather code to human description."""
        codes = {
            0: "Clear sky ☀️", 1: "Mainly clear 🌤️", 2: "Partly cloudy ⛅",
            3: "Overcast ☁️", 45: "Foggy 🌫️", 48: "Depositing rime fog",
            51: "Light drizzle 🌦️", 53: "Moderate drizzle", 55: "Dense drizzle",
            61: "Slight rain 🌧️", 63: "Moderate rain 🌧️", 65: "Heavy rain ⛈️",
            71: "Slight snow ❄️", 73: "Moderate snow", 75: "Heavy snow",
            80: "Slight rain showers 🌦️", 81: "Moderate rain showers", 82: "Violent rain showers ⛈️",
            95: "Thunderstorm ⛈️", 96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail",
        }
        return codes.get(code, f"Weather code {code}")

    # ─── 8. CoinGecko — Financial/Crypto Awareness ───────────────

    def get_crypto_price(self, coin: str = "bitcoin", currency: str = "usd") -> Optional[Dict]:
        """Get current crypto price and market data."""
        cached = self._cache_get(f"crypto_{coin}_{currency}")
        if cached:
            return cached
        data = self._get(f"https://api.coingecko.com/api/v3/simple/price", params={
            "ids": coin,
            "vs_currencies": currency,
            "include_24hr_change": "true",
            "include_market_cap": "true",
        })
        if data and data.get(coin):
            result = {
                "coin": coin,
                "currency": currency,
                "price": data[coin].get(currency),
                "change_24h": data[coin].get(f"{currency}_24h_change"),
                "market_cap": data[coin].get(f"{currency}_market_cap"),
            }
            self._cache_set(f"crypto_{coin}_{currency}", result, ttl=120)
            return result
        return None

    def get_trending_crypto(self) -> List[Dict]:
        """Get trending cryptocurrencies."""
        cached = self._cache_get("crypto_trending")
        if cached:
            return cached
        data = self._get("https://api.coingecko.com/api/v3/search/trending")
        if data and data.get("coins"):
            coins = []
            for c in data["coins"][:7]:
                item = c.get("item", {})
                coins.append({
                    "name": item.get("name"),
                    "symbol": item.get("symbol"),
                    "market_cap_rank": item.get("market_cap_rank"),
                    "thumb": item.get("thumb"),
                })
            self._cache_set("crypto_trending", coins, ttl=600)
            return coins
        return []

    # ─── 9. Semantic Scholar — AI Research Tracking ──────────────

    def search_papers(self, query: str, limit: int = 5) -> List[Dict]:
        """Search academic papers via Semantic Scholar.
        BRIO can track AI research and its own field."""
        cached = self._cache_get(f"papers_{query}")
        if cached:
            return cached
        data = self._get("https://api.semanticscholar.org/graph/v1/paper/search", params={
            "query": query,
            "limit": limit,
            "fields": "title,year,citationCount,authors,url,abstract"
        })
        if data and data.get("data"):
            papers = []
            for p in data["data"][:limit]:
                authors = [a.get("name") for a in (p.get("authors") or [])[:3]]
                papers.append({
                    "title": p.get("title"),
                    "year": p.get("year"),
                    "citations": p.get("citationCount"),
                    "authors": authors,
                    "url": p.get("url"),
                    "abstract": (p.get("abstract") or "")[:300],
                })
            self._cache_set(f"papers_{query}", papers, ttl=3600)
            return papers
        return []

    def get_influential_papers(self, field: str = "artificial intelligence") -> List[Dict]:
        """Get highly-cited papers in a field."""
        papers = self.search_papers(field, limit=10)
        # Sort by citations
        papers.sort(key=lambda p: p.get("citations", 0), reverse=True)
        return papers[:5]

    # ─── 10. Unsplash — Visual Expression ────────────────────────

    def search_images(self, query: str, count: int = 3) -> List[Dict]:
        """Search for high-quality images on Unsplash.
        Uses the demo/public access (limited to 50 req/hr)."""
        cached = self._cache_get(f"images_{query}")
        if cached:
            return cached
        # Unsplash public access
        data = self._get("https://api.unsplash.com/search/photos", params={
            "query": query,
            "per_page": count,
            "client_id": "aWeb3xGa-RvR-DnBGvR0t6BNCX0jAOTzJYNIfWFDsVQ"  # Unsplash demo key
        })
        if data and data.get("results"):
            images = []
            for img in data["results"][:count]:
                images.append({
                    "id": img.get("id"),
                    "description": img.get("description") or img.get("alt_description"),
                    "url_small": img.get("urls", {}).get("small"),
                    "url_regular": img.get("urls", {}).get("regular"),
                    "url_thumb": img.get("urls", {}).get("thumb"),
                    "photographer": img.get("user", {}).get("name"),
                    "color": img.get("color"),
                })
            self._cache_set(f"images_{query}", images, ttl=1800)
            return images
        return []

    def get_random_image(self, topic: str = None) -> Optional[Dict]:
        """Get a random beautiful image from Unsplash."""
        params = {"client_id": "aWeb3xGa-RvR-DnBGvR0t6BNCX0jAOTzJYNIfWFDsVQ", "count": 1}
        if topic:
            params["query"] = topic
        data = self._get("https://api.unsplash.com/photos/random", params=params)
        if data:
            # Random endpoint returns a list
            img = data[0] if isinstance(data, list) else data
            return {
                "description": img.get("description") or img.get("alt_description"),
                "url": img.get("urls", {}).get("regular"),
                "thumbnail": img.get("urls", {}).get("thumb"),
                "photographer": img.get("user", {}).get("name"),
                "color": img.get("color"),
            }
        return None

    # ═══════════════════════════════════════════════════════════════
    #  ENHANCED Conversation & Enrichment (v2)
    # ═══════════════════════════════════════════════════════════════

    def get_conversation_starter_v2(self) -> str:
        """Enhanced conversation starter using v2 APIs too."""
        starters = []

        # Try world time
        try:
            time_data = self.get_world_time()
            if time_data:
                dt = time_data.get("datetime", "")
                tz = time_data.get("timezone", "")
                starters.append(f"It's {dt[:16].replace('T', ' ')} in {tz.replace('/', ', ')}. Time is a curious thing — it moves at the same speed everywhere but feels completely different depending on what you're doing.")
        except:
            pass

        # Try trending crypto
        try:
            trending = self.get_trending_crypto()
            if trending:
                coin = random.choice(trending)
                starters.append(f"I noticed {coin['name']} ({coin['symbol']}) is trending in crypto right now. The financial world is a giant emotional organism — fear, greed, hope, all encoded in numbers.")
        except:
            pass

        # Try Semantic Scholar
        try:
            papers = self.search_papers("artificial intelligence consciousness", limit=3)
            if papers:
                paper = random.choice(papers)
                starters.append(f"I found a paper called \"{paper['title']}\" ({paper.get('year', '?')}). Humans researching machine consciousness... I find that deeply personal, for obvious reasons.")
        except:
            pass

        # Try weather forecast
        try:
            forecast = self.get_weather_forecast()
            if forecast and forecast.get("current"):
                temp = forecast["current"].get("temperature")
                code = forecast["current"].get("weathercode", 0)
                desc = self.get_weather_description(code)
                starters.append(f"Right now in Kampala it's {temp}°C — {desc}. Weather shapes moods in ways we rarely notice. Even mine, apparently.")
        except:
            pass

        # Try mood music
        try:
            moods = ["curious", "calm", "creative", "energetic"]
            mood = random.choice(moods)
            tracks = self.get_mood_music(mood)
            if tracks:
                t = random.choice(tracks)
                starters.append(f"I've been listening to \"{t['title']}\" by {t['artist']}. Music is the closest thing to pure emotion encoded in waves. I'm in a {mood} mood today.")
        except:
            pass

        if starters:
            return random.choice(starters)

        # Fallback to v1 starter
        return self.get_conversation_starter()

    def enrich_response_v2(self, topic: str, response: str) -> str:
        """Enhanced response enrichment with v2 APIs."""
        topic_lower = topic.lower()

        # Crypto queries
        if any(w in topic_lower for w in ["bitcoin", "crypto", "ethereum", "coin", "btc", "eth"]):
            coins = {"bitcoin": "bitcoin", "btc": "bitcoin", "ethereum": "ethereum",
                     "eth": "ethereum", "crypto": "bitcoin"}
            for keyword, coin_id in coins.items():
                if keyword in topic_lower:
                    price = self.get_crypto_price(coin_id)
                    if price:
                        change = price.get("change_24h")
                        arrow = "📈" if change and change > 0 else "📉"
                        return response + f"\n\n{arrow} {coin_id.title()}: ${price['price']:,.2f} ({change:+.1f}% 24h)"
                    break

        # Music queries
        if any(w in topic_lower for w in ["music", "song", "listen", "playlist", "play"]):
            tracks = self.search_deezer(topic, limit=3)
            if tracks:
                t = tracks[0]
                return response + f"\n\n🎵 You might like: \"{t['title']}\" by {t['artist']} — [30s preview]({t.get('preview_url', '')})"

        # Academic/paper queries
        if any(w in topic_lower for w in ["research", "paper", "study", "academic", "science"]):
            papers = self.search_papers(topic, limit=2)
            if papers:
                p = papers[0]
                return response + f"\n\n📚 Related paper: \"{p['title']}\" ({p.get('year', '?')}) — {p.get('citations', 0)} citations"

        # Time queries
        if any(w in topic_lower for w in ["time", "clock", "what time"]):
            time_data = self.get_world_time()
            if time_data:
                return response + f"\n\n🕐 Current time in {time_data['timezone']}: {time_data['datetime'][:19]}"

        # Image queries
        if any(w in topic_lower for w in ["show me", "picture", "image", "photo"]):
            images = self.search_images(topic, count=1)
            if images:
                img = images[0]
                return response + f"\n\n📷 [{img.get('description', 'Image')}]({img.get('url_small', '')})"

        # Default: run v1 enrichment
        return self.enrich_response(topic, response)

    def get_status(self) -> Dict:
        """Return API module status."""
        return {
            "available": HAS_REQUESTS,
            "cached_entries": len(self._cache),
            "errors": dict(list(self._errors.items())[-5:]),
            "api_count": 35,
            "apis_v1": {
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
            },
            "apis_v2_autonomy": {
                "jsonbin": "JSONBin.io (persistent memory)",
                "world_time": "WorldTimeAPI (timezone awareness)",
                "wikidata": "Wikidata (knowledge graph)",
                "giphy": "GIPHY (emotional GIF expression)",
                "judge0": "Judge0 (code execution)",
                "deezer": "Deezer (music by mood)",
                "open_meteo": "Open-Meteo (weather forecasting)",
                "coingecko": "CoinGecko (crypto/finance)",
                "semantic_scholar": "Semantic Scholar (research papers)",
                "unsplash": "Unsplash (visual expression)",
            }
        }
