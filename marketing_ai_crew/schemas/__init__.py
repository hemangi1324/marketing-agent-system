"""
schemas/__init__.py
Exports all Pydantic schemas for inter-agent data exchange.
"""

from schemas.campaign import CampaignInput, CampaignState, CampaignOutput
from schemas.content import EmailContent, SocialContent, ContentOutput
from schemas.risk import RiskInput, RiskOutput
from schemas.analytics import PostMortem, AnalyticsInput, AnalyticsOutput
from schemas.communication import EmailPayload, SlackPayload, TelegramPayload, CommResult
from schemas.strategy import StrategyInput, StrategyOutput

__all__ = [
    # Campaign
    "CampaignInput", "CampaignState", "CampaignOutput",
    # Content
    "EmailContent", "SocialContent", "ContentOutput",
    # Risk
    "RiskInput", "RiskOutput",
    # Analytics
    "PostMortem", "AnalyticsInput", "AnalyticsOutput",
    # Communication
    "EmailPayload", "SlackPayload", "TelegramPayload", "CommResult",
    # Strategy
    "StrategyInput", "StrategyOutput",
]
