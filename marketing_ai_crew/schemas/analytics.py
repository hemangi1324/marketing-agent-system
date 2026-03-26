"""
schemas/analytics.py
Pydantic schemas for the Analytics Agent.
"""

from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field


class PostMortem(BaseModel):
    """Qualitative post-mortem analysis from the analytics agent."""
    what_worked: str = Field("Unknown", description="What change likely caused improvement")
    what_failed: str = Field("Unknown", description="What still isn't working and why")
    market_context: str = Field("Unknown", description="Seasonal or competitive context")
    recommendation: str = Field(
        "Retry with cleaner content", description="Single most important next action"
    )


class AnalyticsInput(BaseModel):
    """Input to the analytics agent — metrics before and after a healing attempt."""
    campaign_id: int
    attempt: int = Field(1, ge=1, le=10)
    old_ctr: float = Field(0.0, ge=0.0, description="CTR before this attempt (%)")
    old_open_rate: float = Field(0.0, ge=0.0, description="Open rate before (%)")
    new_ctr: float = Field(0.0, ge=0.0, description="CTR after this attempt (%)")
    new_open_rate: float = Field(0.0, ge=0.0, description="Open rate after (%)")
    festival_tag: Optional[str] = None

    @classmethod
    def from_dicts(cls, campaign_id: int, attempt: int,
                   old_metrics: dict, new_metrics: dict,
                   festival_tag: str = None) -> "AnalyticsInput":
        """Build from the dict format used by existing run_analytics()."""
        return cls(
            campaign_id=campaign_id,
            attempt=attempt,
            old_ctr=old_metrics.get("ctr", 0.0),
            old_open_rate=old_metrics.get("open_rate", 0.0),
            new_ctr=new_metrics.get("ctr", 0.0),
            new_open_rate=new_metrics.get("open_rate", 0.0),
            festival_tag=festival_tag,
        )

    def to_old_metrics_dict(self) -> dict:
        return {"ctr": self.old_ctr, "open_rate": self.old_open_rate}

    def to_new_metrics_dict(self) -> dict:
        return {"ctr": self.new_ctr, "open_rate": self.new_open_rate}


class AnalyticsOutput(BaseModel):
    """Structured output from the Analytics Agent."""
    healed: bool = Field(False, description="True if CTR >= 1.0%")
    new_ctr: float = Field(0.0, description="Post-healing CTR (%)")
    new_open_rate: float = Field(0.0, description="Post-healing open rate (%)")
    improved_from_last: bool = Field(False, description="True if CTR improved vs last attempt")
    post_mortem: PostMortem = Field(default_factory=PostMortem)

    @classmethod
    def from_dict(cls, d: dict) -> "AnalyticsOutput":
        """Build from the flat dict returned by existing run_analytics()."""
        pm_dict = d.get("post_mortem", {})
        return cls(
            healed=d.get("healed", False),
            new_ctr=d.get("new_ctr", 0.0),
            new_open_rate=d.get("new_open_rate", 0.0),
            improved_from_last=d.get("improved_from_last", False),
            post_mortem=PostMortem(**pm_dict) if pm_dict else PostMortem(),
        )

    def to_dict(self) -> dict:
        return self.model_dump()

    def summary_string(self) -> str:
        status = "HEALED ✅" if self.healed else "NOT HEALED ❌"
        improved = "improved ↑" if self.improved_from_last else "no improvement →"
        return (
            f"{status} | CTR: {self.new_ctr:.2f}% ({improved}) | "
            f"Recommendation: {self.post_mortem.recommendation}"
        )
