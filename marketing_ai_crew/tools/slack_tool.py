import os
import requests
import json
from dotenv import load_dotenv
from crewai.tools import tool


SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")


def _format_slack_message(campaign_id: int, scores_dict: dict, flag_reason: str = None) -> dict:
    """
    Formats the Slack message payload.
    Returns a dict ready to be sent as JSON to the webhook.
    """

    brand_safety        = scores_dict.get("brand_safety", "N/A")
    legal_risk          = scores_dict.get("legal_risk", "N/A")
    cultural_sensitivity = scores_dict.get("cultural_sensitivity", "N/A")

    # Build a score line — mark any score below 5 with a red cross
    def score_line(label, value):
        if isinstance(value, (int, float)) and value < 5:
            return f"*{label}:* {value}/10  ❌  ← FAILED"
        return f"*{label}:* {value}/10  ✅"

    reason_text = f"\n*Flag Reason:* {flag_reason}" if flag_reason else ""

    message = (
        f"🚨 *RISK ALERT — Campaign #{campaign_id}*\n"
        f"One or more risk scores fell below the safe threshold (5/10).\n"
        f"Human review is required before this campaign goes live.\n\n"
        f"{score_line('Brand Safety', brand_safety)}\n"
        f"{score_line('Legal Risk', legal_risk)}\n"
        f"{score_line('Cultural Sensitivity', cultural_sensitivity)}"
        f"{reason_text}"
    )

    return {
        "text": message  # Slack renders *text* as bold in this format
    }


def send_slack_alert(campaign_id: int, scores_dict: dict, flag_reason: str = None) -> str:
    """
    Sends a Slack alert when risk scores are below threshold.

    Args:
        campaign_id  : ID of the campaign that failed the risk gate
        scores_dict  : dict with keys brand_safety, legal_risk, cultural_sensitivity
        flag_reason  : optional string explaining why it was flagged

    Returns:
        "ok" if Slack accepted the message, error string otherwise
    """

    if not SLACK_WEBHOOK_URL:
        return "ERROR: SLACK_WEBHOOK_URL not set in .env"

    payload = _format_slack_message(campaign_id, scores_dict, flag_reason)

    try:
        response = requests.post(
            SLACK_WEBHOOK_URL,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=10
        )

        if response.status_code == 200 and response.text == "ok":
            return "ok"
        else:
            return f"ERROR: Slack returned {response.status_code} — {response.text}"

    except requests.exceptions.Timeout:
        return "ERROR: Slack webhook request timed out"

    except requests.exceptions.RequestException as e:
        return f"ERROR: {str(e)}"


# ── CrewAI Tool wrapper ──────────────────────────────────────────────────────
# The Risk Agent imports and uses this directly as a CrewAI tool.

@tool("Send Slack Risk Alert")
def slack_alert_tool(input_str: str) -> str:
    """
    Sends a Slack alert for a risky campaign.
    Input must be a JSON string with keys:
      campaign_id (int), scores (dict), flag_reason (str, optional)

    Example input:
      {"campaign_id": 12, "scores": {"brand_safety": 3, "legal_risk": 8, "cultural_sensitivity": 4}, "flag_reason": "Low cultural sensitivity score"}
    """
    try:
        data = json.loads(input_str)
        campaign_id  = data["campaign_id"]
        scores       = data["scores"]
        flag_reason  = data.get("flag_reason", None)

        result = send_slack_alert(campaign_id, scores, flag_reason)
        return f"Slack alert result: {result}"

    except (json.JSONDecodeError, KeyError) as e:
        return f"ERROR parsing input: {str(e)}. Expected JSON with campaign_id, scores, flag_reason."


# ── Quick test (run this file directly to verify your webhook works) ─────────
if __name__ == "__main__":
    test_scores = {
        "brand_safety": 3,
        "legal_risk": 8,
        "cultural_sensitivity": 4
    }
    result = send_slack_alert(
        campaign_id=99,
        scores_dict=test_scores,
        flag_reason="Brand safety and cultural sensitivity below threshold"
    )
    print(f"Test result: {result}")