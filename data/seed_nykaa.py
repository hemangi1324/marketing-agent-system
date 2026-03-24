"""
NYKAA SEED DATA
---------------
Why Nykaa?
- India's largest beauty e-commerce platform (publicly listed)
- Extensive public data available: annual reports, press releases,
  social media, campaign case studies
- CTR and engagement benchmarks published by Mailchimp for beauty
  category match well with Nykaa's reported metrics
- Their brand voice is well documented
- Festival campaigns (Pink Friday, Diwali, Valentine's) are widely
  covered in marketing press

Data sources used:
- Nykaa annual report 2023-24 (nykaa.com/investor-relations)
- Mailchimp Email Marketing Benchmarks 2024 (beauty industry)
- Statista India e-commerce data
- Nykaa's own press releases and blog
- BARC India audience data

Run: python seed_nykaa.py
"""
import os
import psycopg2
import json
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()  # This loads the .env file from the current working directory

DATABASE_URL = os.getenv("DATABASE_URL")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:password@localhost:5432/marketing_db"
)

def seed():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    print("Wiping existing data...")
    tables = [
        "campaign_history", "prompt_requests", "performance_snapshots",
        "published_posts", "pending_approvals", "risk_assessments",
        "generated_assets", "reasoning_log", "seasonal_campaigns",
        "festival_calendar", "scrape_logs", "trends", "campaign_offers",
        "campaigns", "audience_segments", "brand_profiles", "campaign_memory",
        "companies"
    ]
    for t in tables:
        cur.execute(f"DELETE FROM {t}")
    cur.execute("SELECT setval(pg_get_serial_sequence('companies', 'id'), 1, false)")

    # ================================================================
    # COMPANY: NYKAA
    # Source: nykaa.com/about-us, annual report 2023-24
    # ================================================================
    cur.execute("""
        INSERT INTO companies
        (id, name, industry, website, brand_voice, avoid_topics, primary_color, country)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        1,
        "Nykaa",
        "beauty_ecommerce",
        "nykaa.com",
        """We are India's beauty destination. Our voice is aspirational yet accessible —
        we celebrate every woman's unique beauty journey. We speak with warmth, confidence
        and expertise. We use YOU not WE. Short, punchy sentences. Power words:
        glow, luxe, bestseller, limited, your shade, self-care. We are never condescending
        — beauty is for everyone at Nykaa.""",
        "body image criticism, competitor comparisons, unrealistic beauty standards, political content",
        "#FC2779",
        "India"
    ))

    # ================================================================
    # BRAND PROFILE
    # Source: Nykaa's Instagram @nykaa, email campaigns (public)
    # ================================================================
    cur.execute("""
        INSERT INTO brand_profiles
        (id, company_id, brand_name, tone_of_voice, power_words,
         avoid_phrases, preferred_channels, competitors_avoid)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        1, 1, "Nykaa",
        "Warm, aspirational, inclusive, beauty-expert. Celebratory tone for launches. Urgency for sales. Never clinical or cold. Think best friend who knows beauty inside out.",
        "glow, radiant, luxe, bestseller, cult favourite, limited edition, your skin, self-care ritual, game changer",
        "guaranteed results, best in market, cheapest, skin whitening, fair skin",
        "email,instagram,whatsapp,youtube",
        "Purplle, Mamaearth, MyGlamm, Plum"
    ))

    # ================================================================
    # AUDIENCE SEGMENTS
    # Source: Nykaa annual report 2023-24 — customer demographics
    # 85% female customers, avg age 27, Tier 1 + Tier 2 cities
    # ================================================================
    segments = [
        (1, 1, "Beauty enthusiasts 20-30",
         "20-30", "female", "Tier 1 (Mumbai, Delhi, Bangalore, Hyderabad)",
         "skincare routines, K-beauty, makeup tutorials, influencer reviews, dermatologist tips",
         "Impulse buyer triggered by influencer content and limited editions. High cart abandonment. Responds to social proof ('10,000 sold'). Mobile-first shopper. Checks reviews before buying.",
         "instagram,youtube"),

        (2, 1, "Working professionals 28-38",
         "28-38", "female", "Tier 1 and Tier 2",
         "minimal makeup, skincare investment, quality ingredients, time-saving routines",
         "Planned buyer. Reads ingredient lists. Brand loyal once converted. Responds to expert endorsements. Higher basket value. Prefers email over Instagram.",
         "email,instagram"),

        (3, 1, "College students 18-24",
         "18-24", "female", "Tier 1, Tier 2, Tier 3",
         "affordable dupes, trending shades, GenZ aesthetics, clean beauty",
         "Price-sensitive. Discovers via Instagram Reels and YouTube. FOMO-driven. Responds to student discounts and first-order offers. Shares purchases on social media.",
         "instagram,whatsapp"),

        (4, 1, "Bridal and occasion buyers 24-35",
         "24-35", "female", "All India",
         "bridal makeup, wedding skincare prep, luxury brands, longevity testing",
         "High-intent buyer with large basket. Research-heavy — reads 10+ reviews. Responds to before/after content. Seasonal peak: Oct-Feb wedding season.",
         "instagram,youtube,email"),
    ]
    for s in segments:
        cur.execute("""
            INSERT INTO audience_segments
            (id, company_id, segment_name, age_range, gender, location_tier,
             interests, buying_behaviour, platform_preference)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, s)

    # ================================================================
    # FESTIVAL CALENDAR
    # Indian festivals + Nykaa-specific events (Pink Friday)
    # Source: Nykaa press releases, industry calendar
    # ================================================================
    festivals = [
        ("Pink Friday Sale", "2024-11-29", 14, "all", "exciting, exclusive, deal-frenzy",
         "pink themed, bold discounts highlighted, luxury products"),
        ("Diwali", "2024-11-01", 10, "all", "warm, festive, celebratory",
         "gold tones, diyas, gifting focused, family occasion"),
        ("Valentine's Day", "2025-02-14", 10, "18-30 segment", "romantic, self-love, gifting",
         "red and pink, couples and self-care, lipstick focus"),
        ("Women's Day", "2025-03-08", 7, "all", "empowering, celebratory, inclusive",
         "bold, diverse representation, achievement focused"),
        ("Navratri", "2024-10-03", 7, "all", "vibrant, festive, traditional meets modern",
         "navratri colours (each day), traditional makeup looks"),
        ("Summer Skincare", "2025-04-01", 14, "segments 1 and 2", "educational, refreshing",
         "lightweight products, SPF, hydration, summer palette"),
        ("Monsoon Care", "2025-06-15", 14, "all", "helpful, protective, caring",
         "waterproof products, humid weather skincare tips"),
        ("Year End Sale", "2024-12-26", 10, "all", "exciting, countdown, biggest sale",
         "bold discounts, bestsellers compilation"),
    ]
    for i, f in enumerate(festivals, 1):
        cur.execute("""
            INSERT INTO festival_calendar
            (id, festival_name, festival_date, trigger_days_before,
             audience, tone_hint, visual_style_hint)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, (i, *f))

    # ================================================================
    # CAMPAIGNS — FAILING (what monitor watches)
    # ================================================================
    # Benchmark data from Mailchimp 2024 Beauty Industry:
    # Avg CTR: 2.09% | Avg Open Rate: 21.8% | Avg ROAS: 3.2x
    # Nykaa-specific from analyst reports: avg CTR ~2.1-2.4%

    campaigns = [
        # CAMPAIGN 1: Pink Friday Email — demo primary campaign
        {
            "id": 1,
            "company_id": 1,
            "brand_profile_id": 1,
            "audience_segment_id": 1,
            "name": "Pink Friday Email Blast 2024",
            "channel": "email",
            "campaign_type": "performance",
            "triggered_by": "monitor",
            "ctr": 0.38,            # Industry avg 2.09% — this is 82% below
            "open_rate": 11.2,      # Industry avg 21.8%
            "roas": 0.9,            # Industry avg 3.2x — losing money
            "industry_avg_ctr": 2.09,
            "budget_inr": 150000,
            "original_subject_line": "Pink Friday Sale — Up to 60% Off on Top Brands",
            "original_send_time": "Friday 08:00 IST",
            "why_failing": "Generic subject line with no personalisation. 8am Friday is one of the worst email send times for beauty audience. No social proof or urgency hook. Looks like every other sale email.",
            "status": "active",
            "heal_attempts": 0
        },
        # CAMPAIGN 2: Diwali Instagram — failing
        {
            "id": 2,
            "company_id": 1,
            "brand_profile_id": 1,
            "audience_segment_id": 3,
            "name": "Diwali Glam Instagram Campaign",
            "channel": "instagram",
            "campaign_type": "seasonal",
            "triggered_by": "festival_calendar",
            "ctr": 0.51,            # Industry avg 1.2% for Instagram beauty
            "open_rate": 0.0,
            "roas": 1.1,
            "industry_avg_ctr": 1.2,
            "budget_inr": 80000,
            "original_subject_line": None,
            "original_send_time": "Posted Tuesday 14:00 IST",
            "why_failing": "Stock photo of generic diya, no Nykaa branding, caption was just discount announcement with no storytelling. Posted at wrong time — college segment is most active 7-10pm IST.",
            "status": "active",
            "heal_attempts": 0
        },
        # CAMPAIGN 3: Skincare Launch Email — launched via manual prompt
        {
            "id": 3,
            "company_id": 1,
            "brand_profile_id": 1,
            "audience_segment_id": 2,
            "name": "Nykaa Skin Stories Launch Campaign",
            "channel": "email",
            "campaign_type": "manual_prompt",
            "triggered_by": "manual_prompt",
            "manual_prompt": "Launch a campaign for our new Nykaa Skin Stories serum range targeting working professionals. Focus on the science-backed ingredients angle.",
            "ctr": 0.0,
            "open_rate": 0.0,
            "roas": 0.0,
            "industry_avg_ctr": 2.09,
            "budget_inr": 100000,
            "original_subject_line": None,
            "original_send_time": None,
            "why_failing": None,    # new campaign, not failing yet
            "status": "active",
            "heal_attempts": 0
        },
    ]

    for c in campaigns:
        cur.execute("""
            INSERT INTO campaigns
            (id, company_id, brand_profile_id, audience_segment_id,
             name, channel, campaign_type, triggered_by, manual_prompt,
             ctr, open_rate, roas, industry_avg_ctr, budget_inr,
             original_subject_line, original_send_time, why_failing,
             status, heal_attempts)
            VALUES
            (%(id)s, %(company_id)s, %(brand_profile_id)s, %(audience_segment_id)s,
             %(name)s, %(channel)s, %(campaign_type)s, %(triggered_by)s, %(manual_prompt)s,
             %(ctr)s, %(open_rate)s, %(roas)s, %(industry_avg_ctr)s, %(budget_inr)s,
             %(original_subject_line)s, %(original_send_time)s, %(why_failing)s,
             %(status)s, %(heal_attempts)s)
        """, {**c, "manual_prompt": c.get("manual_prompt")})

    # ================================================================
    # CAMPAIGN OFFERS
    # (Human enters these — agent cannot change)
    # ================================================================
    offers = [
        # Pink Friday — 60% off, locked
        (1, 1, 60, 60, "PINK60", "2024-11-30 23:59:00",
         "makeup, skincare, haircare, fragrances, tools",
         "luxury brands over 5000, gift sets",
         True, 499, "Adwaita Nayar, CEO Nykaa Fashion", None),

        # Diwali — 30-40% range, agent picks
        (2, 2, 30, 40, "DIWALIGLOW", "2024-11-05 23:59:00",
         "festive makeup, gifting, skincare combos",
         "luxury brands",
         True, 699, "Marketing Head", None),

        # Serum launch — no discount (brand new product)
        (3, 3, 0, 0, "SKINSTORIES10",  # 10% launch offer
         "2024-12-31 23:59:00",
         "Nykaa Skin Stories range only",
         None, True, 0, "Product Team", None),
    ]

    for o in offers:
        cur.execute("""
            INSERT INTO campaign_offers
            (id, campaign_id, min_discount_pct, max_discount_pct,
             promo_code, offer_end_datetime, eligible_categories,
             excluded_items, free_shipping, min_order_value_inr,
             approved_by, approved_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, o)

    # ================================================================
    # INITIAL TRENDS DATA (realistic — would be scraped in production)
    # Based on actual beauty trends India Oct-Nov 2024
    # Source: Google Trends India, Reddit r/IndianSkincareAddicts
    # ================================================================
    trends_data = [
        # Reddit r/IndianSkincareAddicts trending topics
        (1, "reddit", "skincare",
         "glass skin routine for Indian skin type",
         json.dumps(["#GlassSkin", "#SkincareIndia", "#NaturalGlow"]),
         "positive", 850, 0.92),

        (1, "reddit", "skincare",
         "SPF recommendations dark skin Indian summer",
         json.dumps(["#SPFeveryday", "#SkincareHindi", "#SunscreenIndia"]),
         "positive", 720, 0.88),

        (1, "youtube", "makeup",
         "affordable drugstore makeup dupes Nykaa vs luxury",
         json.dumps(["#NykaaDupes", "#AffordableMakeup", "#IndianBeauty"]),
         "positive", 950, 0.95),

        (1, "youtube", "makeup",
         "festive makeup looks Diwali 2024 tutorial",
         json.dumps(["#DiwaliMakeup", "#FestiveLook2024", "#NykaaMakeup"]),
         "positive", 1200, 0.97),

        (1, "google", "skincare",
         "niacinamide serum benefits for pigmentation",
         json.dumps(["#Niacinamide", "#Pigmentation", "#SkincareIngredients"]),
         "positive", 1500, 0.90),

        (1, "google", "haircare",
         "anti hair fall oil best India 2024",
         json.dumps(["#HairFall", "#HaircareIndia", "#NaturalHaircare"]),
         "positive", 980, 0.75),

        (1, "youtube", "skincare",
         "10 step Korean skincare routine Indian adaptation",
         json.dumps(["#KBeautyIndia", "#KoreanSkincare", "#10StepRoutine"]),
         "positive", 1100, 0.89),

        (None, "google", "general",
         "Pink Friday sale 2024 beauty deals",
         json.dumps(["#PinkFriday", "#BeautyDeals", "#NykaaPinkFriday"]),
         "positive", 2000, 0.99),
    ]

    for i, t in enumerate(trends_data, 1):
        cur.execute("""
            INSERT INTO trends
            (id, company_id, source, category, trend_text, hashtags,
             sentiment, volume_score, relevance_score)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (i, *t))

    # ================================================================
    # CAMPAIGN MEMORY — previous year's learnings
    # (Simulated based on Nykaa's known Pink Friday performance)
    # ================================================================
    cur.execute("""
        INSERT INTO campaign_memory
        (company_id, festival_tag, season, year, campaign_id,
         what_worked, what_failed, winning_tone, winning_visual,
         top_hashtags, final_ctr, attempts_needed, recommendations)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        1, "pink_friday", "winter", 2023, None,
        "Urgency-based subject lines with specific hours remaining performed 3x better. Personalisation with first name increased open rate by 28%. Countdown timer in email body doubled CTR.",
        "Generic 'sale' subject lines. Sending before 9am. Images without product names visible. No clear CTA above fold.",
        "urgent, exclusive, personalised",
        "close-up product shots with discount badge, countdown timer, clean white background with pink accents",
        json.dumps(["#NykaaPinkFriday", "#PinkFridaySale", "#NykaaBeauty", "#BeautyDeals"]),
        2.87, 2,
        "Send at 11am or 7pm IST. Use 'X hours left' in subject. Include social proof numbers. Feature bestsellers not entire catalogue."
    ))

    # ================================================================
    # PROMPT REQUESTS — the manual prompt campaign
    # ================================================================
    cur.execute("""
        INSERT INTO prompt_requests
        (id, company_id, user_prompt, parsed_intent, campaign_id, status, processed_at)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
    """, (
        1, 1,
        "Launch a campaign for our new Nykaa Skin Stories serum range targeting working professionals. Focus on the science-backed ingredients angle.",
        "new_product_launch: product=Nykaa Skin Stories serum, audience=working professionals 28-38, angle=science and ingredients, channel=email+instagram",
        3, "completed", datetime.now()
    ))

    # ================================================================
    # CAMPAIGN HISTORY — initial events
    # ================================================================
    history_events = [
        (1, "created", "Pink Friday campaign created by marketing team", "human"),
        (1, "launched", "Email sent to 450,000 subscribers", "system"),
        (1, "performance_check", "24hr check: CTR 0.38%, Open 11.2% — both below threshold", "monitor"),
        (2, "created", "Diwali campaign created from festival calendar", "system"),
        (2, "launched", "Posted to Instagram — 1.2M followers", "system"),
        (2, "performance_check", "48hr check: CTR 0.51% — below 1.2% Instagram beauty average", "monitor"),
        (3, "created", "Campaign created from manual user prompt", "system"),
        (3, "manual_prompt_received", "User: 'Launch a campaign for Nykaa Skin Stories serum targeting working professionals'", "human"),
    ]
    for i, (cid, etype, note, tby) in enumerate(history_events, 1):
        cur.execute("""
            INSERT INTO campaign_history
            (id, campaign_id, event_type, note, triggered_by)
            VALUES (%s,%s,%s,%s,%s)
        """, (i, cid, etype, note, tby))

    conn.commit()
    cur.close()
    conn.close()
    print("Nykaa seed data inserted successfully.")
    print("Campaigns seeded:")
    print("  Campaign 1 — Pink Friday Email (CTR 0.38%) — FAILING → monitor trigger")
    print("  Campaign 2 — Diwali Instagram (CTR 0.51%) — FAILING → festival trigger")
    print("  Campaign 3 — Skin Stories Launch — NEW → manual prompt trigger")

if __name__ == "__main__":
    seed()
