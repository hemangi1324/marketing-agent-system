"""
db/database.py
--------------
Database connection pool and all query helper functions.
Every file in the project imports from here — never connects directly.

Why a connection pool?
  Multiple agents run simultaneously. Without a pool, each agent
  opens its own connection. With 5 agents + monitor + API = 7+
  connections opening/closing constantly. A pool keeps 5-10
  connections open and reuses them — much faster and safer.
"""

import psycopg2
import psycopg2.extras
import psycopg2.pool
import json
from contextlib import contextmanager
from datetime import datetime
from typing import Optional
import subprocess
import os

from backend.config import DATABASE_URL

# ── Connection pool ───────────────────────────────────────────
# minconn=2: always keep 2 connections open
# maxconn=10: never open more than 10 at once
_pool: psycopg2.pool.ThreadedConnectionPool = None

def init_pool():
    """Call this once when the app starts."""
    global _pool
    _pool = psycopg2.pool.ThreadedConnectionPool(
        minconn=2,
        maxconn=10,
        dsn=DATABASE_URL
    )
    print("[DB] Connection pool initialised.")

def get_pool():
    global _pool
    if _pool is None:
        init_pool()
    return _pool

@contextmanager
def get_conn():
    """
    Context manager for database connections.
    Always use this pattern:

        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(...)
                conn.commit()

    Connection is returned to pool automatically when the
    'with' block exits — even if an exception is raised.
    """
    pool = get_pool()
    conn = pool.getconn()
    conn.cursor_factory = psycopg2.extras.RealDictCursor
    try:
        yield conn
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)


# ── Schema creation ───────────────────────────────────────────

def create_tables():
    """
    Creates all tables if they don't exist.
    Safe to call multiple times (IF NOT EXISTS).
    """
    sql = open("data/schema.sql").read()
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
    print("[DB] All tables created.")


# ════════════════════════════════════════════════════════════════
# COMPANY QUERIES
# These are called when user fills the onboarding form
# ════════════════════════════════════════════════════════════════

def create_company(
    name: str,
    industry: str,
    website: str,
    brand_voice: str,
    avoid_topics: str,
    primary_color: str = "#000000",
    country: str = "India"
) -> int:
    """
    Creates a new company from onboarding form input.
    Returns the new company ID.

    All values come from the user — NOTHING is hardcoded.
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO companies
                    (name, industry, website, brand_voice,
                     avoid_topics, primary_color, country)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (name, industry, website, brand_voice,
                  avoid_topics, primary_color, country))
            company_id = cur.fetchone()["id"]
        conn.commit()
    return company_id

def get_company(company_id: int) -> dict:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM companies WHERE id = %s", (company_id,))
            return dict(cur.fetchone() or {})

def get_all_companies() -> list:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, industry, primary_color FROM companies ORDER BY created_at DESC")
            return [dict(r) for r in cur.fetchall()]

def update_company(company_id: int, **fields) -> None:
    """Update any company fields. Called when user edits profile."""
    allowed = {"name","industry","website","brand_voice","avoid_topics","primary_color"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return
    set_clause = ", ".join(f"{k} = %s" for k in updates)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE companies SET {set_clause} WHERE id = %s",
                (*updates.values(), company_id)
            )
        conn.commit()


# ════════════════════════════════════════════════════════════════
# BRAND PROFILE QUERIES
# User enters tone, power words, avoid phrases through the form
# ════════════════════════════════════════════════════════════════

def create_brand_profile(
    company_id: int,
    brand_name: str,
    tone_of_voice: str,
    power_words: str,
    avoid_phrases: str,
    preferred_channels: str,
    competitors_avoid: str
) -> int:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO brand_profiles
                    (company_id, brand_name, tone_of_voice, power_words,
                     avoid_phrases, preferred_channels, competitors_avoid)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (company_id, brand_name, tone_of_voice, power_words,
                  avoid_phrases, preferred_channels, competitors_avoid))
            profile_id = cur.fetchone()["id"]
        conn.commit()
    return profile_id

def get_brand_profile(company_id: int) -> dict:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM brand_profiles
                WHERE company_id = %s
                ORDER BY created_at DESC LIMIT 1
            """, (company_id,))
            row = cur.fetchone()
            return dict(row) if row else {}

def update_brand_profile(profile_id: int, **fields) -> None:
    allowed = {"tone_of_voice","power_words","avoid_phrases",
               "preferred_channels","competitors_avoid"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return
    set_clause = ", ".join(f"{k} = %s" for k in updates)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE brand_profiles SET {set_clause} WHERE id = %s",
                (*updates.values(), profile_id)
            )
        conn.commit()


# ════════════════════════════════════════════════════════════════
# AUDIENCE SEGMENT QUERIES
# User defines their target audience through the form
# ════════════════════════════════════════════════════════════════

