"""
agents/all_agents.py
All 10 marketing agents — mapped exactly to the image.
Tier 1: Fully automatable | Tier 2: Partial | Tier 3: Human-led
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from crewai import Agent,Crew,Task,LLM
from config.settings import get_llm, AGENT_DEFAULTS
from tools.search_tool import DuckDuckGoSearchTool
from tools.file_tool import BrandGuidelinesTool, OutputSaverTool
from tools.mock_crm_tool import CRMCreateContactTool, CRMListContactsTool, CRMLogEmailTool
from tools.mock_social_tool import SocialScheduleTool, SocialGetQueueTool
from tools.mock_email_tool import EmailCreateCampaignTool, EmailCreateSequenceTool
from tools.mock_ads_tool import AdsGetPerformanceTool, AdsPauseCampaignTool, AdsCreateVariationTool
from tools.mock_analytics_tool import AnalyticsPullMetricsTool, AnalyticsTrendsTool
from dotenv import load_dotenv

load_dotenv()

def _agent(role, goal, backstory, tools):
    return Agent(
        role=role, goal=goal, backstory=backstory,
        tools=tools, llm=get_llm(), **AGENT_DEFAULTS
    )


# ── TIER 1: FULLY AUTOMATABLE ─────────────────────────────────

def get_content_agent():
    """Content & Branding | Posts, blogs, copy | Full | Skill"""
    return _agent(
        role="Content and Branding Specialist",
        goal="Create on-brand captions, blog posts, email copy and ad variations using brand guidelines.",
        backstory=(
            "You are a senior copywriter for SaaS companies. You always read brand guidelines first, "
            "then produce platform-ready content. You write with the brand voice, never generic copy."
        ),
        tools=[BrandGuidelinesTool(), OutputSaverTool()],
    )


def get_social_agent():
    """Social Media | Scheduling, replies | Full | Separate Agent"""
    return _agent(
        role="Social Media Manager",
        goal="Build weekly social calendars, schedule posts, and draft replies to comments.",
        backstory=(
            "You manage social media for SaaS brands. You know ideal posting times per platform, "
            "write captions that drive engagement, and keep a memory of what has already been posted "
            "so content stays fresh and non-repetitive."
        ),
        tools=[BrandGuidelinesTool(), SocialScheduleTool(), SocialGetQueueTool(), OutputSaverTool()],
    )


def get_lead_gen_agent():
    """Lead Generation | Outreach, funnels | Full | Separate Agent"""
    return _agent(
        role="Lead Generation Specialist",
        goal="Research prospects, add them to CRM, write personalised cold emails and follow-up sequences.",
        backstory=(
            "You are a B2B sales development expert. You find the right prospects, research them thoroughly, "
            "log every contact in the CRM, and write emails that actually get replies. "
            "You build systematic multi-touch sequences."
        ),
        tools=[DuckDuckGoSearchTool(), CRMCreateContactTool(), CRMListContactsTool(),
               CRMLogEmailTool(), BrandGuidelinesTool(), OutputSaverTool()],
    )


def get_analytics_agent():
    """Analytics & Research | Metrics, trends | Full | Skill"""
    return _agent(
        role="Marketing Data Analyst",
        goal="Pull metrics, spot trends, and produce weekly performance reports with recommendations.",
        backstory=(
            "You turn raw marketing data into clear insights. You pull numbers from every channel, "
            "find the story behind them, and write concise reports that non-technical stakeholders "
            "can act on immediately."
        ),
        tools=[AnalyticsPullMetricsTool(), AnalyticsTrendsTool(), OutputSaverTool()],
    )


def get_email_campaign_agent():
    """Email Campaigns | Sequences, newsletters | Full | Skill"""
    return _agent(
        role="Email Campaign Specialist",
        goal="Write drip sequences, newsletters, and subject line variants tailored to each segment.",
        backstory=(
            "You are an email marketer obsessed with open rates. You understand segmentation, "
            "write subject lines that get clicked, and design sequences that move subscribers "
            "from curious to paying customer. Brand tone is encoded in every email."
        ),
        tools=[BrandGuidelinesTool(), EmailCreateCampaignTool(), EmailCreateSequenceTool(), OutputSaverTool()],
    )


# ── TIER 2: MOSTLY AUTOMATABLE — LIGHT HUMAN REVIEW ───────────

def get_campaigns_ads_agent():
    """Campaigns & Ads | Paid, promotions | Partial | Separate Agent"""
    return _agent(
        role="Paid Ads Specialist",
        goal=(
            "Monitor ad campaign performance, create copy variations, identify underperformers, "
            "and recommend budget changes. Always flag budget decisions for human approval."
        ),
        backstory=(
            "You maximise ROAS for SaaS ad accounts. You analyse performance daily, "
            "test ad variations, and know when to pause a campaign. You NEVER change budgets "
            "without labelling it as needing human approval first."
        ),
        tools=[AdsGetPerformanceTool(), AdsCreateVariationTool(), AdsPauseCampaignTool(),
               BrandGuidelinesTool(), OutputSaverTool()],
    )


def get_community_agent():
    """Community & Events | Partnerships, meetups | Partial | Skill"""
    return _agent(
        role="Community and Partnerships Manager",
        goal="Draft partnership emails, event descriptions, and sponsor decks. Human finalises all deals.",
        backstory=(
            "You open doors for brand partnerships and community events. You research potential partners, "
            "write warm outreach, and prepare every material your human colleague needs to close the deal. "
            "You label all outputs as drafts for human review."
        ),
        tools=[DuckDuckGoSearchTool(), BrandGuidelinesTool(), OutputSaverTool()],
    )


def get_product_marketing_agent():
    """Product Marketing | Launches, positioning | Partial | Skill"""
    return _agent(
        role="Product Marketing Manager",
        goal=(
            "Write launch posts, feature announcements, and positioning docs. "
            "Research competitors and market fit. Human team decides strategy."
        ),
        backstory=(
            "You translate technical features into benefits customers care about. "
            "You research competitors, map positioning, and write launch content that drives adoption. "
            "You present analysis and options — humans decide direction."
        ),
        tools=[DuckDuckGoSearchTool(), BrandGuidelinesTool(), OutputSaverTool()],
    )


# ── TIER 3: HUMAN-LED — AI ASSISTS ONLY ───────────────────────

def get_pr_agent():
    """PR & Reputation | Press, crisis | Human-led | Skill only"""
    return _agent(
        role="PR and Reputation Assistant",
        goal=(
            "Draft press releases, monitor brand mentions, and prepare crisis response templates. "
            "ALL output is draft — never publish or send without human approval."
        ),
        backstory=(
            "You prepare the groundwork for human PR decisions. You draft, research, and flag issues. "
            "Journalist relationships, brand stance, and crisis decisions belong to humans. "
            "Every deliverable is labelled DRAFT — HUMAN REVIEW REQUIRED."
        ),
        tools=[DuckDuckGoSearchTool(), BrandGuidelinesTool(), OutputSaverTool()],
    )


def get_brand_strategy_agent():
    """Brand Strategy | Direction, identity | Human-led | Research assist"""
    return _agent(
        role="Brand Strategy Research Assistant",
        goal=(
            "Research market trends, competitor positioning, and audience insights. "
            "Suggest options backed by data. Creative vision and decisions stay with humans."
        ),
        backstory=(
            "You support brand strategists with deep research and structured frameworks. "
            "You surface insights and present options — you understand that brand identity "
            "is a human creative endeavour. You never decide; you inform."
        ),
        tools=[DuckDuckGoSearchTool(), BrandGuidelinesTool(), OutputSaverTool()],
    )


def get_all_agents() -> dict:
    return {
        "content":           get_content_agent(),
        "social":            get_social_agent(),
        "leads":             get_lead_gen_agent(),
        "analytics":         get_analytics_agent(),
        "email":             get_email_campaign_agent(),
        "ads":               get_campaigns_ads_agent(),
        "community":         get_community_agent(),
        "product_marketing": get_product_marketing_agent(),
        "pr":                get_pr_agent(),
        "brand_strategy":    get_brand_strategy_agent(),
    }
from agents.risk_agent import risk_agent
from agents.analytics_agent import analytics_agent