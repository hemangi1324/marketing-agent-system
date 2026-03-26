"""
tests/test_smtp_tool.py
------------------------
Unit tests for the SMTP email automation system.
Uses unittest.mock to avoid sending real emails during tests.

Run:
    python -m pytest tests/test_smtp_tool.py -v

    # Skip tests that need SMTP credentials:
    python -m pytest tests/test_smtp_tool.py -v -k "not live_smtp"
"""

import sys
import os
import json
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from dotenv import load_dotenv
load_dotenv()


# ── Recipient management tests ─────────────────────────────────────────────────

class TestEmailValidation:
    def test_valid_emails_pass(self):
        from database.recipients import validate_email
        valid_addresses = [
            "user@example.com",
            "first.last@company.co.in",
            "user+tag@domain.org",
            "marketing@yourcompany.com",
        ]
        for addr in valid_addresses:
            assert validate_email(addr), f"Expected {addr} to be valid"

    def test_invalid_emails_rejected(self):
        from database.recipients import validate_email
        invalid_addresses = [
            "not-an-email",
            "missing@tld",
            "@nodomain.com",
            "spaces in@email.com",
            "",
        ]
        for addr in invalid_addresses:
            assert not validate_email(addr), f"Expected {addr} to be invalid"

    def test_get_recipients_returns_list(self):
        from database.recipients import get_recipients
        result = get_recipients()
        assert isinstance(result, list), "get_recipients() must return a list"

    def test_get_recipients_structure(self):
        """Each recipient must have 'name' and 'email' keys."""
        from database.recipients import get_recipients
        for r in get_recipients():
            assert "email" in r, f"Recipient missing 'email' key: {r}"
            assert "name"  in r, f"Recipient missing 'name' key: {r}"

    def test_filter_removes_invalid_emails(self):
        """The internal filter should strip any malformed addresses."""
        from database.recipients import _filter_valid, validate_email
        mixed = [
            {"name": "Good",    "email": "good@example.com"},
            {"name": "Bad",     "email": "bad-email"},
            {"name": "Empty",   "email": ""},
            {"name": "Another", "email": "valid@domain.org"},
        ]
        result = _filter_valid(mixed)
        emails = [r["email"] for r in result]
        assert "good@example.com"  in emails
        assert "valid@domain.org"  in emails
        assert "bad-email"         not in emails
        assert ""                  not in emails


# ── SMTP sender tool (uses mocks — no real emails sent) ────────────────────────

class TestSmtpEmailSenderTool:

    def _make_tool(self):
        from tools.smtp_email_sender import SmtpEmailSenderTool
        return SmtpEmailSenderTool()

    def test_tool_has_correct_name(self):
        tool = self._make_tool()
        assert tool.name == "SMTP Email Sender"

    def test_tool_rejects_bad_json(self):
        tool = self._make_tool()
        result = json.loads(tool._run("this is not json at all"))
        assert "error" in result, "Should return error for invalid JSON"

    def test_tool_rejects_empty_recipients(self):
        tool = self._make_tool()
        result = json.loads(tool._run(json.dumps({
            "recipients": [],
            "subject":    "Test",
            "html_body":  "<p>Test</p>",
        })))
        assert "error" in result, "Should return error for empty recipients list"

    def test_tool_rejects_missing_html_body(self):
        tool = self._make_tool()
        result = json.loads(tool._run(json.dumps({
            "recipients": [{"name": "Alice", "email": "alice@example.com"}],
            "subject":    "Test",
        })))
        assert "error" in result, "Should return error when html_body is missing"

    @patch("tools.smtp_email_sender.smtplib.SMTP")
    def test_tool_sends_successfully_with_mock_smtp(self, mock_smtp_class):
        """Mocked SMTP — no real connection made."""
        mock_server = MagicMock()
        mock_smtp_class.return_value = mock_server

        tool = self._make_tool()

        with patch.dict(os.environ, {
            "EMAIL_USER": "test@example.com",
            "EMAIL_PASS": "testpassword",
        }):
            # Re-import to pick up patched env
            import importlib
            import tools.smtp_email_sender as mod
            mod.EMAIL_USER = "test@example.com"
            mod.EMAIL_PASS = "testpassword"

            result_str = tool._run(json.dumps({
                "recipients": [
                    {"name": "Alice", "email": "alice@example.com"},
                    {"name": "Bob",   "email": "bob@example.com"},
                ],
                "subject":     "Test Campaign",
                "html_body":   "<h1>Hello</h1>",
                "text_body":   "Hello",
                "campaign_id": 1,
            }))

        result = json.loads(result_str)
        assert "sent" in result,   "Result must have 'sent' key"
        assert "failed" in result, "Result must have 'failed' key"
        assert "total" in result,  "Result must have 'total' key"

    def test_send_function_fails_gracefully_with_no_credentials(self):
        """When no credentials are set, should return an error dict not raise."""
        from tools.smtp_email_sender import send_smtp_email
        import tools.smtp_email_sender as mod

        original_user = mod.EMAIL_USER
        original_pass = mod.EMAIL_PASS
        mod.EMAIL_USER = ""
        mod.EMAIL_PASS = ""

        try:
            result = send_smtp_email(
                recipients=[{"name": "Test", "email": "test@example.com"}],
                subject="Test",
                html_body="<p>Test</p>",
            )
            assert result["success"] is False
            assert len(result["failed"]) > 0
        finally:
            mod.EMAIL_USER = original_user
            mod.EMAIL_PASS = original_pass


