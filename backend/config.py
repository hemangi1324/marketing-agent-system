"""
config.py
---------
All environment variables and constants in one place.
Never hardcode values anywhere else — always import from here.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Database ──────────────────────────────────────────────────
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:password@localhost:5432/marketing_db"
)

# ── LLM ───────────────────────────────────────────────────────
GEMINI_API_KEY      = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL_SMART  = "gemini-2.0-flash"          # strategy, risk
GEMINI_MODEL_FAST   = "gemini-2.0-flash"           # content, execution

# ── Integrations ──────────────────────────────────────────────
SENDGRID_API_KEY    = os.getenv("SENDGRID_API_KEY", "")
SENDGRID_FROM_EMAIL = os.getenv("SENDGRID_FROM_EMAIL", "demo@yourproject.com")
TEST_INBOX_EMAIL    = os.getenv("TEST_INBOX_EMAIL", "")   # where demo emails go

REDDIT_CLIENT_ID     = os.getenv("REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "")
YOUTUBE_API_KEY      = os.getenv("YOUTUBE_API_KEY", "")

SLACK_WEBHOOK_URL   = os.getenv("SLACK_WEBHOOK_URL", "")   # escalation alerts

# ── Monitor thresholds ────────────────────────────────────────
# Below these values = campaign is failing = trigger fires
CTR_THRESHOLD_EMAIL     = float(os.getenv("CTR_THRESHOLD_EMAIL", "1.0"))
CTR_THRESHOLD_INSTAGRAM = float(os.getenv("CTR_THRESHOLD_INSTAGRAM", "0.8"))
OPEN_RATE_THRESHOLD     = float(os.getenv("OPEN_RATE_THRESHOLD", "15.0"))
ROAS_THRESHOLD          = float(os.getenv("ROAS_THRESHOLD", "1.5"))

# ── Pipeline settings ─────────────────────────────────────────
MAX_HEAL_ATTEMPTS       = int(os.getenv("MAX_HEAL_ATTEMPTS", "3"))
MONITOR_INTERVAL_SECS   = int(os.getenv("MONITOR_INTERVAL_SECS", "60"))
SCRAPER_INTERVAL_HOURS  = int(os.getenv("SCRAPER_INTERVAL_HOURS", "6"))
APPROVAL_EXPIRY_HOURS   = int(os.getenv("APPROVAL_EXPIRY_HOURS", "24"))

# ── Risk gate thresholds ──────────────────────────────────────
RISK_GREEN_LIGHT_MIN    = int(os.getenv("RISK_GREEN_LIGHT_MIN", "7"))
RISK_HARD_BLOCK_MAX     = int(os.getenv("RISK_HARD_BLOCK_MAX", "4"))
# Score >= GREEN_LIGHT_MIN on ALL dimensions → proceed
# Any score <= HARD_BLOCK_MAX → block immediately, Slack alert

# ── Demo mode ─────────────────────────────────────────────────
DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"
# In demo mode: performance snapshots use simulated data,
# monitor interval is 5s instead of 60s
if DEMO_MODE:
    MONITOR_INTERVAL_SECS = 5
