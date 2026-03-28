"""REPLACE"""
"""
YouTube Trending Topics Scraper
For: Beauty & Skincare niche (Nykaa-style campaigns)
Outputs data matching your trends DB schema
Requires: pip install google-api-python-client python-dotenv
"""

import os
import json
import re
from datetime import datetime, timezone
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()

# ─── CONFIG ───────────────────────────────────────────────────────────────────

API_KEY = "AIzaSyCnYNseR4DKjBOdWiaFqEKn2ewrmav6uPc"  # Set in .env file

# Search queries targeting Indian beauty/skincare trends (mirrors your DB)
SEARCH_QUERIES = [
    "skincare routine Indian skin type",
    "SPF sunscreen dark skin India",
    "affordable makeup dupes Nykaa",
    "Diwali festive makeup tutorial",
    "niacinamide serum pigmentation",
    "anti hair fall oil India",
    "Korean skincare Indian adaptation",
    "beauty sale haul India",
]

REGION_CODE = "IN"          # India
MAX_RESULTS_PER_QUERY = 10  # YouTube API max per request = 50

# ─── SENTIMENT (simple keyword-based) ────────────────────────────────────────

POSITIVE_WORDS = {"best", "love", "amazing", "glow", "affordable", "recommend",
                  "holy grail", "obsessed", "perfect", "wow", "great", "good"}
NEGATIVE_WORDS = {"worst", "terrible", "hate", "awful", "bad", "broke", "fake",
                  "scam", "disappointing", "avoid", "poor", "horrible"}

def detect_sentiment(text: str) -> str:
    text_lower = text.lower()
    pos = sum(1 for w in POSITIVE_WORDS if w in text_lower)
    neg = sum(1 for w in NEGATIVE_WORDS if w in text_lower)
    if pos > neg:
        return "positive"
    elif neg > pos:
        return "negative"
    return "neutral"

# ─── HASHTAG EXTRACTION ───────────────────────────────────────────────────────

def extract_hashtags(text: str) -> list[str]:
    """Pull #hashtags from title + description."""
    tags = re.findall(r"#\w+", text or "")
    return list(set(tags))[:5]  # Cap at 5, dedupe

# ─── ENGAGEMENT SCORE (0–1 like your schema's `score` column) ────────────────

def compute_score(stats: dict) -> float:
    """
    Simple engagement ratio: likes / (likes + dislikes_estimated + comments).
    YouTube hides dislikes; we approximate using likes + comments.
    """
    likes    = int(stats.get("likeCount", 0))
    comments = int(stats.get("commentCount", 0))
    views    = int(stats.get("viewCount", 1))

    if views == 0:
        return 0.0

    # Engagement rate capped at 1.0
    score = (likes + comments) / max(views, 1)
    return round(min(score * 10, 1.0), 2)  # Scale & clamp

# ─── CATEGORY MAPPER ─────────────────────────────────────────────────────────

def infer_category(query: str) -> str:
    q = query.lower()
    if "hair" in q:
        return "haircare"
    elif "makeup" in q or "diwali" in q or "festive" in q:
        return "makeup"
    elif "skincare" in q or "niacinamide" in q or "spf" in q or "korean" in q:
        return "skincare"
    elif "sale" in q or "haul" in q:
        return "general"
    return "general"

# ─── MAIN SCRAPER ─────────────────────────────────────────────────────────────

def scrape_youtube_trends(api_key: str) -> list[dict]:
    youtube = build("youtube", "v3", developerKey=api_key)
    results = []
    now = datetime.now(timezone.utc).isoformat()

    for query in SEARCH_QUERIES:
        print(f"[→] Searching: {query}")

        # Step 1: Search for videos
        search_response = youtube.search().list(
            q=query,
            part="id,snippet",
            type="video",
            regionCode=REGION_CODE,
            relevanceLanguage="en",
            order="relevance",           # or "viewCount", "date", "rating"
            maxResults=MAX_RESULTS_PER_QUERY,
            publishedAfter="2024-01-01T00:00:00Z",  # Recent content only
        ).execute()

        video_ids = [
            item["id"]["videoId"]
            for item in search_response.get("items", [])
            if item["id"]["kind"] == "youtube#video"
        ]

        if not video_ids:
            print(f"    [!] No results for: {query}")
            continue

        # Step 2: Fetch video statistics (views, likes, comments)
        stats_response = youtube.videos().list(
            part="statistics,snippet",
            id=",".join(video_ids),
        ).execute()

        for item in stats_response.get("items", []):
            snippet = item["snippet"]
            stats   = item.get("statistics", {})

            title       = snippet.get("title", "")
            description = snippet.get("description", "")
            full_text   = f"{title} {description}"

            hashtags  = extract_hashtags(full_text)
            sentiment = detect_sentiment(title)
            score     = compute_score(stats)
            views     = int(stats.get("viewCount", 0))
            published = snippet.get("publishedAt", now)

            record = {
                # Matches your DB columns
                "brand_id":    1,                       # Hardcode or pass dynamically
                "platform":    "youtube",
                "category":    infer_category(query),
                "topic":       title[:200],              # Truncate to safe length
                "hashtags":    json.dumps(hashtags),
                "sentiment":   sentiment,
                "volume":      views,
                "score":       score,
                "scraped_at":  now,
                "expires_at":  None,                    # Set TTL logic if needed

                # Extra metadata (useful for campaigns, not in schema yet)
                "_video_id":   item["id"],
                "_channel":    snippet.get("channelTitle", ""),
                "_published":  published,
                "_query":      query,
                "_url":        f"https://youtube.com/watch?v={item['id']}",
            }
            results.append(record)

        print(f"    [✓] Fetched {len(video_ids)} videos")

    return results

# ─── DB INSERT (PostgreSQL example) ──────────────────────────────────────────

def insert_to_db(records: list[dict]):
    """
    Uncomment and configure with your actual DB credentials.
    Uses psycopg2 for PostgreSQL.
    pip install psycopg2-binary
    """
    # import psycopg2
    # conn = psycopg2.connect(
    #     host=os.getenv("DB_HOST"),
    #     dbname=os.getenv("DB_NAME"),
    #     user=os.getenv("DB_USER"),
    #     password=os.getenv("DB_PASSWORD"),
    # )
    # cur = conn.cursor()
    # for r in records:
    #     cur.execute("""
    #         INSERT INTO trends
    #             (brand_id, platform, category, topic, hashtags, sentiment, volume, score, scraped_at)
    #         VALUES
    #             (%(brand_id)s, %(platform)s, %(category)s, %(topic)s, %(hashtags)s,
    #              %(sentiment)s, %(volume)s, %(score)s, %(scraped_at)s)
    #         ON CONFLICT DO NOTHING;
    #     """, r)
    # conn.commit()
    # cur.close()
    # conn.close()
    # print(f"[DB] Inserted {len(records)} records.")
    pass

# ─── ENTRY POINT ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if not API_KEY:
        raise ValueError("Set YOUTUBE_API_KEY in your .env file")

    data = scrape_youtube_trends(API_KEY)

    # Save to JSON for inspection
    output_file = "youtube_trends.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\n[✓] Done. {len(data)} records saved to {output_file}")

    # Pretty-print a sample
    if data:
        print("\n─── Sample Record ───")
        sample = data[0]
        for k, v in sample.items():
            print(f"  {k:15}: {v}")

    # Uncomment to write to DB:
    # insert_to_db(data)