def create_audience_segment(
    company_id: int,
    segment_name: str,
    age_range: str,
    gender: str,
    location_tier: str,
    interests: str,
    buying_behaviour: str,
    platform_preference: str
) -> int:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO audience_segments
                    (company_id, segment_name, age_range, gender,
                     location_tier, interests, buying_behaviour,
                     platform_preference)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                RETURNING id
            """, (company_id, segment_name, age_range, gender,
                  location_tier, interests, buying_behaviour,
                  platform_preference))
            seg_id = cur.fetchone()["id"]
        conn.commit()
    return seg_id

def get_audience_segments(company_id: int) -> list:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM audience_segments
                WHERE company_id = %s
                ORDER BY created_at DESC
            """, (company_id,))
            return [dict(r) for r in cur.fetchall()]

def get_audience_segment(segment_id: int) -> dict:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM audience_segments WHERE id = %s", (segment_id,))
            row = cur.fetchone()
            return dict(row) if row else {}


# ════════════════════════════════════════════════════════════════
# CAMPAIGN OFFER QUERIES
# User enters financial rules — agents read but cannot modify
# ════════════════════════════════════════════════════════════════

def create_campaign_offer(
    campaign_id: int,
    min_discount_pct: int,
    max_discount_pct: int,
    promo_code: str,
    offer_end_datetime: str,
    eligible_categories: str,
    excluded_items: str,
    free_shipping: bool,
    min_order_value_inr: int,
    approved_by: str
) -> int:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO campaign_offers
                    (campaign_id, min_discount_pct, max_discount_pct,
                     promo_code, offer_end_datetime, eligible_categories,
                     excluded_items, free_shipping, min_order_value_inr,
                     approved_by, approved_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s, NOW())
                RETURNING id
            """, (campaign_id, min_discount_pct, max_discount_pct,
                  promo_code, offer_end_datetime, eligible_categories,
                  excluded_items, free_shipping, min_order_value_inr,
                  approved_by))
            offer_id = cur.fetchone()["id"]
        conn.commit()
    return offer_id

def get_campaign_offer(campaign_id: int) -> dict:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM campaign_offers WHERE campaign_id = %s
            """, (campaign_id,))
            row = cur.fetchone()
            return dict(row) if row else {}


# ════════════════════════════════════════════════════════════════
# CAMPAIGN QUERIES
# ════════════════════════════════════════════════════════════════

def create_campaign(
    company_id: int,
    brand_profile_id: int,
    audience_segment_id: int,
    name: str,
    channel: str,
    campaign_type: str = "performance",
    triggered_by: str = "human",
    manual_prompt: Optional[str] = None,
    ctr: float = 0.0,
    open_rate: float = 0.0,
    roas: float = 0.0,
    industry_avg_ctr: float = 2.1,
    budget_inr: int = 0,
    original_subject_line: Optional[str] = None,
    original_send_time: Optional[str] = None,
    why_failing: Optional[str] = None
) -> int:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO campaigns
                    (company_id, brand_profile_id, audience_segment_id,
                     name, channel, campaign_type, triggered_by, manual_prompt,
                     ctr, open_rate, roas, industry_avg_ctr, budget_inr,
                     original_subject_line, original_send_time, why_failing,
                     status, heal_attempts)
                VALUES
                    (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                     'active', 0)
                RETURNING id
            """, (
                company_id, brand_profile_id, audience_segment_id,
                name, channel, campaign_type, triggered_by, manual_prompt,
                ctr, open_rate, roas, industry_avg_ctr, budget_inr,
                original_subject_line, original_send_time, why_failing
            ))
            campaign_id = cur.fetchone()["id"]
        conn.commit()
    return campaign_id

def get_campaign(campaign_id: int) -> dict:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM campaigns WHERE id = %s", (campaign_id,))
            row = cur.fetchone()
            return dict(row) if row else {}

def get_campaigns_for_company(company_id: int) -> list:
    """Returns campaigns with their latest generated content and risk scores."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    c.*,
                    ga.email_subject,
                    ga.instagram_caption,
                    ga.chosen_discount_pct,
                    ra.brand_safety_score,
                    ra.legal_risk_score,
                    ra.cultural_sensitivity_score,
                    ra.green_light,
                    pa.id AS approval_id,
                    pa.status AS approval_status
                FROM campaigns c
                LEFT JOIN LATERAL (
                    SELECT * FROM generated_assets
                    WHERE campaign_id = c.id
                    ORDER BY created_at DESC LIMIT 1
                ) ga ON TRUE
                LEFT JOIN LATERAL (
                    SELECT * FROM risk_assessments
                    WHERE campaign_id = c.id
                    ORDER BY created_at DESC LIMIT 1
                ) ra ON TRUE
                LEFT JOIN LATERAL (
                    SELECT id, status FROM pending_approvals
                    WHERE campaign_id = c.id AND status = 'pending'
                    ORDER BY created_at DESC LIMIT 1
                ) pa ON TRUE
                WHERE c.company_id = %s
                ORDER BY c.updated_at DESC
            """, (company_id,))
            return [dict(r) for r in cur.fetchall()]

def get_failing_campaigns(
    ctr_threshold_email: float,
    ctr_threshold_instagram: float,
    max_heal_attempts: int
) -> list:
    """Called by monitor every 60 seconds."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT c.*, co.promo_code, co.offer_end_datetime,
                       co.min_discount_pct, co.max_discount_pct,
                       co.eligible_categories, co.excluded_items,
                       co.free_shipping
                FROM campaigns c
                LEFT JOIN campaign_offers co ON co.campaign_id = c.id
                WHERE c.status = 'active'
                  AND c.heal_attempts < %s
                  AND (
                      (c.channel = 'email'     AND c.ctr < %s) OR
                      (c.channel = 'instagram' AND c.ctr < %s) OR
                      (c.channel = 'multi'     AND c.ctr < %s)
                  )
                ORDER BY c.ctr ASC
                LIMIT 5
            """, (max_heal_attempts,
                  ctr_threshold_email,
                  ctr_threshold_instagram,
                  ctr_threshold_email))
            return [dict(r) for r in cur.fetchall()]

def update_campaign_status(campaign_id: int, status: str) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE campaigns
                SET status = %s, updated_at = NOW()
                WHERE id = %s
            """, (status, campaign_id))
        conn.commit()

