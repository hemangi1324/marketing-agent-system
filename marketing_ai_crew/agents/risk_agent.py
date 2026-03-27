import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
from dotenv import load_dotenv
from crewai import Agent, Task, Crew

from tools.slack_tool import slack_alert_tool

load_dotenv(override=True)

# ── DB persistence (replaces old no-op stubs) ─────────────────────────────────
from database import campaign_store

def save_risk(output_id, scores_dict):
    """Persist risk scores to the campaign DB."""
    if output_id is not None:
        campaign_store.save_risk_result(int(output_id), scores_dict)

def save_reasoning(agent_name, thought, campaign_id):
    """Log agent reasoning step to audit trail."""
    campaign_store.log_agent_step(
        campaign_id=campaign_id or 0,
        agent_name=agent_name,
        status="success",
        output_summary=thought[:200] if thought else None,
    )


# ── LLM setup ────────────────────────────────────────────────────────────────
from config.settings import get_llm
llm = get_llm()

# ── Agent definition ─────────────────────────────────────────────────────────
risk_agent = Agent(
    role="Brand Safety & Risk Analyst",
    goal=(
        "Score marketing content on brand safety, legal risk, and cultural "
        "sensitivity. Flag anything that could harm the brand or cause legal "
        "or cultural offence. Return a structured JSON risk report."
    ),
    backstory=(
        "You are a senior brand safety analyst with 15 years of experience "
        "reviewing marketing campaigns for Fortune 500 companies. You have "
        "deep knowledge of advertising standards, legal compliance (ASCI, "
        "consumer protection laws), and cultural sensitivities across Indian "
        "and global markets. You are thorough, conservative, and always "
        "explain your reasoning clearly. You never approve content you are "
        "unsure about."
    ),
    tools=[slack_alert_tool],
    llm=llm,
    verbose=True,
    allow_delegation=False
)

# ── Core scoring prompt ───────────────────────────────────────────────────────
def _build_task_description(content_dict: dict, campaign_id: int) -> str:
    return f"""
You are reviewing the following marketing campaign content for Campaign #{campaign_id}.

--- CONTENT TO REVIEW ---
Email Subject   : {content_dict.get("email_subject", "N/A")}
Email Body      : {content_dict.get("email_body", "N/A")}
Instagram Caption: {content_dict.get("instagram_caption", "N/A")}
Twitter Post    : {content_dict.get("twitter_post", "N/A")}
--- END OF CONTENT ---

Your job:
1. Score the content on these 3 dimensions, each from 0 to 10:
   - brand_safety       : Does this protect brand reputation? (10 = perfectly safe)
   - legal_risk         : Is this legally compliant? (10 = no legal risk at all)
   - cultural_sensitivity: Is this culturally respectful for Indian audiences? (10 = fully respectful)

2. Apply these rules:
   - All scores >= 7  → green_light = true, no alert needed
   - Any score 5 or 6 → green_light = true, but note a warning in explanation
   - Any score < 3   → green_light = false, you MUST call the Send Slack Risk Alert tool
   

3. If green_light is false, call the Send Slack Risk Alert tool with this JSON:
   {{"campaign_id": {campaign_id}, "scores": {{"brand_safety": <score>, "legal_risk": <score>, "cultural_sensitivity": <score>}}, "flag_reason": "<one line reason>"}}

4. Return ONLY a valid JSON object — no extra text, no markdown, no backticks.
   Use exactly this structure:
   {{
     "brand_safety": <int>,
     "legal_risk": <int>,
     "cultural_sensitivity": <int>,
     "green_light": <bool>,
     "flag_reason": <string or null>,
     "explanation": "<2-3 sentences explaining the scores>"
   }}
"""

# ── Main function called by the crew ─────────────────────────────────────────
def run_risk_check(content_dict: dict, campaign_id: int, output_id: int = None) -> dict:
    
    task = Task(
        description=_build_task_description(content_dict, campaign_id),
        expected_output=(
            "A valid JSON object with keys: brand_safety, legal_risk, "
            "cultural_sensitivity, green_light, flag_reason, explanation."
        ),
        agent=risk_agent
    )

    crew = Crew(
        agents=[risk_agent],
        tasks=[task],
        verbose=True
    )

    raw_output = crew.kickoff()

    try:
        raw_str = str(raw_output).strip()
        if raw_str.startswith("```"):
            raw_str = raw_str.split("```")[1]
            if raw_str.startswith("json"):
                raw_str = raw_str[4:]
        scores = json.loads(raw_str)

    except (json.JSONDecodeError, IndexError) as e:
        scores = {
            "brand_safety": 0,
            "legal_risk": 0,
            "cultural_sensitivity": 0,
            "green_light": False,
            "flag_reason": f"Risk agent output could not be parsed: {str(e)}",
            "explanation": "Parsing error — campaign blocked as a precaution."
        }
        
    if not scores.get("green_light", True):
        print("🚨 Triggering Slack alert...")

        slack_alert_tool.run(json.dumps({
        "campaign_id": campaign_id,
        "scores": {
        "brand_safety": scores.get("brand_safety"),
        "legal_risk": scores.get("legal_risk"),
        "cultural_sensitivity": scores.get("cultural_sensitivity"),
    },
    "flag_reason": scores.get("flag_reason", "Risk detected")
}))
    save_reasoning(agent_name="RiskAgent", thought=scores.get("explanation", ""), campaign_id=campaign_id)
    save_risk(output_id=output_id, scores_dict=scores)

    return scores

# # ── Quick test ────────────────────────────────────────────────────────────────
# if __name__ == "__main__":
#     sample_content = {
#         "email_subject": "Exclusive Diwali Sale — 50% OFF everything!",
#         "email_body": (
#             "Dear Customer you are stupid and mad idiot celebrate Diwali with our biggest sale ever. "
#             "Shop now and get 50% off all products. Limited time offer!"
#         ),
#         "instagram_caption": "✨ Diwali vibes + massive savings = perfect combo! #Diwali #Sale #Deals",
#         "twitter_post": "🪔 Big Diwali Sale is LIVE! 50% off everything. Shop now → [link] #Diwali #Offers"
#     }

#     result = run_risk_check(content_dict=sample_content, campaign_id=99, output_id=None)

#     print("\n── Risk Report ──────────────────────────────")
#     print(json.dumps(result, indent=2))
#     print(f"\nGreen light: {result.get('green_light')}")


# ── Structured Pydantic variant ───────────────────────────────────────────────
def run_risk_check_structured(risk_input, campaign_id: int = None) -> "RiskOutput":
    """
    Structured wrapper — accepts RiskInput, returns RiskOutput.
    Maintains full backward compatibility: delegates to run_risk_check().

    Args:
        risk_input  : schemas.risk.RiskInput instance
        campaign_id : optional override (uses risk_input.campaign_id if not set)

    Returns:
        schemas.risk.RiskOutput (Pydantic)
    """
    from schemas.risk import RiskInput, RiskOutput

    cid = campaign_id or risk_input.campaign_id
    content_dict = risk_input.to_content_dict()
    raw_result = run_risk_check(
        content_dict=content_dict,
        campaign_id=cid,
        output_id=cid,
    )
    return RiskOutput.from_dict(raw_result)
