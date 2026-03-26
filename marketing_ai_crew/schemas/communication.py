"""
schemas/communication.py
Pydantic schemas for the Communication Layer (Email, Slack, Telegram).
"""

from __future__ import annotations
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, EmailStr


class EmailPayload(BaseModel):
    """Payload sent to the SMTP email tool."""
    recipients: List[Dict[str, str]] = Field(
        ..., description="List of {name, email} dicts"
    )
    subject: str = Field(..., description="Email subject line")
    html_body: str = Field(..., description="HTML body")
    text_body: str = Field("", description="Plain-text fallback body")
    campaign_id: Any = Field(None, description="Campaign identifier for logging")

    def to_dict(self) -> dict:
        return self.model_dump()


class SlackPayload(BaseModel):
    """Payload sent to the Slack alert tool."""
    campaign_id: int
    scores: Dict[str, int] = Field(
        ..., description="Risk scores: brand_safety, legal_risk, cultural_sensitivity"
    )
    flag_reason: Optional[str] = None

    def to_json_string(self) -> str:
        import json
        return json.dumps(self.model_dump())


class TelegramPayload(BaseModel):
    """Payload sent to the Telegram ad tool."""
    message: str = Field(..., description="Ad copy message text")
    campaign_id: Optional[int] = None

    def to_message_string(self) -> str:
        """Return the message string for send_telegram_message()."""
        return self.message


class CommResult(BaseModel):
    """Result from a single communication channel dispatch."""
    channel: str = Field(..., description="Channel name: email | slack | telegram")
    success: bool = False
    sent_count: int = 0
    failed_count: int = 0
    error: Optional[str] = None
    idempotency_key: Optional[str] = None   # hash used to prevent duplicate sends


class CommunicationOutput(BaseModel):
    """Aggregated results from all communication channels triggered in one pipeline run."""
    campaign_id: int
    results: List[CommResult] = Field(default_factory=list)
    overall_success: bool = False
    emails_sent: int = 0
    emails_failed: int = 0

    def add_result(self, result: CommResult):
        self.results.append(result)
        if result.channel == "email":
            self.emails_sent += result.sent_count
            self.emails_failed += result.failed_count
        # Overall success = at least email went through cleanly
        email_results = [r for r in self.results if r.channel == "email"]
        if email_results:
            self.overall_success = all(r.success for r in email_results)
