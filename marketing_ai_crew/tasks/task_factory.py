"""
tasks/task_factory.py
One task per agent. Each task has a clear description and expected output.
Tasks are intentionally short for local LLMs (fewer tokens = faster + more reliable).
"""
import os
from datetime import datetime
from crewai import Task

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

def _out(prefix):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{ts}.md"


def content_task(agent, brief):
    return Task(
        description=f"""
Read the brand guidelines first. Then complete this brief: {brief}

Produce:
1. Three Instagram captions (with hashtags, under 150 chars each)
2. One LinkedIn post (200-300 words, professional tone)
3. One Twitter/X post (under 280 chars)
4. Three email subject line options for this topic

Label each section. Keep everything copy-paste ready.
""",
        expected_output="Formatted document with all 4 sections clearly labelled, ready to publish.",
        agent=agent,
        output_file=_out("content"),
    )


def social_task(agent, brief):
    return Task(
        description=f"""
Task: {brief}

Steps:
1. Check the current queue to avoid duplication
2. Create 5 posts for the week (mix: Instagram, LinkedIn, Twitter)
3. Schedule each with platform, content, and posting time
4. Write 2 reply templates for common comments (pricing question, general praise)
""",
        expected_output="5 scheduled posts with platform/time, plus 2 reply templates.",
        agent=agent,
        output_file=_out("social"),
    )


def lead_gen_task(agent, brief):
    return Task(
        description=f"""
Lead generation task: {brief}

Steps:
1. Search for 3 qualified prospects matching our ICP (small business, 5-50 employees)
2. Add each to the CRM (name, company, role, email, notes)
3. Write a personalised cold email for the best prospect
4. Write a 3-step follow-up sequence (Day 1, Day 4, Day 10)
""",
        expected_output="3 CRM contacts, 1 cold email, 3-step follow-up sequence.",
        agent=agent,
        output_file=_out("leads"),
    )


def analytics_task(agent, brief):
    return Task(
        description=f"""
Task: {brief}

Steps:
1. Pull metrics for last 7 days
2. Analyse trends for sessions, conversions, and bounce rate
3. Write a weekly report with:
   - 3-bullet executive summary
   - Key metrics table (with week-over-week change)
   - Top pages performance
   - Traffic source breakdown
   - 3 specific recommendations
""",
        expected_output="Weekly performance report in Markdown with all sections.",
        agent=agent,
        output_file=_out("analytics"),
    )


def email_campaign_task(agent, brief):
    return Task(
        description=f"""
Task: {brief}

Deliverables:
1. A 5-email welcome drip for new free trial users:
   - Day 0: Welcome + quick win
   - Day 2: Feature spotlight
   - Day 5: Social proof
   - Day 8: Handle objection
   - Day 12: Upgrade offer
2. For each email: subject line, preview text, body, CTA
3. One re-engagement email for users inactive 30+ days
""",
        expected_output="Complete email sequence with all 6 emails written out fully.",
        agent=agent,
        output_file=_out("email"),
    )


def ads_task(agent, brief):
    return Task(
        description=f"""
Task: {brief}

Steps:
1. Pull current campaign performance
2. Identify the best and worst performing campaign
3. Create 3 ad copy variations for the best campaign
4. Recommend pausing the worst — label it: HUMAN APPROVAL REQUIRED
5. Write a budget reallocation recommendation
""",
        expected_output="Performance analysis, 3 ad variations, pause recommendation (flagged), budget plan.",
        agent=agent,
        output_file=_out("ads"),
    )


def community_task(agent, brief):
    return Task(
        description=f"""
Task: {brief}

Deliverables:
1. Research 2 potential SaaS partners (complementary, not competitors)
2. Write a partnership outreach email for each
3. Draft a webinar event description (virtual, 60 min)
4. Outline a one-page sponsor prospectus

Label everything: DRAFT — Human review before sending.
""",
        expected_output="2 outreach emails, 1 event description, 1 sponsor outline. All marked as drafts.",
        agent=agent,
        output_file=_out("community"),
    )