def increment_heal_attempts(campaign_id: int) -> int:
    """Increments heal counter and returns new value."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE campaigns
                SET heal_attempts = heal_attempts + 1, updated_at = NOW()
                WHERE id = %s
                RETURNING heal_attempts
            """, (campaign_id,))
            return cur.fetchone()["heal_attempts"]
        conn.commit()

def set_campaign_metrics(
    campaign_id: int,
    ctr: float,
    open_rate: float = 0.0,
    roas: float = 0.0
) -> None:
    """Called when user enters real performance numbers, or demo button sets them."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE campaigns
                SET ctr = %s, open_rate = %s, roas = %s, updated_at = NOW()
                WHERE id = %s
            """, (ctr, open_rate, roas, campaign_id))
        conn.commit()


# ════════════════════════════════════════════════════════════════
# FULL CAMPAIGN CONTEXT
# This is what gets passed to the Strategy Agent
# All company data + audience + offer rules assembled in one query
# ════════════════════════════════════════════════════════════════

def get_full_campaign_context(campaign_id: int) -> dict:
    """
    Single query that joins everything the Strategy Agent needs.
    Returns a flat dict — agents don't need to know about JOIN logic.
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    -- Campaign fields
                    c.id              AS campaign_id,
                    c.name            AS campaign_name,
                    c.channel,
                    c.campaign_type,
                    c.triggered_by,
                    c.manual_prompt,
                    c.ctr,
                    c.open_rate,
                    c.roas,
                    c.industry_avg_ctr,
                    c.original_subject_line,
                    c.original_send_time,
                    c.why_failing,
                    c.heal_attempts,
                    c.budget_inr,

                    -- Company fields
                    co.name           AS company_name,
                    co.industry,
                    co.brand_voice,
                    co.avoid_topics,

                    -- Brand profile fields (USER-ENTERED)
                    bp.tone_of_voice,
                    bp.power_words,
                    bp.avoid_phrases,
                    bp.preferred_channels,
                    bp.competitors_avoid,

                    -- Audience segment fields (USER-ENTERED)
                    au.segment_name,
                    au.age_range,
                    au.gender,
                    au.location_tier,
                    au.interests,
                    au.buying_behaviour,
                    au.platform_preference,

                    -- Offer rules (USER-ENTERED — agents read only)
                    of.min_discount_pct,
                    of.max_discount_pct,
                    of.promo_code,
                    of.offer_end_datetime,
                    of.eligible_categories,
                    of.excluded_items,
                    of.free_shipping,
                    of.min_order_value_inr,
                    of.approved_by

                FROM campaigns c
                JOIN companies co        ON c.company_id = co.id
                JOIN brand_profiles bp   ON c.brand_profile_id = bp.id
                JOIN audience_segments au ON c.audience_segment_id = au.id
                LEFT JOIN campaign_offers of ON of.campaign_id = c.id
                WHERE c.id = %s
            """, (campaign_id,))
            row = cur.fetchone()
            return dict(row) if row else {}


