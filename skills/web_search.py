"""
ARVIS Web Search — Permanent Solution (Python 3.12+, No API Key)
Uses 4-layer fallback. At least one will always work on your PC.
"""

import requests
import json
import urllib.parse
import time
import urllib3
import warnings
from bs4 import BeautifulSoup

# Disable insecure request warnings globally to bypass Windows SSL certificate store issues
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings("ignore", category=urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings("ignore", category=RuntimeWarning, message="This package.*duckduckgo_search.*renamed")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

# ─────────────────────────────────────────────
# LAYER 0: googlesearch-python library
# ─────────────────────────────────────────────
def search_google(query, max_results=5):
    try:
        from googlesearch import search
        results = []
        urls = list(search(query, num_results=max_results))
        for url in urls:
            domain = url.split("//")[-1].split("/")[0].replace("www.", "")
            path_segments = [s for s in url.split("/")[3:] if s]
            title = f"Google: {domain}"
            if path_segments:
                title += f" - {path_segments[-1].replace('-', ' ').replace('_', ' ').split('.')[0].capitalize()}"
            results.append({
                "title": title,
                "url": url,
                "snippet": f"Web search link from Google search matching query '{query}'."
            })
        return results
    except Exception as e:
        print(f"  [Layer 0 Google failed]: {e}")
    return []

# ─────────────────────────────────────────────
# LAYER 1: duckduckgo_search library
# ─────────────────────────────────────────────
def search_ddgs(query, max_results=5):
    try:
        # Try the new package name 'ddgs' first
        from ddgs import DDGS
        with DDGS() as d:
            results = list(d.text(query, max_results=max_results))
            if results:
                return [{"title": r["title"], "url": r["href"],
                         "snippet": r["body"]} for r in results]
    except Exception as e_ddgs:
        # Secondary fallback: try legacy 'duckduckgo_search' package name
        try:
            from duckduckgo_search import DDGS
            with DDGS() as d:
                results = list(d.text(query, max_results=max_results))
                if results:
                    return [{"title": r["title"], "url": r["href"],
                             "snippet": r["body"]} for r in results]
        except Exception as e_legacy:
            # Only print failure if both fail
            print(f"  [Layer 1 DDGS failed]: {e_ddgs} (Legacy fallback failed: {e_legacy})")
            
    return []


# ─────────────────────────────────────────────
# LAYER 2: Wikipedia Search API (always free)
# No key. Works even when all search engines block.
# Best for factual/knowledge queries.
# ─────────────────────────────────────────────
def search_wikipedia(query, max_results=5):
    try:
        q = urllib.parse.quote(query)
        url = (f"https://en.wikipedia.org/w/api.php"
               f"?action=query&list=search&srsearch={q}"
               f"&format=json&srlimit={max_results}")
        # Added verify=False to bypass Windows SSL certificate store issues
        r = requests.get(url, headers=HEADERS, timeout=8, verify=False)
        data = r.json()
        items = data.get("query", {}).get("search", [])
        if items:
            results = []
            for item in items:
                snippet = BeautifulSoup(
                    item.get("snippet", ""), "html.parser"
                ).get_text()
                results.append({
                    "title": item["title"],
                    "url": f"https://en.wikipedia.org/wiki/{urllib.parse.quote(item['title'])}",
                    "snippet": snippet
                })
            return results
    except Exception as e:
        print(f"  [Layer 2 Wikipedia failed]: {e}")
    return []


# ─────────────────────────────────────────────
# LAYER 3: DuckDuckGo Instant Answer API
# Returns quick facts. Great for "what is X" queries.
# ─────────────────────────────────────────────
def search_ddg_instant(query):
    try:
        q = urllib.parse.quote(query)
        url = f"https://api.duckduckgo.com/?q={q}&format=json&no_html=1&skip_disambig=1"
        # Added verify=False to bypass Windows SSL certificate store issues
        r = requests.get(url, headers=HEADERS, timeout=8, verify=False)
        data = r.json()

        results = []

        # Abstract (main answer)
        if data.get("AbstractText"):
            results.append({
                "title": data.get("Heading", query),
                "url": data.get("AbstractURL", ""),
                "snippet": data["AbstractText"]
            })

        # Related topics
        for topic in data.get("RelatedTopics", [])[:4]:
            if isinstance(topic, dict) and topic.get("Text"):
                results.append({
                    "title": topic.get("Text", "")[:60],
                    "url": topic.get("FirstURL", ""),
                    "snippet": topic.get("Text", "")
                })

        return results if results else []
    except Exception as e:
        print(f"  [Layer 3 DDG Instant failed]: {e}")
    return []


# ─────────────────────────────────────────────
# LAYER 4: Open-Meteo for weather queries
# Handles weather and climate requests without any key.
# ─────────────────────────────────────────────
WMO_CODES = {
    0: ("Clear sky", "☀️"),
    1: ("Mainly clear", "🌤️"),
    2: ("Partly cloudy", "⛅"),
    3: ("Overcast", "☁️"),
    45: ("Fog", "🌫️"),
    48: ("Depositing rime fog", "🌫️"),
    51: ("Light drizzle", "🌦️"),
    53: ("Moderate drizzle", "🌦️"),
    55: ("Dense drizzle", "🌦️"),
    56: ("Light freezing drizzle", "🌧️"),
    57: ("Dense freezing drizzle", "🌧️"),
    61: ("Slight rain", "🌧️"),
    63: ("Moderate rain", "🌧️"),
    65: ("Heavy rain", "🌧️"),
    66: ("Light freezing rain", "🌧️"),
    67: ("Heavy freezing rain", "🌧️"),
    71: ("Slight snow fall", "❄️"),
    73: ("Moderate snow fall", "❄️"),
    75: ("Heavy snow fall", "❄️"),
    77: ("Snow grains", "❄️"),
    80: ("Slight rain showers", "🌦️"),
    81: ("Moderate rain showers", "🌦️"),
    82: ("Violent rain showers", "🌦️"),
    85: ("Slight snow showers", "❄️"),
    86: ("Heavy snow showers", "❄️"),
    95: ("Thunderstorm", "⛈️"),
    96: ("Thunderstorm with slight hail", "⛈️"),
    99: ("Thunderstorm with heavy hail", "⛈️"),
}

def search_weather(query):
    """Fetches detailed current weather conditions and 1-day forecast using Open-Meteo."""
    try:
        import re
        
        # Clean query to extract city/location name
        clean_city = query.lower()
        for word in ["weather", "temperature", "temp", "forecast", "current", "today", "tomorrow", 
                     "show", "me", "get", "fetch", "what", "is", "the", "in", "at", "for", 
                     "of", "please", "now", "report", "news", "how", "looks", "like", "rain",
                     "snow", "humidity", "wind", "speed", "conditions", "climate"]:
            clean_city = re.sub(r'\b' + word + r'\b', '', clean_city)
        clean_city = re.sub(r'\s+', ' ', clean_city).strip()
        
        city = clean_city if clean_city else "Surat"

        # Step 1: geocode city to get coordinates and location details
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(city)}&count=1"
        geo = requests.get(geo_url, timeout=8, verify=False).json()
        if not geo or "results" not in geo or not geo["results"]:
            return [{"title": f"Weather in {city.title()}", "url": "", "snippet": f"Could not retrieve weather: Location '{city}' not found."}]
        
        loc = geo["results"][0]
        lat, lon = loc["latitude"], loc["longitude"]
        loc_name = loc.get("name", city.title())
        country = loc.get("country", "")
        region = loc.get("admin1", "")
        
        full_location = f"{loc_name}"
        if region:
            full_location += f", {region}"
        if country:
            full_location += f" ({country})"

        # Step 2: fetch weather conditions (current + daily max/min)
        wx_url = (f"https://api.open-meteo.com/v1/forecast"
                  f"?latitude={lat}&longitude={lon}"
                  f"&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m,precipitation"
                  f"&daily=temperature_2m_max,temperature_2m_min"
                  f"&timezone=auto")
        wx = requests.get(wx_url, timeout=8, verify=False).json()
        
        curr = wx.get("current", {})
        temp = curr.get("temperature_2m", 0.0)
        feels_like = curr.get("apparent_temperature", temp)
        humidity = curr.get("relative_humidity_2m", 0)
        wind = curr.get("wind_speed_10m", 0.0)
        precip = curr.get("precipitation", 0.0)
        wmo_code = curr.get("weather_code", 0)
        
        # Translate weather code
        desc, emoji = WMO_CODES.get(wmo_code, ("Unknown conditions", "🌡️"))
        
        daily = wx.get("daily", {})
        temp_max = daily.get("temperature_2m_max", [temp])[0]
        temp_min = daily.get("temperature_2m_min", [temp])[0]

        snippet = (
            f"📍 Location: {full_location}\n"
            f"Condition: {emoji} {desc}\n"
            f"Temperature: {temp}°C (Feels like: {feels_like}°C)\n"
            f"Today's Range: Low {temp_min}°C / High {temp_max}°C\n"
            f"Humidity: {humidity}%\n"
            f"Wind Speed: {wind} km/h\n"
            f"Precipitation: {precip} mm"
        )
        
        return [{
            "title": f"Current Weather in {full_location}",
            "url": f"https://open-meteo.com/en/forecast?latitude={lat}&longitude={lon}",
            "snippet": snippet
        }]
    except Exception as e:
        print(f"  [Layer 4 Weather failed]: {e}")
    return []


