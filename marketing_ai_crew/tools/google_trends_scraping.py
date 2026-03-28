import json
import time
import pandas as pd
from datetime import datetime, timezone
from pytrends.request import TrendReq

# ─── CONFIG ─────────────────────────────────────
GEO = "IN"
TIMEFRAME = "today 3-m"
SLEEP_SEC = 5

KEYWORD_BATCHES = [
    ["skincare routine India", "SPF sunscreen India", "niacinamide serum", "vitamin C serum", "face wash India"],
    ["affordable makeup India", "Nykaa sale", "Diwali makeup", "festive makeup tutorial", "kajal eyeliner"],
    ["anti hair fall oil", "hair serum India", "hair mask DIY", "onion hair oil", "scalp care"],
    ["Korean skincare India", "glass skin routine", "beauty haul India", "drugstore skincare", "toner India"],
]

KEYWORD_CATEGORY_MAP = {
    "skincare routine India": "skincare",
    "SPF sunscreen India": "skincare",
    "niacinamide serum": "skincare",
    "vitamin C serum": "skincare",
    "face wash India": "skincare",
    "affordable makeup India": "makeup",
    "Nykaa sale": "general",
    "Diwali makeup": "makeup",
    "festive makeup tutorial": "makeup",
    "kajal eyeliner": "makeup",
    "anti hair fall oil": "haircare",
    "hair serum India": "haircare",
    "hair mask DIY": "haircare",
    "onion hair oil": "haircare",
    "scalp care": "haircare",
    "Korean skincare India": "skincare",
    "glass skin routine": "skincare",
    "beauty haul India": "general",
    "drugstore skincare": "skincare",
    "toner India": "skincare",
}

# ─── FUNCTIONS ──────────────────────────────────

def compute_score(series):
    return round(min(series.iloc[-4:].mean() / 100, 1.0), 2) if not series.empty else 0

def compute_volume(series):
    return int(series.max() * 1000) if not series.empty else 0

def detect_sentiment(series):
    if len(series) < 2:
        return "neutral"
    recent = series.iloc[-4:].mean()
    earlier = series.iloc[:4].mean()
    if recent > earlier * 1.1:
        return "positive"
    elif recent < earlier * 0.9:
        return "negative"
    return "neutral"

def extract_hashtags(keyword):
    words = keyword.lower().split()
    return [f"#{w.capitalize()}" for w in words[:3]]

# ─── MAIN SCRAPER ───────────────────────────────

def scrape_google_trends():
    pytrends = TrendReq(hl="en-IN", tz=330)  # ✅ FIXED

    results = []
    now = datetime.now(timezone.utc).isoformat()

    for i, batch in enumerate(KEYWORD_BATCHES):
        print(f"\n[→] Batch {i+1}: {batch}")

        try:
            pytrends.build_payload(batch, timeframe=TIMEFRAME, geo=GEO)

            df = pytrends.interest_over_time()

            if df.empty:
                print("   ❌ No data")
                continue

            for keyword in batch:
                if keyword not in df.columns:
                    continue

                series = df[keyword].dropna()

                record = {
                    "brand_id": 1,
                    "platform": "google_trends",
                    "category": KEYWORD_CATEGORY_MAP.get(keyword, "general"),
                    "topic": keyword,
                    "hashtags": json.dumps(extract_hashtags(keyword)),
                    "sentiment": detect_sentiment(series),
                    "volume": compute_volume(series),
                    "score": compute_score(series),
                    "scraped_at": now
                }

                results.append(record)

                print(f"   ✔ {keyword} | score={record['score']}")

        except Exception as e:
            print(f"   ❌ Error: {e}")

        time.sleep(SLEEP_SEC)

    return results

# ─── REALTIME TRENDS ───────────────────────────

def get_trending_searches():
    try:
        pytrends = TrendReq(hl="en-IN", tz=330)
        df = pytrends.trending_searches(pn="IN")  # ✅ FIXED
        return df[0].tolist()
    except:
        return []

# ─── RUN ───────────────────────────────────────

if __name__ == "__main__":
    print("🔥 Google Trends Scraper Running...\n")

    data = scrape_google_trends()

    with open("google_trends.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

    print(f"\n✅ Saved {len(data)} records")

    print("\n🔥 Real-time Trends:")
    trends = get_trending_searches()
    for i, t in enumerate(trends[:10], 1):
        print(f"{i}. {t}")