# ════════════════════════════════════════════════════════════════
# REASONING LOG
# Written by every agent — powers the UI monologue panel
# ════════════════════════════════════════════════════════════════

def log_reasoning(
    campaign_id: int,
    agent_name: str,
    status: str,
    reasoning_summary: str,
    output: str = "",
    input_summary: str = "",
    tokens_used: int = 0,
    cost_usd: float = 0.0,
    model_used: str = "gemini-2.0-flash",
    duration_ms: int = 0,
    attempt_number: int = 1,
    sequence_num: Optional[int] = None
) -> int:
    # If sequence_num not provided, compute it
    if sequence_num is None:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COALESCE(MAX(sequence_num), 0) + 1 AS next_seq
                    FROM reasoning_log
                    WHERE campaign_id = %s AND attempt_number = %s
                """, (campaign_id, attempt_number))
                row = cur.fetchone()
                sequence_num = row["next_seq"] if row else 1
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO reasoning_log
                    (campaign_id, attempt_number, agent_name, status,
                     input_summary, output, reasoning_summary,
                     tokens_used, cost_usd, model_used, duration_ms,
                     sequence_num)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                RETURNING id
            """, (
                campaign_id, attempt_number, agent_name, status,
                input_summary, output, reasoning_summary,
                tokens_used, cost_usd, model_used, duration_ms,
                sequence_num
            ))
            log_id = cur.fetchone()["id"]
        conn.commit()
    return log_id

def get_reasoning_since(campaign_id: int, since_id: int = 0) -> list:
    """UI polls this every 2 seconds for the monologue panel."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, agent_name, reasoning_summary, status,
                       cost_usd, model_used, duration_ms, created_at,
                       sequence_num
                FROM reasoning_log
                WHERE campaign_id = %s AND id > %s
                ORDER BY sequence_num ASC
                LIMIT 50
            """, (campaign_id, since_id))
            return [dict(r) for r in cur.fetchall()]

def get_previous_attempt_reasoning(campaign_id: int, attempt_number: int) -> list:
    """
    Strategy Agent calls this when heal_attempts > 0.
    Returns what went wrong in the previous attempt so the
    agent can try a completely different approach.
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT agent_name, reasoning_summary, output
                FROM reasoning_log
                WHERE campaign_id = %s
                  AND attempt_number = %s
                  AND status = 'completed'
                ORDER BY sequence_num ASC
            """, (campaign_id, attempt_number - 1))
            return [dict(r) for r in cur.fetchall()]


# ════════════════════════════════════════════════════════════════
# GENERATED ASSETS
# ════════════════════════════════════════════════════════════════

def save_generated_assets(
    campaign_id: int,
    attempt_number: int,
    email_subject: str = None,
    email_preheader: str = None,
    email_body: str = None,
    email_cta: str = None,
    email_subject_variants: list = None,
    instagram_caption: str = None,
    instagram_hashtags: list = None,
    instagram_visual_direction: str = None,
    linkedin_headline: str = None,
    linkedin_body: str = None,
    linkedin_cta: str = None,
    twitter_post: str = None,
    whatsapp_message: str = None,
    send_time_recommendation: str = None,
    chosen_discount_pct: int = 0,
    agent_reasoning: str = None,
    strategy_json: dict = None,
    trending_hooks_used: list = None,
    image_url: str = None,
    image_prompt: str = None,
    image_model: str = "dall-e-3"
) -> int:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO generated_assets
                    (campaign_id, attempt_number,
                     email_subject, email_preheader, email_body, email_cta,
                     email_subject_variants,
                     instagram_caption, instagram_hashtags, instagram_visual_direction,
                     linkedin_headline, linkedin_body, linkedin_cta,
                     twitter_post,
                     whatsapp_message, send_time_recommendation,
                     chosen_discount_pct, agent_reasoning,
                     strategy_json, trending_hooks_used,
                     image_url, image_prompt, image_model)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                RETURNING id
            """, (
                campaign_id, attempt_number,
                email_subject, email_preheader, email_body, email_cta,
                json.dumps(email_subject_variants) if email_subject_variants else None,
                instagram_caption,
                json.dumps(instagram_hashtags) if instagram_hashtags else None,
                instagram_visual_direction,
                linkedin_headline, linkedin_body, linkedin_cta,
                twitter_post,
                whatsapp_message, send_time_recommendation,
                chosen_discount_pct, agent_reasoning,
                json.dumps(strategy_json) if strategy_json else None,
                json.dumps(trending_hooks_used) if trending_hooks_used else None,
                image_url, image_prompt, image_model
            ))
            asset_id = cur.fetchone()["id"]
        conn.commit()
    return asset_id

def get_latest_assets(campaign_id: int) -> dict:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM generated_assets
                WHERE campaign_id = %s
                ORDER BY created_at DESC LIMIT 1
            """, (campaign_id,))
            row = cur.fetchone()
            return dict(row) if row else {}


