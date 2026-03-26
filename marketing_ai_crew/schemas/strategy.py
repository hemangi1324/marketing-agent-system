"""
schemas/strategy.py
Pydantic schemas for the Strategy Agent.
"""

from __future__ import annotations
from typing import Optional, List, Dict
from pydantic import BaseModel, Field


class StrategyInput(BaseModel):
    """Input for the Strategy Agent — context and brief."""
    brief: str = Field(..., description="Campaign brief / objective")
    festival_tag: Optional[str] = Field(None, description="Festival context e.g. 'diwali'")
    target_audience: Optional[str] = Field(None, description="Who this campaign targets")
    historical_context: Optional[str] = Field(
        None, description="Post-mortem / memory from previous campaigns for this festival"
    )
    competitor_context: Optional[str] = Field(
        None, description="Competitor positioning notes (from research)"
    )


class StrategyOutput(BaseModel):
    """
    Structured strategy output used to guide the Content Agent.
    The orchestrator injects this into the content agent's task description.
    """
    campaign_theme: str = Field(..., description="Central theme / headline concept")
    tone: str = Field(..., description="Brand tone: e.g. 'urgent & warm', 'playful', 'professional'")
    key_messages: List[str] = Field(
        default_factory=list,
        description="3-5 core messages the campaign must convey"
    )
    platform_priorities: Dict[str, str] = Field(
        default_factory=dict,
        description="Per-platform content direction e.g. {instagram: 'visual-first, 2 CTAs'}"
    )
    audience_insight: Optional[str] = Field(
        None, description="Key insight about the target audience to inform copy"
    )
    do_not_use: Optional[List[str]] = Field(
        None, description="Words / phrases to avoid (from brand guidelines or past failures)"
    )

    @classmethod
    def from_dict(cls, d: dict) -> "StrategyOutput":
        return cls(
            campaign_theme=d.get("campaign_theme", "General Promotion"),
            tone=d.get("tone", "professional"),
            key_messages=d.get("key_messages", []),
            platform_priorities=d.get("platform_priorities", {}),
            audience_insight=d.get("audience_insight"),
            do_not_use=d.get("do_not_use"),
        )

    def to_context_string(self) -> str:
        """Format for injection into content agent task description."""
        msgs = "\n".join(f"  - {m}" for m in self.key_messages)
        platforms = "\n".join(f"  {p}: {v}" for p, v in self.platform_priorities.items())
        avoid = ", ".join(self.do_not_use) if self.do_not_use else "None"
        return f"""
--- STRATEGY DIRECTION ---
Campaign Theme : {self.campaign_theme}
Brand Tone     : {self.tone}
Key Messages   :
{msgs}
Platform Notes :
{platforms}
Audience Insight: {self.audience_insight or 'N/A'}
Avoid using    : {avoid}
---
"""
