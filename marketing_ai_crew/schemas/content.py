"""
schemas/content.py
Pydantic schemas for content agent inputs and outputs.
"""

from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel, Field


class EmailContent(BaseModel):
    """Structured email content produced by the content agent."""
    subject: str = Field(..., description="Email subject line (< 80 chars recommended)")
    body: str = Field(..., description="Full email body text")
    preview_text: Optional[str] = Field(None, description="Email preview/preheader text")


class SocialContent(BaseModel):
    """Structured social media content produced by the content agent."""
    instagram_caption: Optional[str] = Field(None, description="Instagram caption with hashtags")
    twitter_post: Optional[str] = Field(None, description="Twitter/X post (< 280 chars)")
    linkedin_post: Optional[str] = Field(None, description="LinkedIn post (200-300 words)")
    subject_line_variants: List[str] = Field(
        default_factory=list,
        description="3 alternative email subject line options"
    )


class ContentOutput(BaseModel):
    """
    Full output from the Content Agent.
    Contains both email and social media content, ready for risk review.
    """
    email_content: EmailContent
    social_content: SocialContent
    brand_tone: Optional[str] = Field(None, description="Detected or applied brand tone")

    def to_risk_dict(self) -> dict:
        """
        Convert to the flat dict format expected by the risk agent's run_risk_check().
        Maintains backward compatibility with the existing risk pipeline.
        """
        return {
            "email_subject":      self.email_content.subject,
            "email_body":         self.email_content.body,
            "instagram_caption":  self.social_content.instagram_caption or "",
            "twitter_post":       self.social_content.twitter_post or "",
        }

    def to_email_service_dict(self) -> dict:
        """
        Convert to the flat dict format expected by dispatch_campaign_email().
        Maintains backward compatibility with the existing email service.
        """
        return {
            "email_subject":      self.email_content.subject,
            "email_body":         self.email_content.body,
            "instagram_caption":  self.social_content.instagram_caption or "",
            "twitter_post":       self.social_content.twitter_post or "",
        }