# ─────────────────────────────────────────────
# MAIN FUNCTION — Smart router + fallback chain
# ─────────────────────────────────────────────
def web_search(query: str, max_results: int = 5) -> str:
    """
    Tries 4 layers. At least one works without any API key.
    Formats and returns the search results directly as a string.
    """
    print(f"[Web Search]: Searching for '{query}'...")

    # Weather shortcut
    if any(w in query.lower() for w in ["weather", "temperature", "temp", "forecast", "climate", "rain", "snow", "humidity", "wind speed", "precipitation"]):
        result = search_weather(query)
        if result:
            print("  [Web Search]: Weather API successful.")
            return format_for_ai(result, query)

    # Layer 0: Google Search
    result = search_google(query, max_results)
    if result:
        print(f"  [Web Search]: Google returned {len(result)} results.")
        return format_for_ai(result, query)

    # Layer 1: ddgs (duckduckgo_search library)
    result = search_ddgs(query, max_results)
    if result:
        print(f"  [Web Search]: DDGS returned {len(result)} results.")
        return format_for_ai(result, query)

    # Small delay to avoid rate limiting
    time.sleep(1)

    # Layer 2: Wikipedia
    result = search_wikipedia(query, max_results)
    if result:
        print(f"  [Web Search]: Wikipedia returned {len(result)} results.")
        return format_for_ai(result, query)

    # Layer 3: DDG Instant Answer
    result = search_ddg_instant(query)
    if result:
        print(f"  [Web Search]: DDG Instant returned {len(result)} results.")
        return format_for_ai(result, query)

    print("  [Web Search]: All layers failed. Returning empty.")
    return "No web search results available."


def format_for_ai(results: list[dict], query: str) -> str:
    """Formats search results into a clean string for the AI prompt."""
    if not results or results[0]["title"] == "No results found":
        return "No web search results available."

    lines = [f"Web search results for: '{query}'\n"]
    for i, r in enumerate(results[:4], 1):
        lines.append(f"[{i}] TITLE: {r['title']}")
        if r["url"]:
            lines.append(f"    URL: {r['url']}")
        lines.append(f"    CONTENT EXCERPT:\n    {r['snippet']}")
    return "\n".join(lines)


# ─────────────────────────────────────────────
# TEST
# ─────────────────────────────────────────────
if __name__ == "__main__":
    results = web_search("latest Python version 2025")
    print("\n=== RESULTS ===")
    print(results)