# ════════════════════════════════════════════════════════════════
# RISK ASSESSMENTS
# ════════════════════════════════════════════════════════════════

def save_risk_assessment(
    asset_id: int,
    campaign_id: int,
    brand_safety_score: int,
    brand_safety_note: str,
    legal_risk_score: int,
    legal_risk_note: str,
    cultural_sensitivity_score: int,
    cultural_sensitivity_note: str,
    overall_recommendation: str,
    green_light: bool,
    decision_reason: str
) -> int:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO risk_assessments
                    (asset_id, campaign_id,
                     brand_safety_score, brand_safety_note,
                     legal_risk_score, legal_risk_note,
                     cultural_sensitivity_score, cultural_sensitivity_note,
                     overall_recommendation, green_light, decision_reason)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                RETURNING id
            """, (
                asset_id, campaign_id,
                brand_safety_score, brand_safety_note,
                legal_risk_score, legal_risk_note,
                cultural_sensitivity_score, cultural_sensitivity_note,
                overall_recommendation, green_light, decision_reason
            ))
            risk_id = cur.fetchone()["id"]
        conn.commit()
    return risk_id

def get_latest_risk(campaign_id: int) -> dict:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM risk_assessments
                WHERE campaign_id = %s
                ORDER BY created_at DESC LIMIT 1
            """, (campaign_id,))
            row = cur.fetchone()
            return dict(row) if row else {}


# ════════════════════════════════════════════════════════════════
# PENDING APPROVALS
# ════════════════════════════════════════════════════════════════

def create_pending_approval(
    campaign_id: int,
    asset_id: int,
    risk_id: int
) -> int:
    from backend.config import APPROVAL_EXPIRY_HOURS
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO pending_approvals
                    (campaign_id, asset_id, risk_id, status, expires_at)
                VALUES (%s, %s, %s, 'pending',
                        NOW() + INTERVAL '%s hours')
                RETURNING id
            """, (campaign_id, asset_id, risk_id, APPROVAL_EXPIRY_HOURS))
            approval_id = cur.fetchone()["id"]
        conn.commit()
    return approval_id

def get_pending_approval(approval_id: int) -> dict:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT pa.*, ga.*, ra.brand_safety_score,
                       ra.legal_risk_score, ra.cultural_sensitivity_score,
                       ra.green_light, ra.overall_recommendation
                FROM pending_approvals pa
                JOIN generated_assets ga ON pa.asset_id = ga.id
                JOIN risk_assessments ra ON pa.risk_id = ra.id
                WHERE pa.id = %s
            """, (approval_id,))
            row = cur.fetchone()
            return dict(row) if row else {}

def resolve_approval(
    approval_id: int,
    status: str,              # "approved" | "approved_with_edits" | "rejected"
    decided_by: str,
    human_edits: dict = None,
    rejection_reason: str = ""
) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE pending_approvals
                SET status = %s,
                    human_edits = %s,
                    rejection_reason = %s,
                    decided_by = %s,
                    decided_at = NOW()
                WHERE id = %s
            """, (
                status,
                json.dumps(human_edits) if human_edits else None,
                rejection_reason,
                decided_by,
                approval_id
            ))
        conn.commit()


# ════════════════════════════════════════════════════════════════
# PUBLISHED POSTS
# ════════════════════════════════════════════════════════════════

def save_published_post(
    campaign_id: int,
    approval_id: int,
    channel: str,
    final_subject: str = None,
    final_body: str = None,
    final_caption: str = None,
    final_hashtags: list = None,
    sendgrid_message_id: str = None,
    external_post_id: str = None,
    send_status: str = "sent",
    recipient_count: int = 1,
    recipient_email: str = None
) -> int:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO published_posts
                    (campaign_id, approval_id, channel,
                     final_subject, final_body, final_caption, final_hashtags,
                     sendgrid_message_id, external_post_id,
                     send_status, recipient_count, recipient_email)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                RETURNING id
            """, (
                campaign_id, approval_id, channel,
                final_subject, final_body, final_caption,
                json.dumps(final_hashtags or []),
                sendgrid_message_id, external_post_id,
                send_status, recipient_count, recipient_email
            ))
            post_id = cur.fetchone()["id"]
        conn.commit()
    return post_id


# ════════════════════════════════════════════════════════════════
# PERFORMANCE SNAPSHOTS
# ════════════════════════════════════════════════════════════════

