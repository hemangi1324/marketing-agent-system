"""
tests/test_tools.py
Unit tests for all tools — no LLM needed, tests tools in isolation.
Run: python -m pytest tests/test_tools.py -v
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from dotenv import load_dotenv
load_dotenv()


# ── Brand Guidelines Tool ─────────────────────────────────────
def test_brand_guidelines_returns_content():
    from tools.file_tool import BrandGuidelinesTool
    t = BrandGuidelinesTool()
    result = t._run("")
    assert len(result) > 50, "Brand guidelines should return content"
    print(f"\n  Brand guidelines: {len(result)} chars OK")


def test_output_saver():
    from tools.file_tool import OutputSaverTool
    t = OutputSaverTool()
    result = t._run("Test output content")
    assert "Saved" in result or "output" in result.lower()
    print(f"\n  OutputSaver: {result}")


# ── CRM Tools ─────────────────────────────────────────────────
def test_crm_create_contact():
    from tools.mock_crm_tool import CRMCreateContactTool, CRMListContactsTool
    creator = CRMCreateContactTool()
    result = creator._run(json.dumps({
        "name": "Test User", "company": "Acme Corp",
        "email": "test@acme.com", "role": "CTO", "notes": "Met at SaaStr"
    }))
    assert "Contact added" in result or "MOCK CRM" in result
    print(f"\n  CRM create: {result}")

    lister = CRMListContactsTool()
    result2 = lister._run()
    assert "Test User" in result2 or "contact" in result2.lower()
    print(f"  CRM list: OK")


def test_crm_log_email():
    from tools.mock_crm_tool import CRMLogEmailTool
    t = CRMLogEmailTool()
    result = t._run(json.dumps({
        "contact_id": "c1", "subject": "Following up", "body": "Hi there..."
    }))
    assert "logged" in result.lower() or "MOCK" in result
    print(f"\n  CRM log email: {result}")


# ── Social Tools ──────────────────────────────────────────────
def test_social_schedule():
    from tools.mock_social_tool import SocialScheduleTool, SocialGetQueueTool
    scheduler = SocialScheduleTool()
    result = scheduler._run(json.dumps({
        "platform": "instagram",
        "content": "Test post content #test",
        "scheduled_at": "2025-06-01T10:00:00"
    }))
    assert "Scheduled" in result or "MOCK" in result
    print(f"\n  Social schedule: {result}")

    viewer = SocialGetQueueTool()
    result2 = viewer._run()
    assert len(result2) > 0
    print(f"  Social queue: OK")


# ── Analytics Tools ───────────────────────────────────────────
def test_analytics_pull_metrics():
    from tools.mock_analytics_tool import AnalyticsPullMetricsTool
    t = AnalyticsPullMetricsTool()
    result = t._run("last_7_days")
    data = json.loads(result)
    assert "sessions" in data
    assert "conversions" in data
    assert data["sessions"] > 0
    print(f"\n  Analytics: sessions={data['sessions']}, "
          f"signups={data['conversions']['free_trial_signups']}")


def test_analytics_trends():
    from tools.mock_analytics_tool import AnalyticsTrendsTool
    t = AnalyticsTrendsTool()
    result = t._run("sessions")
    assert "UP" in result or "DOWN" in result
    print(f"\n  Trends: {result[:80]}")


# ── Ads Tools ─────────────────────────────────────────────────
def test_ads_get_performance():
    from tools.mock_ads_tool import AdsGetPerformanceTool
    t = AdsGetPerformanceTool()
    result = t._run()
    assert "Campaign" in result or "ACTIVE" in result
    print(f"\n  Ads performance: {result[:120]}")


def test_ads_create_variation():
    from tools.mock_ads_tool import AdsCreateVariationTool
    t = AdsCreateVariationTool()
    result = t._run(json.dumps({
        "campaign_id": "c001",
        "headlines": ["Save time today", "Automate everything", "Your team of one"],
        "descriptions": ["Try free for 14 days", "No credit card required"]
    }))
    assert "variation" in result.lower() or "MOCK" in result
    print(f"\n  Ads variation: {result}")


# ── Email Tools ───────────────────────────────────────────────
def test_email_create_campaign():
    from tools.mock_email_tool import EmailCreateCampaignTool
    t = EmailCreateCampaignTool()
    result = t._run(json.dumps({
        "subject_line": "Your free trial starts now",
        "preview_text": "Here's how to get started in 5 minutes",
        "body": "Welcome to Acme...",
        "segment": "new_trials"
    }))
    assert "Campaign" in result or "MOCK" in result
    print(f"\n  Email campaign: {result}")


def test_email_create_sequence():
    from tools.mock_email_tool import EmailCreateSequenceTool
    t = EmailCreateSequenceTool()
    result = t._run(json.dumps({
        "sequence_name": "Welcome Drip",
        "trigger": "signup",
        "emails": [
            {"delay_days": 0, "subject": "Welcome!", "body": "Hi..."},
            {"delay_days": 3, "subject": "Quick tip", "body": "Did you know..."},
        ]
    }))
    assert "Sequence" in result or "MOCK" in result
    print(f"\n  Email sequence: {result}")


# ── Search Tool ───────────────────────────────────────────────
def test_search_returns_results():
    """Note: requires internet. Skip with: pytest -k 'not search'"""
    from tools.search_tool import DuckDuckGoSearchTool
    t = DuckDuckGoSearchTool()
    result = t._run("crewai python framework")
    # Should either return results or a graceful error
    assert len(result) > 20
    print(f"\n  Search: {result[:100]}...")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
