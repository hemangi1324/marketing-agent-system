"""
tools/smtp_email_sender.py
--------------------------
Production SMTP email sender using Python's built-in smtplib (TLS on port 587).
No OAuth, no Gmail API — just SMTP credentials from environment variables.

Environment variables required:
    EMAIL_USER          — sender email address  (e.g. you@gmail.com)
    EMAIL_PASS          — app password / SMTP password
    SMTP_HOST           — SMTP server host      (default: smtp.gmail.com)
    SMTP_PORT           — SMTP port             (default: 587)
    EMAIL_SENDER_NAME   — friendly from name    (default: Marketing AI Crew)

Usage (standalone):
    from tools.smtp_email_sender import send_smtp_email
    result = send_smtp_email(
        recipients=[{"name": "Alice", "email": "alice@example.com"}],
        subject="Hello from Marketing AI",
        html_body="<h1>Hello</h1>",
        text_body="Hello",
    )

Usage (as CrewAI tool):
    from tools.smtp_email_sender import SmtpEmailSenderTool
    tool = SmtpEmailSenderTool()
    # agent calls tool._run(json_string)
"""

import os
import json
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from typing import List, Dict, Any

from dotenv import load_dotenv
from crewai.tools import BaseTool

load_dotenv()

# ── Configuration ─────────────────────────────────────────────────────────────
SMTP_HOST         = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT         = int(os.getenv("SMTP_PORT", "587"))
EMAIL_USER        = os.getenv("EMAIL_USER", "")
EMAIL_PASS        = os.getenv("EMAIL_PASS", "")
EMAIL_SENDER_NAME = os.getenv("EMAIL_SENDER_NAME", "Marketing AI Crew")

# ── Log file (outputs/email_send_log.jsonl) ───────────────────────────────────
_LOG_DIR  = os.path.join(os.path.dirname(__file__), "..", "outputs")
_LOG_FILE = os.path.join(_LOG_DIR, "email_send_log.jsonl")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("smtp_email_sender")


# ── Internal helpers ──────────────────────────────────────────────────────────

