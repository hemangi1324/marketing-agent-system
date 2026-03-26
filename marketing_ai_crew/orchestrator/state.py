"""
orchestrator/state.py
----------------------
SharedState manages the CampaignState Pydantic model throughout a pipeline run.

Responsibilities:
  - Central container for all agent outputs
  - Persists state to DB after every agent step (crash-safe)
  - Provides context strings for agent task descriptions
  - Tracks delegation count (loop prevention)
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any

from schemas.campaign import CampaignState, AgentStepLog
from database import campaign_store

logger = logging.getLogger("shared_state")


class SharedState:
    """
    Wrapper around CampaignState that handles:
    - DB persistence after every update
    - Context string generation for agent task descriptions
    - Step audit logging
    - Loop/delegation control
    """

    def __init__(self, campaign_id: int, brief: str,
                 festival_tag: str = None, target_audience: str = None):
        self._state = CampaignState(
            campaign_id=campaign_id,
            brief=brief,
            festival_tag=festival_tag,
            target_audience=target_audience,
        )
        # Load historical context from DB immediately
        self._state.historical_context = campaign_store.build_historical_context(
            festival_tag=festival_tag, n=3
        )
        logger.info("SharedState initialised for campaign %s", campaign_id)

    # ── Accessors ─────────────────────────────────────────────────────────────

    @property
    def campaign_id(self) -> int:
        return self._state.campaign_id

    @property
    def brief(self) -> str:
        return self._state.brief

    @property
    def festival_tag(self) -> Optional[str]:
        return self._state.festival_tag

    @property
    def green_light(self) -> Optional[bool]:
        return self._state.green_light

    @property
    def pipeline_blocked(self) -> bool:
        return self._state.pipeline_blocked

    def can_delegate(self) -> bool:
        return self._state.can_delegate()

    def increment_delegation(self):
        self._state.delegation_count += 1

    # ── Update methods (one per agent) ────────────────────────────────────────

    def update_strategy(self, strategy_dict: Dict[str, Any]):
        """Called after Strategy Agent completes."""
        self._state.strategy_output = strategy_dict
        self._log_step("strategy_agent", "success",
                       strategy_dict.get("campaign_theme", "")[:100])
        self._persist()

    def update_content(self, content_dict: Dict[str, Any]):
        """Called after Content Agent completes."""
        self._state.content_output = content_dict
        subject = (content_dict.get("email_content") or {}).get("subject", "")
        self._log_step("content_agent", "success", f"Subject: {subject[:80]}")
        self._persist()

    def update_risk(self, risk_dict: Dict[str, Any]):
        """Called after Risk Agent completes."""
        self._state.risk_output = risk_dict
        self._state.green_light = risk_dict.get("green_light", False)
        if not self._state.green_light:
            self._state.pipeline_blocked = True
            self._state.block_reason = risk_dict.get("flag_reason", "Risk check failed")
        self._log_step(
            "risk_agent",
            "success" if self._state.green_light else "failed",
            f"green_light={self._state.green_light}"
        )
        self._persist()

    def update_communication(self, comm_dict: Dict[str, Any]):
        """Called after Communication Layer completes."""
        self._state.communication_output = comm_dict
        self._log_step("communication_layer", "success",
                       f"sent={comm_dict.get('emails_sent', 0)}")
        self._persist()

    def update_analytics(self, analytics_dict: Dict[str, Any]):
        """Called after Analytics Agent completes."""
        self._state.analytics_output = analytics_dict
        self._state.pipeline_complete = True
        summary = analytics_dict.get("summary_string", "Analytics complete")
        self._log_step("analytics_agent", "success", summary[:100])
        self._persist()

    def mark_failed(self, agent_name: str, error: str):
        """Mark an agent step as failed in the state and audit log."""
        self._log_step(agent_name, "failed", error=error)
        self._persist()

    # ── Context for agents ────────────────────────────────────────────────────

    def to_context_string(self) -> str:
        """Formatted state string injected into agent task descriptions."""
        return self._state.to_context_string()

    def get_historical_context(self) -> str:
        return self._state.historical_context or "No historical context available."

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return self._state.model_dump()

    def is_complete(self) -> bool:
        return self._state.pipeline_complete

    def is_blocked(self) -> bool:
        return self._state.pipeline_blocked

    # ── Internal ──────────────────────────────────────────────────────────────

    def _log_step(self, agent_name: str, status: str,
                  output_summary: str = None, error: str = None):
        now = datetime.now().isoformat()
        log = AgentStepLog(
            agent_name=agent_name,
            started_at=now,
            completed_at=now,
            status=status,
            output_summary=output_summary,
            error=error,
        )
        self._state.step_logs.append(log)
        # Persist to DB audit log
        campaign_store.log_agent_step(
            campaign_id=self._state.campaign_id,
            agent_name=agent_name,
            status=status,
            output_summary=output_summary,
            error=error,
        )

    def _persist(self):
        """Save the full state snapshot to the DB after every update."""
        try:
            campaign_store.save_campaign(self._state.campaign_id, self._state.model_dump())
        except Exception as exc:
            logger.warning("State persistence failed (non-fatal): %s", exc)
