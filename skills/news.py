"""
ARVIS News Skill — Live headlines from Google News RSS (No API key needed)
Categories: tech, world, business, sports, health, science, entertainment
Also supports topic search: "news about cricket", "AI news"
"""

import urllib.parse
import urllib3
import warnings

# Suppress SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings("ignore", category=urllib3.exceptions.InsecureRequestWarning)

try:
    import requests
    from bs4 import BeautifulSoup
    _DEPS_OK = True
except ImportError:
    _DEPS_OK = False

# ── Google News RSS category URLs (no API key, always free) ──────────────────
CATEGORY_URLS = {
    "tech":          "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGRqTVhZU0FtVnVHZ0pWVXlnQVAB",
    "technology":    "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGRqTVhZU0FtVnVHZ0pWVXlnQVAB",
    "world":         "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGRqTVhZU0FtVnVHZ0pWVXlnQVAB?hl=en-IN&gl=IN&ceid=IN:en",
    "international": "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGRqTVhZU0FtVnVHZ0pWVXlnQVAB",
    "business":      "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGd5TlRZU0FtVnVHZ0pWVXlnQVAB",
    "finance":       "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGd5TlRZU0FtVnVHZ0pWVXlnQVAB",
    "sports":        "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNR1p1ZEdvU0FtVnVHZ0pWVXlnQVAB",
    "health":        "https://news.google.com/rss/topics/CAAqIQgKIhtDQkFTRGdvSUwyMHZNR3QwTlRFU0FtVnVLQUFQAQ",
    "science":       "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNR1p0Y0RvU0FtVnVHZ0pWVXlnQVAB",
    "entertainment": "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNREpxYW5RU0FtVnVHZ0pWVXlnQVAB",
    "india":         "https://news.google.com/rss/headlines/section/geo/IN?hl=en-IN&gl=IN&ceid=IN:en",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def _parse_rss(xml_text: str, max_items: int = 6) -> list[dict]:
    """Parse Google News RSS XML and return list of {title, source, link}."""
    try:
        soup = BeautifulSoup(xml_text, "xml")
        items = soup.find_all("item")[:max_items]
        results = []
        for item in items:
            title  = item.find("title").get_text(strip=True)  if item.find("title")  else "No title"
            link   = item.find("link").get_text(strip=True)   if item.find("link")   else ""
            source = item.find("source").get_text(strip=True) if item.find("source") else ""
            # Clean Google News redirect URL
            if "news.google.com" in link:
                link = link  # keep as-is; redirect will open correctly in browser
            results.append({"title": title, "source": source, "link": link})
        return results
    except Exception as e:
        return []


def _fetch_category(category: str, max_items: int = 6) -> str:
    """Fetch headlines for a known category."""
    if not _DEPS_OK:
        return "❌ Missing dependency: `pip install requests beautifulsoup4 lxml`"

    url = CATEGORY_URLS.get(category.lower().strip())
    if not url:
        return _fetch_topic(category, max_items)

    try:
        r = requests.get(url, headers=HEADERS, timeout=10, verify=False)
        r.raise_for_status()
        articles = _parse_rss(r.text, max_items)
        if not articles:
            return f"❌ No news found for category '{category}'."
        return _format_news(articles, category.title() + " News")
    except Exception as e:
        return f"❌ Failed to fetch {category} news: {e}"


def _fetch_topic(topic: str, max_items: int = 6) -> str:
    """Search Google News for any free-form topic."""
    if not _DEPS_OK:
        return "❌ Missing dependency: `pip install requests beautifulsoup4 lxml`"

    q = urllib.parse.quote(topic)
    url = f"https://news.google.com/rss/search?q={q}&hl=en-IN&gl=IN&ceid=IN:en"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10, verify=False)
        r.raise_for_status()
        articles = _parse_rss(r.text, max_items)
        if not articles:
            return f"❌ No news results found for '{topic}'."
        return _format_news(articles, f"News: {topic.title()}")
    except Exception as e:
        return f"❌ Failed to search news for '{topic}': {e}"


def _format_news(articles: list[dict], heading: str) -> str:
    """Format articles into a clean Markdown string."""
    lines = [f"## 📰 {heading}\n"]
    for i, a in enumerate(articles, 1):
        source = f" — *{a['source']}*" if a["source"] else ""
        lines.append(f"**{i}. {a['title']}**{source}")
        if a["link"]:
            lines.append(f"   🔗 {a['link']}")
        lines.append("")
    return "\n".join(lines)


def get_news(category_or_topic: str = "tech", max_items: int = 6) -> str:
    """
    Fetch live news headlines from Google News RSS.

    Examples:
        get_news("tech")           → Latest tech headlines
        get_news("sports")         → Latest sports headlines
        get_news("AI")             → News about AI
        get_news("cricket")        → News about cricket
        get_news("business")       → Business news

    No API key required. Supports: tech, world, business, finance,
    sports, health, science, entertainment, india, or any free topic.
    """
    # Normalize input
    raw = category_or_topic.lower().strip()

    # Strip common prefixes users might say
    for prefix in ("news about ", "latest ", "show me ", "get ", "fetch "):
        if raw.startswith(prefix):
            raw = raw[len(prefix):]

    # Remove trailing " news"
    if raw.endswith(" news"):
        raw = raw[:-5].strip()

    known = set(CATEGORY_URLS.keys())
    if raw in known:
        return _fetch_category(raw, max_items)
    else:
        return _fetch_topic(raw, max_items)