def add_performance_snapshot(
    campaign_id: int,
    ctr: float,
    open_rate: float = 0.0,
    roas: float = 0.0,
    click_count: int = 0,
    attempt_number: int = 1,
    phase: str = "attempt_1",
    healed: bool = False,
    note: str = "",
    post_id: int = None
) -> int:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO performance_snapshots
                    (campaign_id, post_id, attempt_number,
                     ctr, open_rate, roas, click_count,
                     phase, healed, note)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                RETURNING id
            """, (
                campaign_id, post_id, attempt_number,
                ctr, open_rate, roas, click_count,
                phase, healed, note
            ))
            snap_id = cur.fetchone()["id"]
        conn.commit()
    return snap_id

def get_performance_snapshots(campaign_id: int) -> list:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT ctr, open_rate, roas, phase, healed, note, recorded_at
                FROM performance_snapshots
                WHERE campaign_id = %s
                ORDER BY recorded_at ASC
            """, (campaign_id,))
            return [dict(r) for r in cur.fetchall()]

def is_campaign_healed(campaign_id: int, ctr_threshold: float) -> bool:
    """Analytics agent calls this to check if latest CTR is above threshold."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT ctr FROM performance_snapshots
                WHERE campaign_id = %s
                ORDER BY recorded_at DESC LIMIT 1
            """, (campaign_id,))
            row = cur.fetchone()
            if not row:
                return False
            return row["ctr"] >= ctr_threshold


# ════════════════════════════════════════════════════════════════
# TRENDS
# ════════════════════════════════════════════════════════════════

def save_trend(
    company_id: int,
    source: str,
    category: str,
    trend_text: str,
    hashtags: list,
    sentiment: str = "positive",
    volume_score: int = 0,
    relevance_score: float = 0.5
) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO trends
                    (company_id, source, category, trend_text,
                     hashtags, sentiment, volume_score, relevance_score)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                company_id, source, category, trend_text,
                json.dumps(hashtags), sentiment, volume_score, relevance_score
            ))
        conn.commit()

def get_top_trends(
    company_id: int,
    category: str = None,
    limit: int = 10
) -> list:
    """Strategy Agent calls this before generating content."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            query = """
                SELECT trend_text, hashtags, source,
                       volume_score, relevance_score
                FROM trends
                WHERE (company_id = %s OR company_id IS NULL)
                  AND scraped_at > NOW() - INTERVAL '24 hours'
            """
            params = [company_id]
            if category:
                query += " AND category = %s"
                params.append(category)
            query += " ORDER BY relevance_score DESC, volume_score DESC LIMIT %s"
            params.append(limit)
            cur.execute(query, params)
            return [dict(r) for r in cur.fetchall()]


# ════════════════════════════════════════════════════════════════
# CAMPAIGN MEMORY
# ════════════════════════════════════════════════════════════════

def save_campaign_memory(
    company_id: int,
    campaign_id: int,
    what_worked: str,
    what_failed: str,
    winning_tone: str,
    winning_visual: str,
    top_hashtags: list,
    market_trends_json: dict,
    final_ctr: float,
    attempts_needed: int,
    recommendations: str,
    festival_tag: str = None,
    season: str = None
) -> None:
    import datetime
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO campaign_memory
                    (company_id, campaign_id, festival_tag, season, year,
                     what_worked, what_failed, winning_tone, winning_visual,
                     top_hashtags, market_trends_json, final_ctr,
                     attempts_needed, recommendations)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                company_id, campaign_id, festival_tag, season,
                datetime.datetime.now().year,
                what_worked, what_failed, winning_tone, winning_visual,
                json.dumps(top_hashtags), json.dumps(market_trends_json),
                final_ctr, attempts_needed, recommendations
            ))
        conn.commit()

def get_campaign_memory(
    company_id: int,
    festival_tag: str = None
) -> list:
    """Strategy Agent reads this for relevant past learnings."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            query = """
                SELECT * FROM campaign_memory
                WHERE company_id = %s
            """
            params = [company_id]
            if festival_tag:
                query += " AND festival_tag = %s"
                params.append(festival_tag)
            query += " ORDER BY created_at DESC LIMIT 5"
            cur.execute(query, params)
            return [dict(r) for r in cur.fetchall()]


# ════════════════════════════════════════════════════════════════
# CAMPAIGN HISTORY
# ════════════════════════════════════════════════════════════════

def log_event(
    campaign_id: int,
    event_type: str,
    note: str = "",
    triggered_by: str = "system",
    metadata: dict = None
) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO campaign_history
                    (campaign_id, event_type, note, triggered_by, metadata)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                campaign_id, event_type, note, triggered_by,
                json.dumps(metadata or {})
            ))
        conn.commit()

def get_campaign_history(campaign_id: int) -> list:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT event_type, note, triggered_by, metadata, created_at
                FROM campaign_history
                WHERE campaign_id = %s
                ORDER BY created_at ASC
            """, (campaign_id,))
            return [dict(r) for r in cur.fetchall()]


