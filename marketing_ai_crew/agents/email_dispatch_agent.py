"""
agents/email_dispatch_agent.py
-------------------------------
The Email Dispatch Agent — the final step in the pipeline.
This agent only activates after the risk agent has issued a green_light.
It uses the real SmtpEmailSenderTool to send HTML emails.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from crewai import Agent
from config.settings import get_llm, AGENT_DEFAULTS
from tools.smtp_email_sender import SmtpEmailSenderTool
from dotenv import load_dotenv

load_dotenv()


def get_email_dispatch_agent() -> Agent:
    """
    Returns the Email Dispatch Agent.

    This agent is responsible for:
    - Receiving validated, risk-approved email content
    - Sending it to real recipients via SMTP
    - Reporting back the send results (sent, failed counts)

    It is intentionally scoped narrowly: it does NOT generate content,
    it does NOT do risk analysis — it only sends.
    """
    return Agent(
        role="Email Dispatch Specialist",
        goal=(
            "Send approved marketing email campaigns to recipients using SMTP. "
            "Report the number of emails sent and any failures. "
            "ONLY send emails that have passed the risk review (green_light=True)."
        ),
        backstory=(
            "You are a reliable email delivery specialist with experience in high-volume "
            "marketing campaigns. You ensure that every approved email reaches its intended "
            "recipient. You log every outcome meticulously and never send content that "
            "has not been cleared by the risk review process."
        ),
        tools=[SmtpEmailSenderTool()],
        llm=get_llm(),
        **AGENT_DEFAULTS,
    )
