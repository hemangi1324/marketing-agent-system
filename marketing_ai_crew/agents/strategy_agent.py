"""
agents/strategy_agent.py
-------------------------
Strategy Agent — the first step in the pipeline.

Responsibilities:
  - Read campaign brief and historical context (from DB)
  - Determine campaign theme, tone, and key messages
  - Output a StrategyOutput that guides the Content Agent

This agent is context-aware: it reads past campaign post-mortems and
festival memory to make data-driven strategic decisions, not just LLM guesses.
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
from tools.search_tool import DuckDuckGoSearchTool
from tools.file_tool import BrandGuidelinesTool, OutputSaverTool
from schemas.strategy import StrategyInput, StrategyOutput

load_dotenv(override=True)
logger = logging.getLogger("strategy_agent")


# ── Agent definition ───────────────────────────────────────────────────────────
def get_strategy_agent() -> Agent:
    """
    Returns a Strategy Agent instance.
    Lazily creates — caller caches if needed.
    """
    return Agent(
        role="Campaign Strategy Director",
        goal=(
            "Analyse the campaign brief and all available context (historical performance, "
            "festival data, brand guidelines) to define a precise campaign strategy. "
            "Output a structured strategy: theme, tone, key messages, and platform priorities."
        ),
        backstory=(
            "You are a senior marketing strategist with 12 years of experience running "
            "campaigns for consumer brands in India and globally. You combine data from "
            "past campaign performance, seasonal trends, and brand guidelines to create "
            "strategies that are specific, actionable, and grounded in evidence. "
            "You never produce generic strategies — every decision cites a reason. "
            "You read historical context carefully and use it to avoid past mistakes."
        ),
        tools=[BrandGuidelinesTool(), DuckDuckGoSearchTool(), OutputSaverTool()],
        llm=get_llm(),
        **AGENT_DEFAULTS,
    )


# ── Task builder ──────────────────────────────────────────────────────────────
def _build_strategy_task_description(inp: StrategyInput) -> str:
    hist = inp.historical_context or "No previous campaigns found for this context."
    competitor = inp.competitor_context or "No competitor data provided."
    audience = inp.target_audience or "General consumer audience."
    festival_line = f"Festival Context: {inp.festival_tag}" if inp.festival_tag else "No specific festival context."

    return f"""
You are creating the strategy for a new marketing campaign.

=== CAMPAIGN BRIEF ===
{inp.brief}

=== CONTEXT ===
{festival_line}
Target Audience: {audience}

=== HISTORICAL PERFORMANCE (learn from this) ===
{hist}

=== COMPETITOR LANDSCAPE ===
{competitor}

=== YOUR TASK ===
1. Read the brand guidelines using the Brand Guidelines tool.
2. Based on all the above, define a campaign strategy with exactly these fields:
   - campaign_theme : A single compelling headline concept (max 15 words)
   - tone           : Brand tone e.g. "urgent & warm", "playful & witty", "professional & trustworthy"
   - key_messages   : List of 3-5 core messages the campaign must convey
   - platform_priorities : Dict mapping platform to content direction
                           e.g. {{"instagram": "visual-first, lifestyle focus", "email": "urgency + CTA"}}
   - audience_insight : One key insight about the target audience that should shape the copy
   - do_not_use     : List of words/phrases to avoid based on brand guidelines or past failures

3. Return ONLY a valid JSON object — no markdown, no extra text.
   Use exactly this structure:
   {{
     "campaign_theme": "<string>",
     "tone": "<string>",
     "key_messages": ["<string>", ...],
     "platform_priorities": {{"instagram": "...", "email": "...", "twitter": "..."}},
     "audience_insight": "<string>",
     "do_not_use": ["<word>", ...]
   }}
"""


# ── Main function ───────────────────────────────────────────────────────────
def run_strategy(
    brief: str,
    campaign_id: int,
    festival_tag: Optional[str] = None,
    target_audience: Optional[str] = None,
    historical_context: Optional[str] = None,
) -> StrategyOutput:
    """
    Run the Strategy Agent and return a structured StrategyOutput.

    Args:
        brief              : Campaign brief / goal
        campaign_id        : Campaign identifier
        festival_tag       : Optional festival context
        target_audience    : Optional audience description
        historical_context : Pre-built historical context string from campaign_store

    Returns:
        StrategyOutput (Pydantic)
    """
    inp = StrategyInput(
        brief=brief,
        festival_tag=festival_tag,
        target_audience=target_audience,
        historical_context=historical_context,
    )

    agent = get_strategy_agent()
    task = Task(
        description=_build_strategy_task_description(inp),
        expected_output=(
            "A valid JSON object with keys: campaign_theme, tone, key_messages, "
            "platform_priorities, audience_insight, do_not_use."
        ),
        agent=agent,
    )

    crew = Crew(agents=[agent], tasks=[task], verbose=True)
    raw_output = crew.kickoff()

    # ── Parse JSON ────────────────────────────────────────────────────────────
    try:
        raw_str = str(raw_output).strip()
        if raw_str.startswith("```"):
            raw_str = raw_str.split("```")[1]
            if raw_str.startswith("json"):
                raw_str = raw_str[4:]
        result_dict = json.loads(raw_str)
        strategy_output = StrategyOutput.from_dict(result_dict)

    except (json.JSONDecodeError, IndexError, Exception) as e:
        logger.warning("Strategy agent output parse failed: %s. Using safe defaults.", e)
        strategy_output = StrategyOutput(
            campaign_theme=f"Campaign: {brief[:60]}",
            tone="professional and engaging",
            key_messages=["Deliver value to customers", "Build brand trust", "Drive action"],
            platform_priorities={"email": "clear CTA", "instagram": "visual-first"},
        )

    logger.info("Strategy complete — theme: %s", strategy_output.campaign_theme)
    return strategy_output


# # ── Quick test ────────────────────────────────────────────────────────────────
# if __name__ == "__main__":
#     result = run_strategy(
#         brief="Diwali promotional campaign for Acme SaaS — 30% discount for the festival week",
#         campaign_id=99,
#         festival_tag="diwali",
#         target_audience="SMB owners in India, 25-45 years old",
#     )
#     print("\n── Strategy Output ──────────────────────────────────")
#     print(json.dumps(result.model_dump(), indent=2))