# ════════════════════════════════════════════════════════════════
# PROMPT REQUESTS
# Every manual user prompt logged here
# ════════════════════════════════════════════════════════════════

def log_prompt_request(
    company_id: int,
    user_prompt: str
) -> int:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO prompt_requests
                    (company_id, user_prompt, status)
                VALUES (%s, %s, 'received')
                RETURNING id
            """, (company_id, user_prompt))
            prompt_id = cur.fetchone()["id"]
        conn.commit()
    return prompt_id

def update_prompt_request(
    prompt_id: int,
    campaign_id: int,
    parsed_intent: str,
    status: str = "processing"
) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE prompt_requests
                SET campaign_id = %s, parsed_intent = %s,
                    status = %s, processed_at = NOW()
                WHERE id = %s
            """, (campaign_id, parsed_intent, status, prompt_id))
        conn.commit()


# ════════════════════════════════════════════════════════════════
# COST TRACKING (for UI cost panel)
# ════════════════════════════════════════════════════════════════

def get_total_cost(campaign_id: int) -> dict:
    """Returns running totals for the cost tracker panel."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    COUNT(*)            AS api_calls,
                    SUM(tokens_used)    AS total_tokens,
                    SUM(cost_usd)       AS total_cost_usd,
                    SUM(cost_usd) * 84  AS total_cost_inr
                FROM reasoning_log
                WHERE campaign_id = %s
            """, (campaign_id,))
            row = cur.fetchone()
            return dict(row) if row else {
                "api_calls": 0, "total_tokens": 0,
                "total_cost_usd": 0, "total_cost_inr": 0
            }


# ════════════════════════════════════════════════════════════════
# NEW HELPER FUNCTIONS (Required by team)
# ════════════════════════════════════════════════════════════════

def get_current_attempt(campaign_id: int) -> int:
    """Return the current heal_attempts for a campaign."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT heal_attempts FROM campaigns WHERE id = %s", (campaign_id,))
            row = cur.fetchone()
            return row["heal_attempts"] if row else 1

def save_reasoning(agent: str, thought: str, campaign_id: int):
    """Wrapper around log_reasoning for the team's interface."""
    attempt = get_current_attempt(campaign_id)
    return log_reasoning(
        campaign_id=campaign_id,
        attempt_number=attempt,
        agent_name=agent,
        status="completed",
        reasoning_summary=thought,
        output=thought,
        tokens_used=0,
        cost_usd=0.0,
        model_used="gemini-2.0-flash",
        duration_ms=0
    )

def get_trends(limit: int = 10) -> list:
    """Return a list of trend texts from the last 12 hours, sorted by relevance."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT trend_text FROM trends
                WHERE scraped_at > NOW() - INTERVAL '12 hours'
                ORDER BY relevance_score DESC
                LIMIT %s
            """, (limit,))
            return [row["trend_text"] for row in cur.fetchall()]

def get_memory(festival_tag: str, year: int) -> dict:
    """Return the most recent memory for given festival_tag and year."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM campaign_memory
                WHERE festival_tag = %s AND year = %s
                ORDER BY created_at DESC
                LIMIT 1
            """, (festival_tag, year))
            row = cur.fetchone()
            return dict(row) if row else {}

def save_memory(campaign_id: int, festival_tag: str, mortem: dict):
    """Store a campaign memory entry from the analytics agent."""
    return save_campaign_memory(
        company_id=1,  # Nykaa (adjust if multiple companies)
        campaign_id=campaign_id,
        festival_tag=festival_tag,
        season=mortem.get("season"),
        what_worked=mortem.get("what_worked", ""),
        what_failed=mortem.get("what_failed", ""),
        winning_tone=mortem.get("winning_tone", ""),
        winning_visual=mortem.get("winning_visual", ""),
        top_hashtags=mortem.get("top_hashtags", []),
        market_trends_json=mortem.get("market_trends_json", {}),
        final_ctr=mortem.get("final_ctr", 0.0),
        attempts_needed=mortem.get("attempts_needed", 1),
        recommendations=mortem.get("recommendations", "")
    )

