import sys
import os
print("RUNNING ANALYTICS AGENT FILE")
# Fix module resolution — must be before any local imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from dotenv import load_dotenv

from crewai import Agent, Task, Crew

load_dotenv()

# ── TODO: swap these 2 lines when M2 finishes db/session.py ─────────────────
# from db.session import save_memory, save_reasoning
def save_memory(campaign_id, festival_tag, mortem_dict): pass
def save_reasoning(agent_name, thought, campaign_id): pass
# ─────────────────────────────────────────────────────────────────────────────


# ── LLM setup ────────────────────────────────────────────────────────────────
from config.settings import get_llm
llm = get_llm()

# ── Agent definition ─────────────────────────────────────────────────────────
analytics_agent = Agent(
    role="Campaign Performance Analyst",
    goal=(
        "Analyse marketing campaign performance metrics before and after a "
        "healing attempt. Decide if the campaign has recovered. Write a "
        "detailed post-mortem so future campaigns can learn from this one."
    ),
    backstory=(
        "You are a data-driven marketing analyst with 10 years of experience "
        "measuring campaign effectiveness for e-commerce brands in India. "
        "You specialise in diagnosing why campaigns underperform and turning "
        "those lessons into actionable recommendations. You are precise, "
        "honest, and never sugarcoat results. A campaign is only healed when "
        "CTR reaches 1% or above — nothing less counts as success."
    ),
    llm=llm,
    verbose=True,
    allow_delegation=False
)


# ── Core analysis prompt ──────────────────────────────────────────────────────
def _build_task_description(
    campaign_id: int,
    attempt: int,
    old_metrics: dict,
    new_metrics: dict,
    festival_tag: str = None
) -> str:

    festival_line = f"Festival context: {festival_tag}" if festival_tag else "No festival context provided."

    return f"""
You are analysing the performance of Campaign #{campaign_id} after healing attempt #{attempt}.

--- METRICS ---
Before this attempt:
  CTR        : {old_metrics.get("ctr", "N/A")}%
  Open Rate  : {old_metrics.get("open_rate", "N/A")}%

After this attempt:
  CTR        : {new_metrics.get("ctr", "N/A")}%
  Open Rate  : {new_metrics.get("open_rate", "N/A")}%

{festival_line}
--- END METRICS ---

Your job:
1. Determine if the campaign is healed:
   - healed = true ONLY if new CTR >= 1.0%
   - healed = false if new CTR < 1.0%

2. Determine if it improved from the last attempt:
   - improved_from_last = true if new CTR > old CTR
   - improved_from_last = false otherwise

3. Write a post-mortem with these 4 fields:
   - what_worked    : what change likely caused any improvement (be specific)
   - what_failed    : what still is not working and why
   - market_context : any seasonal or competitive context that affected results
   - recommendation : the single most important change for the next attempt

4. Return ONLY a valid JSON object — no extra text, no markdown, no backticks.
   Use exactly this structure:
   {{
     "healed": <bool>,
     "new_ctr": <float>,
     "new_open_rate": <float>,
     "improved_from_last": <bool>,
     "post_mortem": {{
       "what_worked": "<specific observation>",
       "what_failed": "<specific observation>",
       "market_context": "<context>",
       "recommendation": "<single actionable recommendation>"
     }}
   }}
"""


# ── Main function called by the self-healing loop ─────────────────────────────
def run_analytics(
    campaign_id: int,
    attempt: int,
    old_metrics: dict,
    new_metrics: dict,
    festival_tag: str = None
) -> dict:
    """
    Runs the Analytics Agent after a healing attempt.

    Args:
        campaign_id  : int — ID of the campaign being analysed
        attempt      : int — which healing attempt this is (1, 2, or 3)
        old_metrics  : dict with keys ctr, open_rate (before this attempt)
        new_metrics  : dict with keys ctr, open_rate (after this attempt)
        festival_tag : str — e.g. "diwali", "valentines" (optional)

    Returns:
        dict matching the analytics agent output schema
    """

    task = Task(
        description=_build_task_description(
            campaign_id, attempt, old_metrics, new_metrics, festival_tag
        ),
        expected_output=(
            "A valid JSON object with keys: healed, new_ctr, new_open_rate, "
            "improved_from_last, post_mortem."
        ),
        agent=analytics_agent
    )

    crew = Crew(
        agents=[analytics_agent],
        tasks=[task],
        verbose=True
    )

    raw_output = crew.kickoff()

    # ── Parse the JSON output ─────────────────────────────────────────────────
    try:
        raw_str = str(raw_output).strip()

        # Strip markdown fences if the model added them anyway
        if raw_str.startswith("```"):
            raw_str = raw_str.split("```")[1]
            if raw_str.startswith("json"):
                raw_str = raw_str[4:]

        result = json.loads(raw_str)

    except (json.JSONDecodeError, IndexError) as e:
        # Fallback — fail safe, mark as not healed
        result = {
            "healed": False,
            "new_ctr": new_metrics.get("ctr", 0.0),
            "new_open_rate": new_metrics.get("open_rate", 0.0),
            "improved_from_last": False,
            "post_mortem": {
                "what_worked": "Unknown — analytics parsing failed",
                "what_failed": f"Could not parse agent output: {str(e)}",
                "market_context": "Unknown",
                "recommendation": "Retry with cleaner content structure"
            }
        }

    # ── Save to DB and memory (no-op until M2 is ready) ──────────────────────
    save_reasoning(
        agent_name="AnalyticsAgent",
        thought=json.dumps(result.get("post_mortem", {})),
        campaign_id=campaign_id
    )

    # Only save memory if we have a festival tag — memory is festival-scoped
    if festival_tag:
        save_memory(
            campaign_id=campaign_id,
            festival_tag=festival_tag,
            mortem_dict=result.get("post_mortem", {})
        )

    return result


# ── Quick test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":

    # Simulating: campaign was at 0.4% CTR, after healing attempt it's at 0.7%
    # Still not healed (need 1%) but improved
    old = {"ctr": 0.4, "open_rate": 9.1}
    new = {"ctr": 0.7, "open_rate": 11.2}

    result = run_analytics(
        campaign_id=99,
        attempt=1,
        old_metrics=old,
        new_metrics=new,
        festival_tag="diwali"
    )

    print("\n── Analytics Report ─────────────────────────")
    print(json.dumps(result, indent=2))
    print(f"\nHealed      : {result.get('healed')}")
    print(f"Improved    : {result.get('improved_from_last')}")
    print(f"New CTR     : {result.get('new_ctr')}%")