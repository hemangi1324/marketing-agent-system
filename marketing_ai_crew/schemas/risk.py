"""
schemas/risk.py
Pydantic schemas for the Risk Agent.
"""

from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class RiskInput(BaseModel):
    """Input to the risk agent — the content to review."""
    campaign_id: int
    email_subject: str = ""
    email_body: str = ""
    instagram_caption: str = ""
    twitter_post: str = ""

    @classmethod
    def from_content_dict(cls, content_dict: dict, campaign_id: int) -> "RiskInput":
        """Build from the flat dict format used by existing pipeline."""
        return cls(
            campaign_id=campaign_id,
            email_subject=content_dict.get("email_subject", ""),
            email_body=content_dict.get("email_body", ""),
            instagram_caption=content_dict.get("instagram_caption", ""),
            twitter_post=content_dict.get("twitter_post", ""),
        )

    def to_content_dict(self) -> dict:
        """Convert back to flat dict for existing run_risk_check()."""
        return {
            "email_subject":     self.email_subject,
            "email_body":        self.email_body,
            "instagram_caption": self.instagram_caption,
            "twitter_post":      self.twitter_post,
        }


class RiskOutput(BaseModel):
    """Structured output from the Risk Agent."""
    brand_safety: int = Field(..., ge=0, le=10, description="Brand safety score 0-10")
    legal_risk: int = Field(..., ge=0, le=10, description="Legal risk score 0-10")
    cultural_sensitivity: int = Field(..., ge=0, le=10, description="Cultural sensitivity 0-10")
    green_light: bool = Field(..., description="True = content approved for dispatch")
    flag_reason: Optional[str] = Field(None, description="Reason for flagging (if any)")
    explanation: str = Field("", description="2-3 sentence explanation of scores")

    @field_validator("brand_safety", "legal_risk", "cultural_sensitivity", mode="before")
    @classmethod
    def clamp_score(cls, v):
        """Ensure scores are always within [0, 10] even if LLM hallucinates."""
        try:
            return max(0, min(10, int(v)))
        except (TypeError, ValueError):
            return 0

    @classmethod
    def from_dict(cls, d: dict) -> "RiskOutput":
        """Build from the flat dict returned by existing run_risk_check()."""
        return cls(
            brand_safety=d.get("brand_safety", 0),
            legal_risk=d.get("legal_risk", 0),
            cultural_sensitivity=d.get("cultural_sensitivity", 0),
            green_light=d.get("green_light", False),
            flag_reason=d.get("flag_reason"),
            explanation=d.get("explanation", ""),
        )

    def to_dict(self) -> dict:
        """Back to flat dict for backward compatibility."""
        return self.model_dump()

    @property
    def min_score(self) -> int:
        return min(self.brand_safety, self.legal_risk, self.cultural_sensitivity)

    @property
    def avg_score(self) -> float:
        return (self.brand_safety + self.legal_risk + self.cultural_sensitivity) / 3