def save_output(campaign_id: int, attempt: int, content_dict: dict):
    """Wrapper around save_generated_assets for the team's interface."""
    return save_generated_assets(
        campaign_id=campaign_id,
        attempt_number=attempt,
        email_subject=content_dict.get("email_subject"),
        email_preheader=content_dict.get("email_preheader"),
        email_body=content_dict.get("email_body"),
        email_cta=content_dict.get("email_cta"),
        email_subject_variants=content_dict.get("email_subject_variants"),
        instagram_caption=content_dict.get("instagram_caption"),
        instagram_hashtags=content_dict.get("instagram_hashtags"),
        instagram_visual_direction=content_dict.get("instagram_visual_direction"),
        linkedin_headline=content_dict.get("linkedin_headline"),
        linkedin_body=content_dict.get("linkedin_body"),
        linkedin_cta=content_dict.get("linkedin_cta"),
        twitter_post=content_dict.get("twitter_post"),
        whatsapp_message=content_dict.get("whatsapp_message"),
        send_time_recommendation=content_dict.get("send_time_recommendation"),
        chosen_discount_pct=content_dict.get("chosen_discount_pct", 0),
        agent_reasoning=content_dict.get("agent_reasoning"),
        strategy_json=content_dict.get("strategy_json"),
        trending_hooks_used=content_dict.get("trending_hooks_used"),
        image_url=content_dict.get("image_url"),
        image_prompt=content_dict.get("image_prompt"),
        image_model=content_dict.get("image_model", "dall-e-3")
    )

def get_campaign_id_from_asset(asset_id: int) -> int:
    """Helper to retrieve campaign_id from generated_assets."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT campaign_id FROM generated_assets WHERE id = %s", (asset_id,))
            row = cur.fetchone()
            return row["campaign_id"] if row else None

def save_risk(output_id: int, scores_dict: dict):
    """Wrapper around save_risk_assessment for the team's interface."""
    campaign_id = get_campaign_id_from_asset(output_id)
    if not campaign_id:
        raise ValueError(f"Asset {output_id} not found")
    return save_risk_assessment(
        asset_id=output_id,
        campaign_id=campaign_id,
        brand_safety_score=scores_dict.get("brand_safety", 0),
        brand_safety_note=scores_dict.get("flag_reason", ""),
        legal_risk_score=scores_dict.get("legal_risk", 0),
        legal_risk_note="",
        cultural_sensitivity_score=scores_dict.get("cultural_sensitivity", 0),
        cultural_sensitivity_note="",
        overall_recommendation="APPROVE" if scores_dict.get("green_light") else "REJECT",
        green_light=scores_dict.get("green_light", False),
        decision_reason=scores_dict.get("explanation", "")
    )

def save_post_performance(post_id: int, perf_dict: dict):
    """Wrapper around add_performance_snapshot for the team's interface."""
    # Get campaign_id from published_posts
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT campaign_id FROM published_posts WHERE id = %s", (post_id,))
            row = cur.fetchone()
            if not row:
                return None
            campaign_id = row["campaign_id"]
    attempt = get_current_attempt(campaign_id)
    return add_performance_snapshot(
        campaign_id=campaign_id,
        ctr=perf_dict.get("new_ctr", 0.0),
        open_rate=perf_dict.get("new_open_rate", 0.0),
        roas=0.0,
        click_count=perf_dict.get("clicks", 0),
        attempt_number=attempt,
        phase="healed" if perf_dict.get("healed") else "attempt",
        healed=perf_dict.get("healed", False),
        note="",
        post_id=post_id
    )

def get_post_performance(campaign_id: int) -> dict:
    """Return the latest performance snapshot for a campaign."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM performance_snapshots
                WHERE campaign_id = %s
                ORDER BY recorded_at DESC
                LIMIT 1
            """, (campaign_id,))
            row = cur.fetchone()
            return dict(row) if row else {}

def log_api_cost(campaign_id: int, agent: str, tokens: int, cost: float):
    """Log token usage and cost for a specific agent call."""
    attempt = get_current_attempt(campaign_id)
    return log_reasoning(
        campaign_id=campaign_id,
        attempt_number=attempt,
        agent_name=agent,
        status="completed",
        reasoning_summary=f"API call: {tokens} tokens, ${cost:.4f}",
        output="",
        tokens_used=tokens,
        cost_usd=cost,
        model_used="unknown",
        duration_ms=0
    )

def reset_demo():
    """Reset the database to initial seed state (for exhibition)."""
    # Determine project root
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)  # one level up from backend/db/
    seed_script = os.path.join(project_root, "data", "seed_nykaa.py")
    # Truncate all tables
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SET session_replication_role = replica;")
            tables = [
                "campaign_history", "prompt_requests", "performance_snapshots",
                "published_posts", "pending_approvals", "risk_assessments",
                "generated_assets", "reasoning_log", "seasonal_campaigns",
                "festival_calendar", "scrape_logs", "trends", "campaign_offers",
                "campaigns", "audience_segments", "brand_profiles", "campaign_memory",
                "companies", "customers"
            ]
            for t in tables:
                cur.execute(f"TRUNCATE TABLE {t} RESTART IDENTITY CASCADE;")
            cur.execute("SET session_replication_role = DEFAULT;")
        conn.commit()
    # Re‑run the seed script
    subprocess.run(["python", seed_script], check=True, cwd=project_root)
    print("[DB] Demo reset complete.")