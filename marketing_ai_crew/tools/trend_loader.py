"""
tools/trend_loader.py
----------------------
Loads scraped trend data (YouTube + Google) from JSON files and
builds a structured context string for injection into agent prompts.

Expects these files in the project root (or configured paths):
  - youtube_trends.json   ← output of youtube_scraper.py
  - google_trends.json    ← output of your Google Trends scraper (same schema)

Both files should contain a list of records matching the trends DB schema:
  { platform, category, topic, hashtags, sentiment, volume, score, ... }
"""

import json
import os
import logging
from typing import Optional

logger = logging.getLogger("trend_loader")

# ── File paths (override via env vars if needed) ──────────────────────────────
YOUTUBE_TRENDS_FILE = os.getenv("YOUTUBE_TRENDS_FILE", "youtube_trends.json")
GOOGLE_TRENDS_FILE  = os.getenv("GOOGLE_TRENDS_FILE",  "google_trends.json")


# ── Loader ────────────────────────────────────────────────────────────────────

def _load_json(filepath: str) -> list[dict]:
    """Load a JSON trend file. Returns empty list if file is missing or malformed."""
    if not os.path.exists(filepath):
        logger.warning("Trend file not found: %s", filepath)
        return []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            logger.warning("Expected a list in %s, got %s", filepath, type(data))
            return []
        logger.info("Loaded %d records from %s", len(data), filepath)
        return data
    except Exception as e:
        logger.error("Failed to load %s: %s", filepath, e)
        return []


def _filter_and_rank(
    records: list[dict],
    category: Optional[str],
    top_n: int,
) -> list[dict]:
    """
    Filter by category (if given), then sort by score DESC, volume DESC.
    Returns top_n results.
    """
    if category:
        records = [r for r in records if r.get("category", "").lower() == category.lower()]

    records = sorted(
        records,
        key=lambda r: (float(r.get("score", 0)), int(r.get("volume", 0))),
        reverse=True,
    )
    return records[:top_n]


def _format_hashtags(raw: str | list) -> str:
    """Normalise hashtags — stored as JSON string or already a list."""
    if isinstance(raw, list):
        tags = raw
    elif isinstance(raw, str):
        try:
            tags = json.loads(raw)
        except Exception:
            # Fallback: space-separated string
            tags = raw.split()
    else:
        return ""
    return " ".join(tags) if tags else ""


# ── Public API ────────────────────────────────────────────────────────────────

def build_trend_context(
    category: Optional[str] = None,
    top_n: int = 5,
    youtube_file: str = YOUTUBE_TRENDS_FILE,
    google_file: str = GOOGLE_TRENDS_FILE,
) -> str:
    """
    Build a concise, LLM-ready trend context string from scraped trend files.

    Args:
        category     : Filter by category ("skincare", "makeup", "haircare", "general").
                       Pass None to include all categories.
        top_n        : Number of top trends to surface per platform.
        youtube_file : Path to youtube_trends.json
        google_file  : Path to google_trends.json

    Returns:
        A formatted string ready to be appended to an agent's prompt context.
        Returns an empty string if no data is available.
    """
    yt_records = _load_json(youtube_file)
    gg_records = _load_json(google_file)

    yt_top = _filter_and_rank(yt_records, category, top_n)
    gg_top = _filter_and_rank(gg_records, category, top_n)

    if not yt_top and not gg_top:
        logger.warning("No trend data available for category=%s", category)
        return ""

    lines = ["=== REAL-TIME TREND INTELLIGENCE ==="]
    cat_label = category.title() if category else "All Categories"
    lines.append(f"Category filter: {cat_label} | Top {top_n} per platform\n")

    # ── YouTube Trends ────────────────────────────────────────────────────────
    if yt_top:
        lines.append("── YouTube Trending Topics ──")
        for i, r in enumerate(yt_top, 1):
            hashtags = _format_hashtags(r.get("hashtags", []))
            lines.append(
                f"{i}. [{r.get('sentiment', 'neutral').upper()}] {r.get('topic', 'N/A')}"
            )
            lines.append(
                f"   Views: {int(r.get('volume', 0)):,}  |  Score: {r.get('score', 0)}"
                f"  |  Channel: {r.get('_channel', 'N/A')}"
            )
            if hashtags:
                lines.append(f"   Hashtags: {hashtags}")
            lines.append(f"   URL: {r.get('_url', '')}")
        lines.append("")

    # ── Google Trends ─────────────────────────────────────────────────────────
    if gg_top:
        lines.append("── Google Trending Searches ──")
        for i, r in enumerate(gg_top, 1):
            hashtags = _format_hashtags(r.get("hashtags", []))
            lines.append(
                f"{i}. [{r.get('sentiment', 'neutral').upper()}] {r.get('topic', 'N/A')}"
            )
            lines.append(
                f"   Search Volume: {int(r.get('volume', 0)):,}  |  Score: {r.get('score', 0)}"
            )
            if hashtags:
                lines.append(f"   Hashtags: {hashtags}")
        lines.append("")

    # ── Summary hints for the agent ───────────────────────────────────────────
    all_tags: list[str] = []
    for r in yt_top + gg_top:
        parsed = json.loads(r["hashtags"]) if isinstance(r.get("hashtags"), str) else r.get("hashtags", [])
        all_tags.extend(parsed)

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique_tags = [t for t in all_tags if not (t in seen or seen.add(t))]

    if unique_tags:
        lines.append(f"Top hashtags to consider: {' '.join(unique_tags[:8])}")

    positive_topics = [
        r.get("topic", "")[:60]
        for r in (yt_top + gg_top)
        if r.get("sentiment") == "positive"
    ]
    if positive_topics:
        lines.append("Positively-received topics (lean into these):")
        for t in positive_topics[:3]:
            lines.append(f"  • {t}")

    lines.append("\nUSE THIS DATA TO: choose relevant hashtags, mirror language consumers are already using,")
    lines.append("reference trending formats/concerns naturally — never force-fit a trend.")

    return "\n".join(lines)


# ── CLI test ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(build_trend_context(category="skincare", top_n=5))
