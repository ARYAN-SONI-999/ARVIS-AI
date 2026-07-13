"""
ARVIS Web Reader Skill — Fetches and parses content from any webpage (No API Key needed)
"""

import requests
import urllib3
import warnings
from bs4 import BeautifulSoup

# Suppress SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings("ignore", category=urllib3.exceptions.InsecureRequestWarning)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

def browse_url(url: str, max_chars: int = 4000) -> str:
    """Visits the provided URL, extracts clean, readable text, and returns it.

    Filters out page boilerplate (navigation, footer, styles, scripts) to save tokens.
    """
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    print(f"[Web Reader]: Fetching content from '{url}'...")
    try:
        r = requests.get(url, headers=HEADERS, timeout=12, verify=False)
        r.raise_for_status()
    except Exception as e:
        return f"Error: Failed to fetch the URL: {str(e)}"

    try:
        # Determine content encoding
        r.encoding = r.apparent_encoding
        soup = BeautifulSoup(r.text, "html.parser")

        # Strip headers, footers, scripts, and navigation to clean up boilerplates
        for element in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
            element.decompose()

        # Extract text content
        text = soup.get_text()

        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        clean_text = "\n".join(chunk for chunk in chunks if chunk)

        if not clean_text:
            return "Error: Webpage contained no indexable text content."

        # Return truncated text
        if len(clean_text) > max_chars:
            return clean_text[:max_chars] + f"\n\n... [Content Truncated; showing first {max_chars} characters]"
        return clean_text

    except Exception as e:
        return f"Error: Failed to parse webpage content: {str(e)}"
