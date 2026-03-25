"""
scheduler/email_scheduler.py
-----------------------------
APScheduler-based event-driven email campaign scheduler.

How it works:
    - Runs a daily job (default: 08:00 system local time)
    - Checks CAMPAIGN_EVENTS in campaign_events.py for due campaigns
    - Tracks "already sent" state in outputs/scheduler_state.json
    - For each due campaign that hasn't been sent yet:
        → Runs the full pipeline: Content Agent → Risk Check → SMTP Send
    - Never sends the same campaign twice

Usage:
    # Start the scheduler daemon (blocks — run in a terminal or as a service)
    python scheduler/email_scheduler.py

    # Or via main.py:
    python main.py --schedule

    # Run immediately (no wait) — great for testing:
    python scheduler/email_scheduler.py --run-now
"""

import sys
import os
import json
import logging
import argparse
from datetime import datetime, date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()

from apscheduler.schedulers.blocking import BlockingScheduler

from scheduler.campaign_events import get_due_campaigns

logger = logging.getLogger("email_scheduler")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  [Scheduler]  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# State file tracks which campaigns have already been sent
_STATE_DIR  = os.path.join(os.path.dirname(__file__), "..", "outputs")
_STATE_FILE = os.path.join(_STATE_DIR, "scheduler_state.json")


# ── State management ──────────────────────────────────────────────────────────

def _load_state() -> dict:
    """Load the scheduler state from disk."""
    if os.path.exists(_STATE_FILE):
        try:
            with open(_STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {"sent_campaigns": []}


def _save_state(state: dict) -> None:
    """Persist scheduler state to disk."""
    os.makedirs(_STATE_DIR, exist_ok=True)
    with open(_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def _mark_sent(campaign_id: str) -> None:
    """Record a campaign as sent in the state file."""
    state = _load_state()
    if campaign_id not in state["sent_campaigns"]:
        state["sent_campaigns"].append(campaign_id)
        state[f"sent_at_{campaign_id}"] = datetime.now().isoformat()
        _save_state(state)


def _already_sent(campaign_id: str) -> bool:
    """Return True if this campaign has already been dispatched."""
    state = _load_state()
    return campaign_id in state.get("sent_campaigns", [])


# ── Pipeline execution ────────────────────────────────────────────────────────

def _run_pipeline_for_campaign(event: dict) -> dict:
    """
    Run the full Content → Risk → SMTP pipeline for a single campaign event.
    Imported here (not at module level) to keep startup fast.
    """
    # Import inside function to avoid circular imports at module load time
    from crews.marketing_crew import run_email_campaign_pipeline

    campaign_id = event["campaign_id"]
    brief       = event["brief"]
    name        = event["name"]

    logger.info("▶  Running pipeline for: %s (campaign_id=%s)", name, campaign_id)

    try:
        result = run_email_campaign_pipeline(
            brief=brief,
            campaign_id=campaign_id,
        )
        logger.info(
            "✅  Campaign '%s' complete — sent: %d, failed: %d, blocked: %s",
            name,
            result.get("sent", 0),
            result.get("failed", 0),
            result.get("blocked", False),
        )
        return result
    except Exception as exc:   # noqa: BLE001 — keep scheduler alive on one failure
        logger.error("❌  Pipeline failed for '%s': %s", name, exc, exc_info=True)
        return {"error": str(exc), "blocked": False, "sent": 0, "failed": 0}


# ── Daily job ─────────────────────────────────────────────────────────────────

def daily_campaign_check() -> None:
    """
    Called once per day by APScheduler.
    Checks for due campaigns and runs the pipeline for any not yet sent.
    """
    today = date.today()
    logger.info("🗓️   Daily check — today is %s", today.isoformat())

    due = get_due_campaigns(reference_date=today)
    if not due:
        logger.info("No campaigns due today.")
        return

    logger.info("Found %d due campaign(s).", len(due))
    for event in due:
        cid = event["id"]
        if _already_sent(cid):
            logger.info("   ⏭  Skipping '%s' — already sent.", event["name"])
            continue

        result = _run_pipeline_for_campaign(event)

        # Mark as sent even if SMTP failed, to avoid hammering recipients
        # with retries. User can re-run manually if needed.
        if not result.get("error"):
            _mark_sent(cid)
            logger.info("   ✅  Marked '%s' as sent.", event["name"])
        else:
            logger.error(
                "   ⚠️   NOT marking '%s' as sent due to pipeline error. "
                "It will retry tomorrow.", event["name"]
            )


# ── Entry point ───────────────────────────────────────────────────────────────

def start_scheduler(run_hour: int = 8, run_minute: int = 0) -> None:
    """
    Start the APScheduler blocking scheduler.
    Runs the daily check job every day at run_hour:run_minute (local time).

    Args:
        run_hour   : hour to run (0–23), default 8 (8 AM)
        run_minute : minute to run (0–59), default 0
    """
    scheduler = BlockingScheduler(timezone="Asia/Kolkata")
    scheduler.add_job(
        daily_campaign_check,
        trigger="cron",
        hour=run_hour,
        minute=run_minute,
        id="daily_campaign_check",
        name="Daily Campaign Email Check",
        replace_existing=True,
    )

    logger.info(
        "📅  Scheduler started. Daily check at %02d:%02d IST. "
        "Press Ctrl+C to stop.",
        run_hour, run_minute,
    )

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Marketing AI Crew — Email Scheduler")
    parser.add_argument(
        "--run-now",
        action="store_true",
        help="Run the campaign check immediately (don't wait for scheduled time)",
    )
    parser.add_argument("--hour",   type=int, default=8,  help="Hour to run daily job (0-23), default 8")
    parser.add_argument("--minute", type=int, default=0,  help="Minute to run daily job (0-59), default 0")
    args = parser.parse_args()

    if args.run_now:
        logger.info("Running campaign check NOW (--run-now flag used)…")
        daily_campaign_check()
    else:
        start_scheduler(run_hour=args.hour, run_minute=args.minute)
