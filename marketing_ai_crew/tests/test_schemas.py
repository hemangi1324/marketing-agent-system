"""
tests/test_schemas.py
Tests for all Pydantic schemas.
Run: python -m pytest tests/test_schemas.py -v
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from pydantic import ValidationError


# ── CampaignState ─────────────────────────────────────────────────────────────

def test_campaign_state_creation():
    from schemas.campaign import CampaignState
    state = CampaignState(campaign_id=1, brief="Test campaign")
    assert state.campaign_id == 1
    assert state.brief == "Test campaign"
    assert state.green_light is None
    assert state.pipeline_complete is False


def test_campaign_state_context_string():
    from schemas.campaign import CampaignState
    state = CampaignState(campaign_id=42, brief="Diwali offer", festival_tag="diwali")
    ctx = state.to_context_string()
    assert "42" in ctx
    assert "Diwali offer" in ctx
    assert "diwali" in ctx


def test_campaign_state_log_step():
    from schemas.campaign import CampaignState
    state = CampaignState(campaign_id=1, brief="Test")
    state.log_step("risk_agent", "success", output_summary="green_light=True")
    assert len(state.step_logs) == 1
    assert state.step_logs[0].agent_name == "risk_agent"


def test_campaign_input_validation():
    from schemas.campaign import CampaignInput
    inp = CampaignInput(brief="Test", campaign_id=5)
    assert inp.mode == "sequential"
    assert inp.festival_tag is None


# ── ContentOutput ─────────────────────────────────────────────────────────────

def test_content_output_risk_dict():
    from schemas.content import ContentOutput, EmailContent, SocialContent
    co = ContentOutput(
        email_content=EmailContent(subject="Test Subject", body="Test body"),
        social_content=SocialContent(
            instagram_caption="Insta caption #test",
            twitter_post="Twitter post",
        ),
    )
    risk_dict = co.to_risk_dict()
    assert risk_dict["email_subject"] == "Test Subject"
    assert risk_dict["email_body"] == "Test body"
    assert risk_dict["instagram_caption"] == "Insta caption #test"


def test_content_output_email_service_dict():
    from schemas.content import ContentOutput, EmailContent, SocialContent
    co = ContentOutput(
        email_content=EmailContent(subject="Sub", body="Body"),
        social_content=SocialContent(),
    )
    d = co.to_email_service_dict()
    assert "email_subject" in d
    assert "email_body" in d


# ── RiskOutput ────────────────────────────────────────────────────────────────

def test_risk_output_score_clamping():
    """Scores outside 0-10 should be clamped."""
    from schemas.risk import RiskOutput
    ro = RiskOutput(
        brand_safety=15,   # should clamp to 10
        legal_risk=-3,     # should clamp to 0
        cultural_sensitivity=7,
        green_light=True,
        explanation="Test",
    )
    assert ro.brand_safety == 10
    assert ro.legal_risk == 0


def test_risk_output_from_dict():
    from schemas.risk import RiskOutput
    d = {
        "brand_safety": 8, "legal_risk": 9, "cultural_sensitivity": 7,
        "green_light": True, "flag_reason": None, "explanation": "All good"
    }
    ro = RiskOutput.from_dict(d)
    assert ro.green_light is True
    assert ro.min_score == 7
    assert ro.avg_score == pytest.approx(8.0)


def test_risk_input_roundtrip():
    from schemas.risk import RiskInput
    content_dict = {
        "email_subject": "Sale!",
        "email_body": "Buy now",
        "instagram_caption": "#sale",
        "twitter_post": "Tweet",
    }
    ri = RiskInput.from_content_dict(content_dict, campaign_id=99)
    assert ri.campaign_id == 99
    assert ri.email_subject == "Sale!"
    out = ri.to_content_dict()
    assert out["email_subject"] == "Sale!"


# ── AnalyticsOutput ───────────────────────────────────────────────────────────

def test_analytics_output_from_dict():
    from schemas.analytics import AnalyticsOutput
    d = {
        "healed": True,
        "new_ctr": 1.2,
        "new_open_rate": 25.0,
        "improved_from_last": True,
        "post_mortem": {
            "what_worked": "Urgency tone",
            "what_failed": "Small discount",
            "market_context": "Diwali peak",
            "recommendation": "Use 40% discount next time",
        }
    }
    ao = AnalyticsOutput.from_dict(d)
    assert ao.healed is True
    assert ao.new_ctr == pytest.approx(1.2)
    assert "Urgency tone" in ao.post_mortem.what_worked


def test_analytics_input_from_dicts():
    from schemas.analytics import AnalyticsInput
    ai = AnalyticsInput.from_dicts(
        campaign_id=10, attempt=2,
        old_metrics={"ctr": 0.4, "open_rate": 10.0},
        new_metrics={"ctr": 0.9, "open_rate": 18.0},
    )
    assert ai.old_ctr == 0.4
    assert ai.new_ctr == 0.9


# ── StrategyOutput ────────────────────────────────────────────────────────────

def test_strategy_output_context_string():
    from schemas.strategy import StrategyOutput
    so = StrategyOutput(
        campaign_theme="Festival of Savings",
        tone="warm and urgent",
        key_messages=["Save 30%", "Limited time only"],
        platform_priorities={"email": "CTA focused"},
    )
    ctx = so.to_context_string()
    assert "Festival of Savings" in ctx
    assert "warm and urgent" in ctx
    assert "Save 30%" in ctx


# ── CommunicationOutput ───────────────────────────────────────────────────────

def test_comm_result_add():
    from schemas.communication import CommunicationOutput, CommResult
    co = CommunicationOutput(campaign_id=1)
    co.add_result(CommResult(channel="email", success=True, sent_count=5, failed_count=0))
    assert co.emails_sent == 5
    assert co.overall_success is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