def product_marketing_task(agent, brief):
    return Task(
        description=f"""
Task: {brief}

Deliverables:
1. Research 2-3 top competitors online
2. Write a short competitive positioning summary
3. Write a product launch blog post (400-500 words)
4. Write 2 positioning statements for different audience segments
5. Write a LinkedIn feature announcement

Note: Present findings — human team decides final strategy.
""",
        expected_output="Competitive summary, launch blog post, 2 positioning statements, LinkedIn post.",
        agent=agent,
        output_file=_out("product_marketing"),
    )


def pr_task(agent, brief):
    return Task(
        description=f"""
Task: {brief}

Deliverables — ALL marked DRAFT, HUMAN REVIEW REQUIRED:
1. Search for recent brand or competitor mentions
2. Draft one press release (milestone or product news)
3. Create a crisis response template (for: outage, bad review, data issue)
4. Write a media pitch for a relevant tech publication
""",
        expected_output="Press release, crisis template, media pitch — all clearly marked as drafts.",
        agent=agent,
        output_file=_out("pr"),
    )


def brand_strategy_task(agent, brief):
    return Task(
        description=f"""
Task: {brief}

Deliverables — research and options only, no final decisions:
1. Research how 2-3 competitors position themselves
2. Summarise 3 key audience insights from web research
3. Propose 3 potential brand direction options with pros/cons each
4. Brief competitor voice analysis (how do they sound?)

Present options. Human team chooses direction.
""",
        expected_output="Competitor positioning, audience insights, 3 brand options, voice analysis.",
        agent=agent,
        output_file=_out("brand_strategy"),
    )


def email_dispatch_task(agent, brief):
    return Task(
        description=f"""
Task: {brief}

You are the email dispatch specialist. Your ONLY job here is to:
1. Take the provided email content (subject and body)
2. Send it using the SMTP Email Sender tool to all configured recipients
3. Report back the exact number of emails sent and any failures

Input you will receive (already approved by risk agent):
- email_subject: the subject line
- email_body: the body content
- recipients: use the recipient list from the system

Use the SMTP Email Sender tool with a JSON input containing:
  recipients, subject, html_body, text_body, campaign_id

After sending, confirm: how many were sent, how many failed.
""",
        expected_output="JSON result from the SMTP Email Sender: sent count, failed count, and list of any failures.",
        agent=agent,
        output_file=_out("email_dispatch"),
    )


TASK_MAP = {
    "content":           content_task,
    "social":            social_task,
    "leads":             lead_gen_task,
    "analytics":         analytics_task,
    "email":             email_campaign_task,
    "ads":               ads_task,
    "community":         community_task,
    "product_marketing": product_marketing_task,
    "pr":                pr_task,
    "brand_strategy":    brand_strategy_task,
    "email_dispatch":    lambda agent, brief: email_dispatch_task(agent, brief),
}

DEFAULT_BRIEFS = {
    "content":           "Write content for our Acme Automate 2.0 feature launch",
    "social":            "Build next week's social media calendar for our product launch",
    "leads":             "Find 3 prospects in the fintech or e-commerce space",
    "analytics":         "Generate weekly performance report for the past 7 days",
    "email":             "Create onboarding email sequence for new free trial users",
    "ads":               "Review campaign performance and optimise budget allocation",
    "community":         "Find partnership opportunities with complementary SaaS tools",
    "product_marketing": "Launch campaign for Acme Automate 2.0 workflow automation",
    "pr":                "Prepare press materials for our 1000-customer milestone",
    "brand_strategy":    "Research positioning options for SMB-focused SaaS market",
    "email_dispatch":    "Send the risk-approved email campaign to all subscribers",
}


def get_task(agent_name: str, agent, brief: str = ""):
    factory = TASK_MAP.get(agent_name)
    if not factory:
        raise ValueError(f"Unknown agent '{agent_name}'. Choose: {list(TASK_MAP.keys())}")
    return factory(agent, brief or DEFAULT_BRIEFS[agent_name])
