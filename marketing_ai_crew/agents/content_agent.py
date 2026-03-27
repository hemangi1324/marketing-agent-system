"""
agents/content_agent.py
------------------------
Content Agent — the second step in the pipeline.

Responsibilities:
  - Accept strategy context (theme, tone, key messages) from the Strategy Agent
  - Generate email content (subject + body) and social content (Instagram, Twitter)
  - Output a structured ContentOutput (Pydantic)

This agent consolidates the former content_agent + email_campaign_agent into
a single, context-driven specialist.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import logging
from typing import Optional
from dotenv import load_dotenv

from crewai import Agent, Task, Crew
from config.settings import get_llm, AGENT_DEFAULTS
from tools.file_tool import BrandGuidelinesTool, OutputSaverTool
from schemas.content import ContentOutput, EmailContent, SocialContent
from schemas.strategy import StrategyOutput

load_dotenv(override=True)
logger = logging.getLogger("content_agent")


# ── Agent definition ──────────────────────────────────────────────────────────
def get_content_agent() -> Agent:
    """Returns a Content Agent instance."""
    return Agent(
        role="Content and Copy Specialist",
        goal=(
            "Generate complete, on-brand marketing content for every channel: "
            "a compelling email (subject + body) and platform-specific social media posts. "
            "Content must follow the provided strategy direction precisely and align with brand guidelines."
        ),
        backstory=(
            "You are a senior copywriter with 10 years of experience crafting marketing content "
            "for SaaS companies targeting Indian SMBs. You have a gift for writing subject lines "
            "that get opened, emails that build trust, and social captions that drive engagement. "
            "You always read the brand guidelines before writing a single word. "
            "You strictly follow the strategy brief — you do not deviate from the theme, tone, "
            "or key messages provided. You write platform-native content: Instagram is punchy, "
            "Twitter is concise, email is persuasive."
        ),
        tools=[BrandGuidelinesTool(), OutputSaverTool()],
        llm=get_llm(),
        **AGENT_DEFAULTS,
    )


# ── Task builder ──────────────────────────────────────────────────────────────
def _build_content_task_description(
    brief: str,
    strategy: Optional[StrategyOutput],
    campaign_context: str = "",
) -> str:
    strategy_section = (
        strategy.to_context_string() if strategy
        else "No strategy provided — use brand guidelines and the brief directly."
    )
    context_section = (
        f"\n=== PIPELINE CONTEXT ===\n{campaign_context}\n"
        if campaign_context else ""
    )

    return f"""
You are generating all marketing content for the following campaign.

=== CAMPAIGN BRIEF ===
{brief}
{context_section}
{strategy_section}

=== YOUR TASK ===
Step 1: Read the Brand Guidelines tool to understand tone, values and voice.
Step 2: Generate the following:

EMAIL:
  - subject       : Compelling subject line (max 70 chars). Avoid spam words.
  - body          : Full email body (200-400 words). Include greeting, value proposition, CTA.
  - preview_text  : Email preview/preheader text (max 100 chars)

SOCIAL MEDIA:
  - instagram_caption : Caption with relevant hashtags (max 150 chars body + hashtags)
  - twitter_post      : Post under 280 chars. Should standalone without context.
  - linkedin_post     : Professional post (150-250 words) with industry insight angle.
  - subject_line_variants : 3 ALTERNATIVE subject line options (different angles)

CRITICAL RULES:
  - Follow the tone and key messages from the strategy EXACTLY
  - Never use words in the 'do_not_use' list from strategy
  - Make every piece of content feel like it was written by a human expert
  - The email body must NOT just repeat the subject line — build on it
  - DO NOT include any hardcoded real or placeholder usernames (e.g., [Username])
  - DO NOT include website links, URLs, or Call-To-Action (CTA) buttons
  - The content should read naturally without boilerplate template placeholders

Step 3: Return ONLY a valid JSON object — no markdown, no backticks, no extra text.
Use exactly this structure:
{{
  "email_content": {{
    "subject": "<string>",
    "body": "<string>",
    "preview_text": "<string>"
  }},
  "social_content": {{
    "instagram_caption": "<string>",
    "twitter_post": "<string>",
    "linkedin_post": "<string>",
    "subject_line_variants": ["<string>", "<string>", "<string>"]
  }},
  "brand_tone": "<string — detected or applied>"
}}
"""


# ── Main function ─────────────────────────────────────────────────────────────
def run_content_generation(
    brief: str,
    campaign_id: int,
    strategy: Optional[StrategyOutput] = None,
    campaign_context: str = "",
) -> ContentOutput:
    """
    Run the Content Agent and return a structured ContentOutput.

    Args:
        brief            : Campaign brief
        campaign_id      : Campaign identifier (used for output file naming)
        strategy         : StrategyOutput from strategy_agent (optional but recommended)
        campaign_context : Shared state context string for additional guidance

    Returns:
        ContentOutput (Pydantic) — includes email + social content
    """
    agent = get_content_agent()
    task = Task(
        description=_build_content_task_description(brief, strategy, campaign_context),
        expected_output=(
            "A valid JSON object with keys: email_content (subject, body, preview_text), "
            "social_content (instagram_caption, twitter_post, linkedin_post, subject_line_variants), "
            "brand_tone."
        ),
        agent=agent,
    )

    crew = Crew(agents=[agent], tasks=[task], verbose=True)
    raw_output = crew.kickoff()

    # ── Parse JSON ─────────────────────────────────────────────────────────────
    try:
        raw_str = str(raw_output).strip()
        if raw_str.startswith("```"):
            raw_str = raw_str.split("```")[1]
            if raw_str.startswith("json"):
                raw_str = raw_str[4:]
        result_dict = json.loads(raw_str)

        ec = result_dict.get("email_content", {})
        sc = result_dict.get("social_content", {})

        content_output = ContentOutput(
            email_content=EmailContent(
                subject=ec.get("subject", f"Campaign #{campaign_id}"),
                body=ec.get("body", ""),
                preview_text=ec.get("preview_text"),
            ),
            social_content=SocialContent(
                instagram_caption=sc.get("instagram_caption"),
                twitter_post=sc.get("twitter_post"),
                linkedin_post=sc.get("linkedin_post"),
                subject_line_variants=sc.get("subject_line_variants", []),
            ),
            brand_tone=result_dict.get("brand_tone"),
        )

    except Exception as e:
        logger.warning("Content agent output parse failed: %s. Using fallback.", e)
        # Fallback — extract plain text for backward compatibility
        raw_str = str(raw_output).strip()
        content_output = ContentOutput(
            email_content=EmailContent(
                subject=f"Campaign #{campaign_id} Update",
                body=raw_str[:2000],
            ),
            social_content=SocialContent(),
        )

    logger.info("Content generation complete — subject: %s", content_output.email_content.subject)
    return content_output


# ── Quick test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    output = run_content_generation(
        brief="Diwali sale — 30% off all Acme SaaS plans for the festival week",
        campaign_id=99,
        campaign_context="Target audience: SMB owners in India, 25-45."
    )
    print("\n── Content Output ──────────────────────────────────")
    print(f"Subject : {output.email_content.subject}")
    print(f"Body    : {output.email_content.body[:300]}...")
    print(f"Instagram: {output.social_content.instagram_caption}")
    print(f"Twitter  : {output.social_content.twitter_post}")
