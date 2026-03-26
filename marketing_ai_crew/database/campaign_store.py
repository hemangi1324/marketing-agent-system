"""
database/campaign_store.py
---------------------------
High-level campaign CRUD operations built on top of db_manager.

This is the single interface all agents use to persist and retrieve
campaign data. It ensures consistent data formats and centralises
all campaign-related DB logic.

Collections used:
  campaigns    — full CampaignState dicts (one record per campaign_id)
  agent_steps  — per-step audit log entries (append-only)
  risk_scores  — risk result per campaign (keyed by campaign_id)
  analytics    — analytics result per campaign (keyed by campaign_id)
"""

import logging
from typing import Optional, List, Dict, Any

from database import db_manager as db

logger = logging.getLogger("campaign_store")

# ── Campaign CRUD ─────────────────────────────────────────────────────────────

def save_campaign(campaign_id: int, state_dict: Dict[str, Any]) -> None:
    """
    Persist a full CampaignState snapshot to the database.
    Called by the orchestrator after every agent step.

    Args:
        campaign_id : unique campaign identifier
        state_dict  : CampaignState.model_dump() output
    """
    db.write("campaigns", str(campaign_id), state_dict)
    logger.info("Campaign %s saved to DB.", campaign_id)


def load_campaign(campaign_id: int) -> Optional[Dict[str, Any]]:
    """
    Load a campaign state from the database.

    Returns:
        dict if found, None otherwise
    """
    record = db.read("campaigns", str(campaign_id))
    if record:
        logger.info("Campaign %s loaded from DB.", campaign_id)
    else:
        logger.debug("Campaign %s not found in DB.", campaign_id)
    return record


def get_campaign_history(n: int = 5) -> List[Dict[str, Any]]:
    """
    Return the n most recently completed campaigns.
    Used by the Strategy Agent for historical context.

    Returns:
        list of campaign state dicts, most recent first
    """
    return db.get_recent("campaigns", n=n)


def campaign_exists(campaign_id: int) -> bool:
    """Check if a campaign with this ID is already in the DB (idempotency check)."""
    return db.exists("campaigns", str(campaign_id))


# ── Agent Step Logging ────────────────────────────────────────────────────────

def log_agent_step(
    campaign_id: int,
    agent_name: str,
    status: str,
    output_summary: str = None,
    error: str = None,
) -> None:
    """
    Append a single agent step to the audit log.
    This is an append-only log — every step across all campaigns is recorded.

    Args:
        campaign_id    : campaign this step belongs to
        agent_name     : e.g. 'strategy_agent', 'risk_agent'
        status         : 'success' | 'failed' | 'skipped'
        output_summary : brief description of what the agent produced
        error          : error message if status is 'failed'
    """
    entry = {
        "campaign_id":    campaign_id,
        "agent_name":     agent_name,
        "status":         status,
        "output_summary": output_summary,
        "error":          error,
    }
    db.append_log("agent_steps", entry)
    logger.debug("Step logged — campaign=%s agent=%s status=%s", campaign_id, agent_name, status)


# ── Risk Score Storage ────────────────────────────────────────────────────────

def save_risk_result(campaign_id: int, risk_dict: Dict[str, Any]) -> None:
    """Save the risk agent's output for a campaign."""
    db.write("risk_scores", str(campaign_id), risk_dict)


def load_risk_result(campaign_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve the risk result for a campaign."""
    return db.read("risk_scores", str(campaign_id))


# ── Analytics Storage ─────────────────────────────────────────────────────────

def save_analytics_result(campaign_id: int, analytics_dict: Dict[str, Any]) -> None:
    """Save the analytics agent's output for a campaign."""
    db.write("analytics", str(campaign_id), analytics_dict)


def load_analytics_result(campaign_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve the analytics result for a campaign."""
    return db.read("analytics", str(campaign_id))


# ── Context Builder ───────────────────────────────────────────────────────────

def build_historical_context(festival_tag: str = None, n: int = 3) -> str:
    """
    Build a human-readable historical context string from recent campaigns.
    Injected into the Strategy Agent's task to inform its decisions.

    Args:
        festival_tag : only include campaigns matching this tag (optional)
        n            : max number of past campaigns to include

    Returns:
        Formatted string of past campaign insights.
    """
    history = get_campaign_history(n=10)

    if festival_tag:
        history = [
            c for c in history
            if c.get("festival_tag") == festival_tag
        ]

    history = history[:n]

    if not history:
        return "No previous campaigns found for this context."

    lines = ["=== Historical Campaign Insights ==="]
    for i, campaign in enumerate(history, 1):
        cid = campaign.get("campaign_id", "?")
        brief = campaign.get("brief", "N/A")[:80]
        analytics = campaign.get("analytics_output") or {}
        pm = analytics.get("post_mortem", {})
        green = campaign.get("green_light")
        lines.append(
            f"\n[Campaign #{cid}] Brief: {brief}\n"
            f"  Risk Green Light : {green}\n"
            f"  What Worked      : {pm.get('what_worked', 'N/A')}\n"
            f"  Recommendation   : {pm.get('recommendation', 'N/A')}"
        )
    lines.append("=== End of History ===")
    return "\n".join(lines)
