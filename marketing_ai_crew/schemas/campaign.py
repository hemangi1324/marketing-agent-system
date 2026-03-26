"""
schemas/campaign.py
Core campaign lifecycle schemas. CampaignState is the shared state object
that flows through the entire orchestrator pipeline.
"""

from __future__ import annotations
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field


class CampaignInput(BaseModel):
    """Input provided by the user to kick off a campaign."""
    brief: str = Field(..., description="Campaign brief / objective")
    campaign_id: int = Field(..., description="Unique numeric campaign identifier")
    festival_tag: Optional[str] = Field(None, description="Optional festival context e.g. 'diwali'")
    target_audience: Optional[str] = Field(None, description="Target audience description")
    mode: str = Field("sequential", description="Execution mode: 'sequential' or 'dynamic'")


class AgentStepLog(BaseModel):
    """Audit record for a single agent execution step."""
    agent_name: str
    started_at: str
    completed_at: Optional[str] = None
    status: str = "pending"          # pending | success | failed | skipped
    output_summary: Optional[str] = None
    error: Optional[str] = None


class CampaignState(BaseModel):
    """
    Shared mutable state object passed between every agent in the pipeline.
    Each agent reads from this, does its job, then writes its output back.
    The orchestrator passes this as context when building task descriptions.
    """
    # ── Identity ──────────────────────────────────────────────────────────────
    campaign_id: int
    brief: str
    festival_tag: Optional[str] = None
    target_audience: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())

    # ── Agent outputs (populated progressively) ───────────────────────────────
    strategy_output: Optional[Dict[str, Any]] = None      # from strategy_agent
    content_output: Optional[Dict[str, Any]] = None       # from content_agent
    risk_output: Optional[Dict[str, Any]] = None          # from risk_agent
    communication_output: Optional[Dict[str, Any]] = None # from comms layer
    analytics_output: Optional[Dict[str, Any]] = None     # from analytics_agent

    # ── Pipeline control ──────────────────────────────────────────────────────
    green_light: Optional[bool] = None    # set by risk agent
    pipeline_complete: bool = False
    pipeline_blocked: bool = False
    block_reason: Optional[str] = None

    # ── Dynamic delegation tracking ──────────────────────────────────────────
    delegation_count: int = 0            # prevents infinite loops
    MAX_DELEGATIONS: int = Field(3, exclude=True)

    # ── Audit trail ──────────────────────────────────────────────────────────
    step_logs: List[AgentStepLog] = Field(default_factory=list)
    historical_context: Optional[str] = None   # from memory / previous campaigns

    def to_context_string(self) -> str:
        """
        Formats state as a human-readable string injected into agent task descriptions.
        This is how context flows between agents WITHOUT passing Python objects.
        """
        lines = [
            f"=== CAMPAIGN CONTEXT (ID: {self.campaign_id}) ===",
            f"Brief        : {self.brief}",
        ]
        if self.festival_tag:
            lines.append(f"Festival Tag : {self.festival_tag}")
        if self.target_audience:
            lines.append(f"Audience     : {self.target_audience}")
        if self.historical_context:
            lines.append(f"History      : {self.historical_context}")
        if self.strategy_output:
            lines.append(f"\n--- Strategy Output ---")
            lines.append(f"Theme        : {self.strategy_output.get('campaign_theme', 'N/A')}")
            lines.append(f"Tone         : {self.strategy_output.get('tone', 'N/A')}")
            msgs = self.strategy_output.get('key_messages', [])
            if msgs:
                lines.append(f"Key Messages : {'; '.join(msgs[:3])}")
        if self.content_output:
            ec = self.content_output.get("email_content", {})
            lines.append(f"\n--- Content Output ---")
            lines.append(f"Email Subject: {ec.get('subject', 'N/A')}")
        if self.risk_output:
            lines.append(f"\n--- Risk Output ---")
            lines.append(f"Green Light  : {self.risk_output.get('green_light')}")
            lines.append(f"Brand Safety : {self.risk_output.get('brand_safety')}/10")
        lines.append("=" * 45)
        return "\n".join(lines)

    def update_timestamp(self):
        self.updated_at = datetime.now().isoformat()

    def can_delegate(self) -> bool:
        return self.delegation_count < self.MAX_DELEGATIONS

    def log_step(self, agent_name: str, status: str,
                 output_summary: str = None, error: str = None,
                 started_at: str = None, completed_at: str = None):
        """Add or update an agent step in the audit log."""
        log = AgentStepLog(
            agent_name=agent_name,
            started_at=started_at or datetime.now().isoformat(),
            completed_at=completed_at or datetime.now().isoformat(),
            status=status,
            output_summary=output_summary,
            error=error,
        )
        self.step_logs.append(log)
        self.update_timestamp()


class CampaignOutput(BaseModel):
    """Final summarised output returned by the orchestrator after the full pipeline."""
    campaign_id: int
    success: bool
    pipeline_blocked: bool = False
    block_reason: Optional[str] = None
    emails_sent: int = 0
    emails_failed: int = 0
    risk_green_light: Optional[bool] = None
    analytics_summary: Optional[str] = None
    step_logs: List[AgentStepLog] = Field(default_factory=list)
    completed_at: str = Field(default_factory=lambda: datetime.now().isoformat())
