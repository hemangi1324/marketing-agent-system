-- =============================================================
-- AGENTIC MARKETING SYSTEM — COMPLETE DATABASE SCHEMA
-- Target Company: Nykaa (Beauty E-commerce, India)
-- Database: PostgreSQL 15+
-- =============================================================

-- PRAGMA equivalent for PostgreSQL
-- Run this once after connecting:
-- SET timezone = 'Asia/Kolkata';

-- =============================================================
-- LAYER 1: COMPANY FOUNDATION TABLES
-- (Human fills these via UI — one time setup)
-- =============================================================

CREATE TABLE IF NOT EXISTS companies (
    id              SERIAL PRIMARY KEY,
    name            TEXT NOT NULL,              -- "Nykaa"
    industry        TEXT NOT NULL,              -- "beauty_ecommerce"
    website         TEXT,                       -- "nykaa.com"
    brand_voice     TEXT,                       -- full brand voice paragraph
    avoid_topics    TEXT,                       -- comma-separated
    primary_color   TEXT DEFAULT '#FC2779',     -- Nykaa pink
    country         TEXT DEFAULT 'India',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS brand_profiles (
    id                  SERIAL PRIMARY KEY,
    company_id          INT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    brand_name          TEXT NOT NULL,
    tone_of_voice       TEXT,
    power_words         TEXT,                   -- "glow, luxe, bestseller, limited"
    avoid_phrases       TEXT,                   -- "guaranteed, cheapest"
    preferred_channels  TEXT DEFAULT 'email,instagram,linkedin,whatsapp',
    competitors_avoid   TEXT,                   -- "Purplle, Mamaearth, Plum"
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS audience_segments (
    id                  SERIAL PRIMARY KEY,
    company_id          INT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    segment_name        TEXT NOT NULL,          -- "Beauty enthusiasts 20-30"
    age_range           TEXT,                   -- "20-30"
    gender              TEXT DEFAULT 'female',
    location_tier       TEXT,                   -- "Tier 1 and Tier 2"
    interests           TEXT,                   -- "skincare, makeup tutorials, K-beauty"
    buying_behaviour    TEXT,                   -- "responds to influencer reviews, FOMO buyer"
    platform_preference TEXT DEFAULT 'instagram,youtube',
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================
-- LAYER 2: CAMPAIGN TABLES
-- (Human creates campaign + offer, system fills the rest)
-- =============================================================

CREATE TABLE IF NOT EXISTS campaigns (
    id                      SERIAL PRIMARY KEY,
    company_id              INT NOT NULL REFERENCES companies(id),
    brand_profile_id        INT REFERENCES brand_profiles(id),
    audience_segment_id     INT REFERENCES audience_segments(id),

    -- Campaign identity
    name                    TEXT NOT NULL,      -- "Nykaa Pink Friday Sale"
    channel                 TEXT NOT NULL,      -- "email" / "instagram" / "multi"
    campaign_type           TEXT DEFAULT 'performance',
                            -- "performance" | "seasonal" | "manual_prompt"
    triggered_by            TEXT DEFAULT 'monitor',
                            -- "monitor" | "festival_calendar" | "manual_prompt"
    manual_prompt           TEXT,               -- if user typed a prompt, stored here

    -- Current performance (failing metrics)
    ctr                     FLOAT DEFAULT 0,
    open_rate               FLOAT DEFAULT 0,
    roas                    FLOAT DEFAULT 0,
    click_count             INT DEFAULT 0,

    -- Benchmark for comparison
    industry_avg_ctr        FLOAT DEFAULT 2.1,  -- Nykaa industry avg
    budget_inr              INT DEFAULT 0,

    -- Why it's failing (human or auto-diagnosed)
    original_subject_line   TEXT,
    original_send_time      TEXT,
    why_failing             TEXT,

    -- Pipeline state machine
    status                  TEXT DEFAULT 'active',
                            -- active | healing | awaiting_approval
                            -- | approved | published | healed | escalated | failed
    heal_attempts           INT DEFAULT 0,
    max_heal_attempts       INT DEFAULT 3,

    created_at              TIMESTAMPTZ DEFAULT NOW(),
    updated_at              TIMESTAMPTZ DEFAULT NOW()
);

-- Index for monitor query — this runs every 60 seconds
CREATE INDEX IF NOT EXISTS idx_campaigns_monitor
    ON campaigns(ctr, status, heal_attempts)
    WHERE status = 'active';

-- Index for manual prompt lookup
CREATE INDEX IF NOT EXISTS idx_campaigns_type
    ON campaigns(campaign_type, triggered_by);

CREATE TABLE IF NOT EXISTS campaign_offers (
    id                  SERIAL PRIMARY KEY,
    campaign_id         INT NOT NULL UNIQUE REFERENCES campaigns(id) ON DELETE CASCADE,

    -- Financial rules — SET BY HUMAN, READ-ONLY for agents
    min_discount_pct    INT NOT NULL DEFAULT 10,
    max_discount_pct    INT NOT NULL DEFAULT 10,  -- set min=max to lock it
    promo_code          TEXT,                     -- "PINK40"
    offer_end_datetime  TIMESTAMPTZ,              -- exact deadline
    eligible_categories TEXT,                     -- "skincare, lipsticks, haircare"
    excluded_items      TEXT,                     -- "luxury brands, gift sets"
    free_shipping       BOOLEAN DEFAULT FALSE,
    min_order_value_inr INT DEFAULT 0,

    -- Approval trail
    approved_by         TEXT,                     -- "Falguni Nayar, CEO"
    approved_at         TIMESTAMPTZ,

    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================
-- LAYER 3: SCRAPING / TREND TABLES
-- (Populated by background scrapers every 6 hours)
-- =============================================================

CREATE TABLE IF NOT EXISTS trends (
    id              SERIAL PRIMARY KEY,
    company_id      INT REFERENCES companies(id),  -- NULL means global trends
    source          TEXT NOT NULL,                  -- "reddit" | "youtube" | "google" | "twitter"
    category        TEXT,                           -- "beauty" | "skincare" | "haircare"
    trend_text      TEXT NOT NULL,                  -- "glass skin routine"
    hashtags        JSONB DEFAULT '[]',             -- ["#GlassSkin", "#KBeauty"]
    sentiment       TEXT DEFAULT 'positive',        -- positive | negative | neutral
    volume_score    INT DEFAULT 0,                  -- relative popularity
    relevance_score FLOAT DEFAULT 0.5,              -- 0-1 relevance to brand
    scraped_at      TIMESTAMPTZ DEFAULT NOW(),
    expires_at      TIMESTAMPTZ DEFAULT NOW() + INTERVAL '24 hours'
);

CREATE INDEX IF NOT EXISTS idx_trends_fresh
    ON trends(company_id, category, scraped_at DESC);

CREATE TABLE IF NOT EXISTS scrape_logs (
    id          SERIAL PRIMARY KEY,
    source      TEXT NOT NULL,
    status      TEXT NOT NULL,  -- "success" | "failed" | "rate_limited"
    records_added INT DEFAULT 0,
    error_msg   TEXT,
    ran_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Festival/seasonal campaign pre-planning
CREATE TABLE IF NOT EXISTS festival_calendar (
    id                  SERIAL PRIMARY KEY,
    festival_name       TEXT NOT NULL,          -- "Diwali", "Valentines Day"
    festival_date       DATE NOT NULL,
    trigger_days_before INT DEFAULT 7,          -- start building 7 days before
    audience            TEXT DEFAULT 'all',
    tone_hint           TEXT DEFAULT 'warm, festive',
    visual_style_hint   TEXT DEFAULT 'warm colours, celebration',
    is_active           BOOLEAN DEFAULT TRUE,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS seasonal_campaigns (
    id              SERIAL PRIMARY KEY,
    campaign_id     INT REFERENCES campaigns(id),
    festival_id     INT REFERENCES festival_calendar(id),
    draft_content   JSONB,                      -- pre-generated draft
    status          TEXT DEFAULT 'draft',       -- draft | pending_approval | approved | published
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================
-- LAYER 4: AGENT EXECUTION TABLES
-- (Written by agents during pipeline run)
-- =============================================================

CREATE TABLE IF NOT EXISTS reasoning_log (
    id              SERIAL PRIMARY KEY,
    campaign_id     INT NOT NULL REFERENCES campaigns(id),
    attempt_number  INT DEFAULT 1,
    agent_name      TEXT NOT NULL,
                    -- "strategy" | "content" | "risk" | "decision"
                    -- | "execution" | "analytics" | "scraper"
    status          TEXT DEFAULT 'started',     -- started | completed | failed
    input_summary   TEXT,                       -- short version of what was sent in
    output          TEXT,                       -- full agent response
    reasoning_summary TEXT,                     -- 1 line shown in UI monologue panel
    tokens_used     INT DEFAULT 0,
    cost_usd        FLOAT DEFAULT 0,
    model_used      TEXT DEFAULT 'gemini-2.5-flash',
    duration_ms     INT DEFAULT 0,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- UI polls this every 2 seconds — needs to be fast
CREATE INDEX IF NOT EXISTS idx_reasoning_live
    ON reasoning_log(campaign_id, created_at DESC);

CREATE TABLE IF NOT EXISTS generated_assets (
    id                          SERIAL PRIMARY KEY,
    campaign_id                 INT NOT NULL REFERENCES campaigns(id),
    attempt_number              INT DEFAULT 1,

    -- Email content
    email_subject               TEXT,
    email_preheader             TEXT,
    email_body                  TEXT,
    email_cta                   TEXT,

    -- Instagram content
    instagram_caption           TEXT,
    instagram_hashtags          JSONB DEFAULT '[]',
    instagram_visual_direction  TEXT,

    -- LinkedIn content
    linkedin_headline           TEXT,
    linkedin_body               TEXT,
    linkedin_cta                TEXT,

    -- WhatsApp
    whatsapp_message            TEXT,

    -- Agent decisions (within company-set offer rules)
    send_time_recommendation    TEXT,           -- "Tuesday 10:00 IST"
    chosen_discount_pct         INT,            -- what agent picked
    agent_reasoning             TEXT,           -- why these choices
    strategy_json               JSONB,          -- full strategy from strategy agent
    trending_hooks_used         JSONB DEFAULT '[]',

    created_at                  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS risk_assessments (
    id                          SERIAL PRIMARY KEY,
    asset_id                    INT NOT NULL REFERENCES generated_assets(id),
    campaign_id                 INT NOT NULL REFERENCES campaigns(id),

    brand_safety_score          INT CHECK (brand_safety_score BETWEEN 1 AND 10),
    brand_safety_note           TEXT,
    legal_risk_score            INT CHECK (legal_risk_score BETWEEN 1 AND 10),
    legal_risk_note             TEXT,
    cultural_sensitivity_score  INT CHECK (cultural_sensitivity_score BETWEEN 1 AND 10),
    cultural_sensitivity_note   TEXT,

    overall_recommendation      TEXT,           -- APPROVE | APPROVE_WITH_WARNING | REJECT
    green_light                 BOOLEAN DEFAULT FALSE,
    decision_reason             TEXT,

    created_at                  TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================
-- LAYER 5: HUMAN-IN-THE-LOOP TABLES
-- (Pipeline pauses here for human decision)
-- =============================================================

CREATE TABLE IF NOT EXISTS pending_approvals (
    id              SERIAL PRIMARY KEY,
    campaign_id     INT NOT NULL REFERENCES campaigns(id),
    asset_id        INT NOT NULL REFERENCES generated_assets(id),
    risk_id         INT REFERENCES risk_assessments(id),

    status          TEXT DEFAULT 'pending',
                    -- pending | approved | approved_with_edits | rejected | expired
    human_edits     JSONB,                      -- what human changed (nullable)
    rejection_reason TEXT,
    decided_by      TEXT,
    decided_at      TIMESTAMPTZ,
    expires_at      TIMESTAMPTZ DEFAULT NOW() + INTERVAL '24 hours',

    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pending_approvals_status
    ON pending_approvals(status, expires_at)
    WHERE status = 'pending';

-- =============================================================
-- LAYER 6: EXECUTION + RESULTS TABLES
-- =============================================================

CREATE TABLE IF NOT EXISTS published_posts (
    id                  SERIAL PRIMARY KEY,
    approval_id         INT REFERENCES pending_approvals(id),
    campaign_id         INT NOT NULL REFERENCES campaigns(id),
    channel             TEXT NOT NULL,

    -- Final content (may differ from generated if human edited)
    final_subject       TEXT,
    final_body          TEXT,
    final_caption       TEXT,
    final_hashtags      JSONB DEFAULT '[]',

    -- Delivery proof
    sendgrid_message_id TEXT,                   -- real ID from SendGrid
    external_post_id    TEXT,                   -- Twitter/Instagram post ID
    send_status         TEXT DEFAULT 'pending', -- sent | failed | simulated
    recipient_count     INT DEFAULT 1,
    recipient_email     TEXT,                   -- test inbox for demo

    sent_at             TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS performance_snapshots (
    id              SERIAL PRIMARY KEY,
    campaign_id     INT NOT NULL REFERENCES campaigns(id),
    post_id         INT REFERENCES published_posts(id),
    attempt_number  INT DEFAULT 1,

    ctr             FLOAT DEFAULT 0,
    open_rate       FLOAT DEFAULT 0,
    roas            FLOAT DEFAULT 0,
    click_count     INT DEFAULT 0,

    phase           TEXT DEFAULT 'attempt_1',
                    -- pre_campaign | attempt_1 | attempt_2 | attempt_3 | healed
    healed          BOOLEAN DEFAULT FALSE,
    note            TEXT,

    recorded_at     TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_snapshots_chart
    ON performance_snapshots(campaign_id, recorded_at DESC);

-- =============================================================
-- LAYER 7: MEMORY TABLE
-- (Long-term learning — read by Strategy Agent next run)
-- =============================================================

CREATE TABLE IF NOT EXISTS campaign_memory (
    id                  SERIAL PRIMARY KEY,
    company_id          INT REFERENCES companies(id),
    festival_tag        TEXT,                   -- "diwali" | "valentines" | NULL
    season              TEXT,                   -- "summer" | "winter" | "monsoon"
    year                INT,
    campaign_id         INT REFERENCES campaigns(id),

    what_worked         TEXT,
    what_failed         TEXT,
    winning_tone        TEXT,
    winning_visual      TEXT,
    top_hashtags        JSONB DEFAULT '[]',
    market_trends_json  JSONB DEFAULT '{}',
    final_ctr           FLOAT,
    attempts_needed     INT DEFAULT 1,
    recommendations     TEXT,

    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================
-- LAYER 8: AUDIT / EVENT LOG
-- (Every state change tracked here — never deleted)
-- =============================================================

CREATE TABLE IF NOT EXISTS campaign_history (
    id          SERIAL PRIMARY KEY,
    campaign_id INT NOT NULL REFERENCES campaigns(id),
    event_type  TEXT NOT NULL,
                -- created | launched | monitor_triggered | manual_prompt_received
                -- | agent_started | agent_completed | risk_flagged | awaiting_approval
                -- | approved | rejected | published | performance_check
                -- | self_heal_triggered | healed | escalated | failed
    note        TEXT,
    triggered_by TEXT DEFAULT 'system',         -- "system" | "human" | "monitor" | "agent"
    metadata    JSONB DEFAULT '{}',
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_history_campaign
    ON campaign_history(campaign_id, created_at DESC);

-- =============================================================
-- LAYER 9: MANUAL PROMPT LOG
-- (Every user-typed instruction tracked here)
-- =============================================================

CREATE TABLE IF NOT EXISTS prompt_requests (
    id              SERIAL PRIMARY KEY,
    company_id      INT REFERENCES companies(id),
    user_prompt     TEXT NOT NULL,              -- "launch a campaign for new lipstick launch"
    parsed_intent   TEXT,                       -- what the system understood
    campaign_id     INT REFERENCES campaigns(id), -- campaign created as result
    status          TEXT DEFAULT 'received',    -- received | processing | completed | failed
    processed_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================
-- HELPER: updated_at auto-trigger
-- =============================================================

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER campaigns_updated_at
    BEFORE UPDATE ON campaigns
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
