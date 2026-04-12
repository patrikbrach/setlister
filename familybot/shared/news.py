"""RSS feed parser for top news headlines."""

import feedparser
from typing import Optional

RSS_FEEDS = [
    ("SVT Nyheter", "https://www.svt.se/nyheter/rss.xml"),
    ("Omni", "https://omni.se/feed"),
    ("Reuters World", "https://feeds.reuters.com/reuters/worldNews"),
]


def fetch_headlines(feeds: list[tuple[str, str]] = RSS_FEEDS, max_items: int = 3) -> list[dict]:
    """
    Fetch headlines from multiple RSS feeds and return the top `max_items`.
    Each item is a dict with 'title' and 'link'.
    """
    all_entries = []

    for source_name, url in feeds:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:5]:
                title = entry.get("title", "").strip()
                link = entry.get("link", "").strip()
                if title and link:
                    all_entries.append({"title": title, "link": link, "source": source_name})
        except Exception as e:
            print(f"RSS error for {source_name}: {e}")

    # Deduplicate by title, preserve order
    seen = set()
    unique = []
    for entry in all_entries:
        if entry["title"] not in seen:
            seen.add(entry["title"])
            unique.append(entry)

    return unique[:max_items]


def format_news_telegram(max_items: int = 3) -> str:
    """Format top news headlines for Telegram."""
    headlines = fetch_headlines(max_items=max_items)
    lines = ["📰 *NYHETER*"]
    if not headlines:
        lines.append("Kunde inte hämta nyheter just nu.")
        return "\n".join(lines)
    for i, h in enumerate(headlines, 1):
        lines.append(f"{i}. [{h['title']}]({h['link']})")
    return "\n".join(lines)
