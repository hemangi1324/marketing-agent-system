"""
scheduler/campaign_events.py
-----------------------------
Define your scheduled email campaigns here.

Each entry in CAMPAIGN_EVENTS is a dict with:
    id          — unique identifier (string)
    name        — human-readable campaign name
    send_date   — date to trigger the campaign (YYYY-MM-DD)
                  The scheduler will fire on or after this date (once per day check)
    brief       — task brief sent to the content agent
    campaign_id — numeric ID passed to the risk agent and email logs
    campaign_type — optional filter passed to get_recipients() (e.g. "newsletter")

HOW TO ADD A NEW CAMPAIGN:
    Just append a new dict to the list below. Save the file.
    The scheduler picks it up automatically on its next poll.

HOW DATES WORK:
    The scheduler runs once per day. It checks if today >= send_date.
    It will NOT fire the same campaign twice (tracks sent campaigns in
    outputs/scheduler_state.json).
"""

from datetime import date

CAMPAIGN_EVENTS = [
    {
        "id":            "camp-001",
        "name":          "Product Launch Announcement",
        "send_date":     "2026-04-01",          # ← Change to your desired fire date (YYYY-MM-DD)
        "brief":         "Write a product launch email for Acme Automate 2.0 — our new workflow automation feature. Highlight 3 key benefits: saves 5 hours/week, integrates with 50+ tools, and works with no setup.",
        "campaign_id":   1,
        "campaign_type": None,                  # None = all recipients
    },
    {
        "id":            "camp-002",
        "name":          "Monthly Newsletter — April",
        "send_date":     "2026-04-05",
        "brief":         "Write our April newsletter: share 3 product tips, one customer success story, and an upcoming webinar invite.",
        "campaign_id":   2,
        "campaign_type": "newsletter",
    },
    {
        "id":            "camp-003",
        "name":          "Summer Sale Campaign",
        "send_date":     "2026-05-15",
        "brief":         "Write a compelling summer sale email announcing 30% off annual plans. Create urgency with a 7-day deadline.",
        "campaign_id":   3,
        "campaign_type": None,
    },
    # ── Add more campaigns below ──────────────────────────────────────────────
    # {
    #     "id":            "camp-004",
    #     "name":          "Your Campaign Name",
    #     "send_date":     "2026-06-01",
    #     "brief":         "Describe what the email should contain...",
    #     "campaign_id":   4,
    #     "campaign_type": None,
    # },
]


def get_due_campaigns(reference_date: date = None) -> list:
    """
    Return campaigns whose send_date is today or in the past.

    Args:
        reference_date: date to compare against (default: today)

    Returns:
        List of CampaignEvent dicts that are due for sending.
    """
    today = reference_date or date.today()
    due   = []
    for event in CAMPAIGN_EVENTS:
        try:
            fire_date = date.fromisoformat(event["send_date"])
            if fire_date <= today:
                due.append(event)
        except (ValueError, KeyError):
            print(f"⚠️  Skipping campaign '{event.get('id', '?')}' — invalid send_date format.")
    return due


if __name__ == "__main__":
    print(f"All configured campaigns ({len(CAMPAIGN_EVENTS)} total):\n")
    for e in CAMPAIGN_EVENTS:
        print(f"  [{e['id']}]  {e['name']:40s}  →  fire on {e['send_date']}")

    due = get_due_campaigns()
    print(f"\nCampaigns due today or earlier: {len(due)}")
    for d in due:
        print(f"  → {d['name']} (ID: {d['campaign_id']})")
