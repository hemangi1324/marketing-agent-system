import os
import requests
import json
from dotenv import load_dotenv
from crewai.tools import tool

load_dotenv(override=True)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID")


def send_telegram_message(text: str) -> str:
    """
    Sends a plain text message to the configured Telegram chat.

    Args:
        text : the message to send

    Returns:
        "ok" if successful, error string otherwise
    """

    if not TELEGRAM_BOT_TOKEN:
        return "ERROR: TELEGRAM_BOT_TOKEN not set in .env"
    if not TELEGRAM_CHAT_ID:
        return "ERROR: TELEGRAM_CHAT_ID not set in .env"

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id"    : TELEGRAM_CHAT_ID,
        "text"       : text,
        "parse_mode" : "Markdown"   # allows *bold* and _italic_ in messages
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        data = response.json()

        if data.get("ok"):
            return "ok"
        else:
            return f"ERROR: Telegram returned — {data.get('description', 'unknown error')}"

    except requests.exceptions.Timeout:
        return "ERROR: Telegram request timed out"

    except requests.exceptions.RequestException as e:
        return f"ERROR: {str(e)}"


# ── CrewAI Tool wrapper ───────────────────────────────────────────────────────
@tool("Send Telegram Ad")
def telegram_ad_tool(ad_copy: str) -> str:
    """
    Sends a Telegram advertisement message to the configured Telegram channel or chat.
    Input should be the complete ad copy text ready to be sent as a Telegram message.
    Keep it punchy, 2-4 lines, with emojis. Markdown supported (*bold*, _italic_).

    Example input:
      🔥 *Diwali Sale is HERE!*
      Grab 50% off everything — today only.
      👉 Shop now: acmesaas.com
    """
    result = send_telegram_message(ad_copy)

    if result == "ok":
        return "Telegram ad sent successfully."
    else:
        return f"Failed to send Telegram ad: {result}"


# ── Quick test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    test_message = (
        "🔥 *Acme Automate 2.0 is LIVE!*\n"
        "Small businesses — save 10+ hours a week, guaranteed.\n"
        "Enterprise power at a small business price.\n"
        "👉 Try it free: acmesaas.com"
    )
    result = send_telegram_message(test_message)
    print(f"Test result: {result}")