def _log_send_event(event: Dict[str, Any]) -> None:
    """Append a JSON line to the send-log file."""
    os.makedirs(_LOG_DIR, exist_ok=True)
    event["logged_at"] = datetime.now().isoformat()
    try:
        with open(_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")
    except OSError as exc:
        logger.warning("Could not write to log file: %s", exc)


def _build_mime_message(
    recipient_name: str,
    recipient_email: str,
    subject: str,
    html_body: str,
    text_body: str,
) -> MIMEMultipart:
    """Build a MIME multipart (text + HTML) message object."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"{EMAIL_SENDER_NAME} <{EMAIL_USER}>"
    msg["To"]      = f"{recipient_name} <{recipient_email}>" if recipient_name else recipient_email

    # Attach plain text first, then HTML (clients prefer the last part)
    msg.attach(MIMEText(text_body or "Please view this email in an HTML-capable client.", "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))
    return msg


# ── Core send function ────────────────────────────────────────────────────────

def send_smtp_email(
    recipients: List[Dict[str, str]],
    subject: str,
    html_body: str,
    text_body: str = "",
    campaign_id: Any = None,
) -> Dict[str, Any]:
    """
    Send an HTML email to one or more recipients via SMTP (TLS port 587).

    Args:
        recipients  : list of dicts with keys "email" (required) and "name" (optional)
        subject     : email subject line
        html_body   : full HTML body string
        text_body   : plain-text fallback body (optional)
        campaign_id : optional campaign identifier for logging

    Returns:
        dict with keys:
            sent    — list of successfully delivered email addresses
            failed  — list of dicts {"email":…, "error":…}
            total   — int total attempted
            success — bool (True if all sent without errors)
    """
    if not EMAIL_USER or not EMAIL_PASS:
        msg = (
            "SMTP credentials missing. Set EMAIL_USER and EMAIL_PASS in your .env file.\n"
            "For Gmail, use a 16-character App Password (not your regular password)."
        )
        logger.error(msg)
        return {"sent": [], "failed": [{"email": "ALL", "error": msg}], "total": 0, "success": False}

    sent_list:   List[str]           = []
    failed_list: List[Dict[str, str]] = []

    try:
        logger.info("Connecting to %s:%s …", SMTP_HOST, SMTP_PORT)
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(EMAIL_USER, EMAIL_PASS)
        logger.info("SMTP login successful.")

        for recipient in recipients:
            email = recipient.get("email", "").strip()
            name  = recipient.get("name", "").strip()

            if not email:
                logger.warning("Skipping recipient with missing email field: %s", recipient)
                failed_list.append({"email": "(missing)", "error": "email field is empty"})
                continue

            try:
                mime_msg = _build_mime_message(name, email, subject, html_body, text_body)
                server.sendmail(EMAIL_USER, [email], mime_msg.as_string())
                sent_list.append(email)
                logger.info("✅  Sent  → %s", email)

                _log_send_event({
                    "status":      "sent",
                    "campaign_id": campaign_id,
                    "recipient":   email,
                    "subject":     subject,
                })

            except smtplib.SMTPRecipientsRefused as exc:
                error_msg = f"Recipient refused: {exc}"
                logger.error("❌  Failed → %s | %s", email, error_msg)
                failed_list.append({"email": email, "error": error_msg})
                _log_send_event({
                    "status":      "failed",
                    "campaign_id": campaign_id,
                    "recipient":   email,
                    "subject":     subject,
                    "error":       error_msg,
                })

            except Exception as exc:          # noqa: BLE001
                error_msg = str(exc)
                logger.error("❌  Failed → %s | %s", email, error_msg)
                failed_list.append({"email": email, "error": error_msg})
                _log_send_event({
                    "status":      "failed",
                    "campaign_id": campaign_id,
                    "recipient":   email,
                    "subject":     subject,
                    "error":       error_msg,
                })

        server.quit()

    except smtplib.SMTPAuthenticationError:
        error_msg = (
            "SMTP authentication failed. Check EMAIL_USER / EMAIL_PASS. "
            "For Gmail, ensure you are using an App Password, not your regular password."
        )
        logger.error(error_msg)
        return {"sent": [], "failed": [{"email": "ALL", "error": error_msg}], "total": len(recipients), "success": False}

    except (smtplib.SMTPException, OSError) as exc:
        error_msg = f"SMTP connection error: {exc}"
        logger.error(error_msg)
        return {"sent": [], "failed": [{"email": "ALL", "error": error_msg}], "total": len(recipients), "success": False}

    result = {
        "sent":    sent_list,
        "failed":  failed_list,
        "total":   len(recipients),
        "success": len(failed_list) == 0,
    }
    logger.info(
        "Campaign %s complete — sent: %d / %d  |  failed: %d",
        campaign_id or "?", len(sent_list), len(recipients), len(failed_list),
    )
    return result


# ── CrewAI Tool wrapper ───────────────────────────────────────────────────────

class SmtpEmailSenderTool(BaseTool):
    """
    CrewAI tool that sends real HTML emails via SMTP.
    Input must be a JSON string with keys:
        recipients  — list of {name, email} dicts      (required)
        subject     — email subject line                (required)
        html_body   — HTML content of the email         (required)
        text_body   — plain text fallback               (optional)
        campaign_id — campaign identifier for logging   (optional)

    Example input:
        {
          "recipients": [{"name": "Alice", "email": "alice@example.com"}],
          "subject": "Your Diwali Offer Inside 🎉",
          "html_body": "<h1>Big Sale!</h1><p>Shop now.</p>",
          "text_body": "Big Sale! Shop now.",
          "campaign_id": 42
        }
    """

    name: str        = "SMTP Email Sender"
    description: str = (
        "Send real HTML emails to a list of recipients via SMTP. "
        "Input: JSON with recipients (list of {name,email}), subject, html_body, "
        "text_body (optional), campaign_id (optional). "
        "Returns a JSON result with sent/failed counts."
    )

    def _run(self, input_json: str) -> str:
        try:
            data = json.loads(input_json)
        except (json.JSONDecodeError, TypeError):
            # Treat bare string as subject if not valid JSON
            return json.dumps({
                "error": "Invalid JSON input. Expected keys: recipients, subject, html_body.",
                "input_received": str(input_json)[:200],
            })

        recipients  = data.get("recipients", [])
        subject     = data.get("subject", "(No Subject)")
        html_body   = data.get("html_body", "")
        text_body   = data.get("text_body", "")
        campaign_id = data.get("campaign_id", None)

        if not recipients:
            return json.dumps({"error": "No recipients provided. Include a 'recipients' list in the JSON."})
        if not html_body:
            return json.dumps({"error": "No html_body provided."})

        result = send_smtp_email(
            recipients=recipients,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
            campaign_id=campaign_id,
        )
        return json.dumps(result)


# ── Quick manual test ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    print("="*60)
    print("SMTP Email Sender — Manual Test")
    print("="*60)
    print(f"SMTP_HOST : {SMTP_HOST}:{SMTP_PORT}")
    print(f"EMAIL_USER: {EMAIL_USER or '⚠️  NOT SET'}")
    print(f"EMAIL_PASS: {'*'*len(EMAIL_PASS) if EMAIL_PASS else '⚠️  NOT SET'}")
    print()

    if not EMAIL_USER or not EMAIL_PASS:
        print("❌  Set EMAIL_USER and EMAIL_PASS in your .env first.")
        sys.exit(1)

    test_result = send_smtp_email(
        recipients=[{"name": "Test User", "email": EMAIL_USER}],  # send to self
        subject="✅ Marketing AI — SMTP Test",
        html_body="<h2>SMTP is working! 🎉</h2><p>Your Marketing AI Crew email pipeline is connected.</p>",
        text_body="SMTP is working! Your Marketing AI Crew email pipeline is connected.",
        campaign_id="test-001",
    )
    print("\n── Result ──────────────────────────────────")
    print(json.dumps(test_result, indent=2))