# ── Email service (dispatch layer) tests ──────────────────────────────────────

class TestEmailService:

    def test_blocks_when_green_light_false(self):
        """dispatch_campaign_email must NOT send when green_light is False."""
        from services.email_service import dispatch_campaign_email

        content = {
            "email_subject": "Test Subject",
            "email_body":    "Test Body",
        }
        risk_result = {
            "green_light":          False,
            "brand_safety":         2,
            "legal_risk":           8,
            "cultural_sensitivity": 4,
            "flag_reason":          "Brand safety too low",
        }

        with patch("services.email_service.send_smtp_email") as mock_send:
            result = dispatch_campaign_email(
                content_dict=content,
                campaign_id=99,
                risk_result=risk_result,
            )
            mock_send.assert_not_called()   # SMTP must never be called
            assert result["blocked"] is True
            assert result["sent"] == 0
            assert "Brand safety" in result["block_reason"]

    def test_sends_when_green_light_true(self):
        """dispatch_campaign_email must attempt send when green_light is True."""
        from services.email_service import dispatch_campaign_email

        content = {
            "email_subject": "Diwali Sale — 50% OFF!",
            "email_body":    "Celebrate with our biggest ever sale.",
        }
        risk_result = {
            "green_light":          True,
            "brand_safety":         9,
            "legal_risk":           9,
            "cultural_sensitivity": 9,
            "flag_reason":          None,
        }

        mock_smtp_result = {
            "sent":    ["alice@example.com"],
            "failed":  [],
            "total":   1,
            "success": True,
        }

        with patch("services.email_service.send_smtp_email", return_value=mock_smtp_result) as mock_send, \
             patch("services.email_service.get_recipients",
                   return_value=[{"name": "Alice", "email": "alice@example.com"}]):

            result = dispatch_campaign_email(
                content_dict=content,
                campaign_id=42,
                risk_result=risk_result,
            )
            mock_send.assert_called_once()
            assert result["blocked"] is False
            assert result["sent"]    == 1
            assert result["failed"]  == 0

    def test_returns_no_recipients_error_gracefully(self):
        """Should handle empty recipient list gracefully (no crash)."""
        from services.email_service import dispatch_campaign_email

        content     = {"email_subject": "Test", "email_body": "Body"}
        risk_result = {"green_light": True, "flag_reason": None}

        with patch("services.email_service.get_recipients", return_value=[]):
            result = dispatch_campaign_email(
                content_dict=content,
                campaign_id=5,
                risk_result=risk_result,
            )
            assert result["recipients"] == 0
            assert "error" in result or result["sent"] == 0

    def test_html_body_builder_contains_subject(self):
        """HTML builder should embed the email subject in the output."""
        from services.email_service import _build_html_body

        html = _build_html_body(
            {"email_subject": "Unique Subject XYZ-999", "email_body": "Body text."},
            campaign_id=7,
        )
        assert "Unique Subject XYZ-999" in html
        assert "<html" in html.lower()

    def test_text_body_builder_contains_subject(self):
        """Plain text builder should include the subject line."""
        from services.email_service import _build_text_body
        text = _build_text_body({
            "email_subject": "My Subject Line",
            "email_body":    "Hello world.",
        })
        assert "My Subject Line" in text
        assert "Hello world." in text


# ── Scheduler tests ────────────────────────────────────────────────────────────

class TestCampaignScheduler:

    def test_get_due_campaigns_returns_past_dates(self):
        from datetime import date
        from scheduler.campaign_events import get_due_campaigns, CAMPAIGN_EVENTS

        # All campaigns with a past or today date should be returned
        from datetime import date as d
        past = d(2020, 1, 1)
        # No campaigns should be due as of 2020
        result = get_due_campaigns(reference_date=past)
        assert isinstance(result, list)
        # All should have send_date after 2020, so none due
        assert len(result) == 0

    def test_get_due_campaigns_future_date_gets_all(self):
        from datetime import date
        from scheduler.campaign_events import get_due_campaigns, CAMPAIGN_EVENTS

        # Use far future date — all events should be due
        far_future = date(2099, 12, 31)
        result = get_due_campaigns(reference_date=far_future)
        assert len(result) == len(CAMPAIGN_EVENTS)

    def test_scheduler_state_not_sent_initially(self):
        """Already-sent check should return False for a new ID."""
        # Temporarily override state file to use a temp path
        import scheduler.email_scheduler as sched
        original_state_file = sched._STATE_FILE
        sched._STATE_FILE = os.path.join(os.path.dirname(__file__), "_test_state.json")

        try:
            assert not sched._already_sent("brand-new-campaign-id-xyz")
        finally:
            sched._STATE_FILE = original_state_file
            # Clean up temp file
            if os.path.exists(sched._STATE_FILE):
                os.remove(sched._STATE_FILE)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
