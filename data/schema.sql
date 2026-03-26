-- =============================================================
-- AGENTIC MARKETING SYSTEM — COMPLETE DATABASE SCHEMA (REFINED)
-- Target Company: Nykaa (Beauty E-commerce, India)
-- Database: PostgreSQL 15+
-- =============================================================

SET timezone = 'Asia/Kolkata';

-- =============================================================
-- LAYER 1: COMPANY FOUNDATION TABLES
-- =============================================================

CREATE TABLE IF NOT EXISTS companies (
    id              SERIAL PRIMARY KEY,
    name            TEXT NOT NULL,
    industry        TEXT NOT NULL,
    website         TEXT,
    brand_voice     TEXT,
    avoid_topics    TEXT,
    primary_color   TEXT DEFAULT '#FC2779',
    country         TEXT DEFAULT 'India',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS brand_profiles (
    id                  SERIAL PRIMARY KEY,
    company_id          INT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    brand_name          TEXT NOT NULL,
    tone_of_voice       TEXT,
    power_words         TEXT,
    avoid_phrases       TEXT,
    preferred_channels  TEXT DEFAULT 'email,instagram,linkedin,whatsapp',
    competitors_avoid   TEXT,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS audience_segments (
    id                  SERIAL PRIMARY KEY,
    company_id          INT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    segment_name        TEXT NOT NULL,
    age_range           TEXT,
    gender              TEXT DEFAULT 'female',
    location_tier       TEXT,
    interests           TEXT,
    buying_behaviour    TEXT,
    platform_preference TEXT DEFAULT 'instagram,youtube',
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================
-- LAYER 2: CUSTOMERS (NEW)
-- =============================================================

CREATE TABLE IF NOT EXISTS customers (
    id                  SERIAL PRIMARY KEY,
    email               TEXT NOT NULL UNIQUE,
    first_name          TEXT,
    last_name           TEXT,
    age                 INT,
    gender              TEXT,
    location            TEXT,
    tier                TEXT,
    interests           JSONB,
    buying_behaviour    JSONB,
    platform_preference JSONB,
    lifetime_value      FLOAT,
    last_active         TIMESTAMPTZ,
    segment_ids         JSONB,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================
-- LAYER 3: CAMPAIGN TABLES
-- =============================================================

CREATE TABLE IF NOT EXISTS campaigns (
    id                      SERIAL PRIMARY KEY,
    company_id              INT NOT NULL REFERENCES companies(id),
    brand_profile_id        INT REFERENCES brand_profiles(id),
    audience_segment_id     INT REFERENCES audience_segments(id),

    name                    TEXT NOT NULL,
    channel                 TEXT NOT NULL,
    campaign_type           TEXT DEFAULT 'performance',
    triggered_by            TEXT DEFAULT 'monitor',
    manual_prompt           TEXT,

    ctr                     FLOAT DEFAULT 0,
    open_rate               FLOAT DEFAULT 0,
    roas                    FLOAT DEFAULT 0,
    click_count             INT DEFAULT 0,

    industry_avg_ctr        FLOAT DEFAULT 2.1,
    budget_inr              INT DEFAULT 0,

    original_subject_line   TEXT,
    original_send_time      TEXT,
    why_failing             TEXT,

    status                  TEXT DEFAULT 'active',
    heal_attempts           INT DEFAULT 0,
    max_heal_attempts       INT DEFAULT 3,

    created_at              TIMESTAMPTZ DEFAULT NOW(),
    updated_at              TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_campaigns_monitor
    ON campaigns(ctr, status, heal_attempts)
    WHERE status = 'active';

CREATE INDEX IF NOT EXISTS idx_campaigns_type
    ON campaigns(campaign_type, triggered_by);

CREATE TABLE IF NOT EXISTS campaign_offers (
    id                  SERIAL PRIMARY KEY,
    campaign_id         INT NOT NULL UNIQUE REFERENCES campaigns(id) ON DELETE CASCADE,

    min_discount_pct    INT NOT NULL DEFAULT 10,
    max_discount_pct    INT NOT NULL DEFAULT 10,
    promo_code          TEXT,
    offer_end_datetime  TIMESTAMPTZ,
    eligible_categories TEXT,
    excluded_items      TEXT,
    free_shipping       BOOLEAN DEFAULT FALSE,
    min_order_value_inr INT DEFAULT 0,

    approved_by         TEXT,
    approved_at         TIMESTAMPTZ,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================
-- LAYER 4: TRENDS & SCRAPING
-- =============================================================

CREATE TABLE IF NOT EXISTS trends (
    id              SERIAL PRIMARY KEY,
    company_id      INT REFERENCES companies(id),
    source          TEXT NOT NULL,
    category        TEXT,
    trend_text      TEXT NOT NULL,
    hashtags        JSONB DEFAULT '[]',
    sentiment       TEXT DEFAULT 'positive',
    volume_score    INT DEFAULT 0,
    relevance_score FLOAT DEFAULT 0.5,
    scraped_at      TIMESTAMPTZ DEFAULT NOW(),
    expires_at      TIMESTAMPTZ DEFAULT NOW() + INTERVAL '24 hours'
);

-- Fixed index: removed NOW() from WHERE clause
CREATE INDEX IF NOT EXISTS idx_trends_fresh
    ON trends(company_id, category, scraped_at DESC);

CREATE TABLE IF NOT EXISTS scrape_logs (
    id          SERIAL PRIMARY KEY,
    source      TEXT NOT NULL,
    status      TEXT NOT NULL,
    records_added INT DEFAULT 0,
    error_msg   TEXT,
    ran_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS festival_calendar (
    id                  SERIAL PRIMARY KEY,
    festival_name       TEXT NOT NULL,
    festival_date       DATE NOT NULL,
    trigger_days_before INT DEFAULT 7,
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
    draft_content   JSONB,
    status          TEXT DEFAULT 'draft',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================
-- LAYER 5: AGENT EXECUTION TABLES
-- =============================================================

CREATE TABLE IF NOT EXISTS reasoning_log (
    id              SERIAL PRIMARY KEY,
    campaign_id     INT NOT NULL REFERENCES campaigns(id),
    attempt_number  INT DEFAULT 1,
    agent_name      TEXT NOT NULL,
    status          TEXT DEFAULT 'started',
    input_summary   TEXT,
    output          TEXT,
    reasoning_summary TEXT,
    tokens_used     INT DEFAULT 0,
    cost_usd        FLOAT DEFAULT 0,
    model_used      TEXT DEFAULT 'gemini-2.0-flash',
    duration_ms     INT DEFAULT 0,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_reasoning_live
    ON reasoning_log(campaign_id, created_at DESC);

CREATE TABLE IF NOT EXISTS generated_assets (
    id                          SERIAL PRIMARY KEY,
    campaign_id                 INT NOT NULL REFERENCES campaigns(id),
    attempt_number              INT DEFAULT 1,

    email_subject               TEXT,
    email_preheader             TEXT,
    email_body                  TEXT,
    email_cta                   TEXT,

    instagram_caption           TEXT,
    instagram_hashtags          JSONB DEFAULT '[]',
    instagram_visual_direction  TEXT,

    linkedin_headline           TEXT,
    linkedin_body               TEXT,
    linkedin_cta                TEXT,

    whatsapp_message            TEXT,

    send_time_recommendation    TEXT,
    chosen_discount_pct         INT,
    agent_reasoning             TEXT,
    strategy_json               JSONB,
    trending_hooks_used         JSONB DEFAULT '[]',

    -- New image columns
    image_url                   TEXT,
    image_prompt                TEXT,
    image_model                 TEXT DEFAULT 'dall-e-3',

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

    overall_recommendation      TEXT,
    green_light                 BOOLEAN DEFAULT FALSE,
    decision_reason             TEXT,

    created_at                  TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================
-- LAYER 6: HUMAN-IN-THE-LOOP
-- =============================================================

CREATE TABLE IF NOT EXISTS pending_approvals (
    id              SERIAL PRIMARY KEY,
    campaign_id     INT NOT NULL REFERENCES campaigns(id),
    asset_id        INT NOT NULL REFERENCES generated_assets(id),
    risk_id         INT REFERENCES risk_assessments(id),

    status          TEXT DEFAULT 'pending',
    human_edits     JSONB,
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
-- LAYER 7: EXECUTION & RESULTS
-- =============================================================

CREATE TABLE IF NOT EXISTS published_posts (
    id                  SERIAL PRIMARY KEY,
    approval_id         INT REFERENCES pending_approvals(id),
    campaign_id         INT NOT NULL REFERENCES campaigns(id),
    channel             TEXT NOT NULL,

    final_subject       TEXT,
    final_body          TEXT,
    final_caption       TEXT,
    final_hashtags      JSONB DEFAULT '[]',

    sendgrid_message_id TEXT,
    external_post_id    TEXT,
    send_status         TEXT DEFAULT 'pending',
    recipient_count     INT DEFAULT 1,
    recipient_email     TEXT,

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
    healed          BOOLEAN DEFAULT FALSE,
    note            TEXT,

    recorded_at     TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_snapshots_chart
    ON performance_snapshots(campaign_id, recorded_at DESC);

-- =============================================================
-- LAYER 8: MEMORY
-- =============================================================

CREATE TABLE IF NOT EXISTS campaign_memory (
    id                  SERIAL PRIMARY KEY,
    company_id          INT REFERENCES companies(id),
    festival_tag        TEXT,
    season              TEXT,
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
-- LAYER 9: AUDIT
-- =============================================================

CREATE TABLE IF NOT EXISTS campaign_history (
    id          SERIAL PRIMARY KEY,
    campaign_id INT NOT NULL REFERENCES campaigns(id),
    event_type  TEXT NOT NULL,
    note        TEXT,
    triggered_by TEXT DEFAULT 'system',
    metadata    JSONB DEFAULT '{}',
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_history_campaign
    ON campaign_history(campaign_id, created_at DESC);

-- =============================================================
-- LAYER 10: MANUAL PROMPT LOG
-- =============================================================

CREATE TABLE IF NOT EXISTS prompt_requests (
    id              SERIAL PRIMARY KEY,
    company_id      INT REFERENCES companies(id),
    user_prompt     TEXT NOT NULL,
    parsed_intent   TEXT,
    campaign_id     INT REFERENCES campaigns(id),
    status          TEXT DEFAULT 'received',
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