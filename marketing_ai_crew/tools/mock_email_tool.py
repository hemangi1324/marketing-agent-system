"""
tools/mock_email_tool.py
Simulates Mailchimp with local JSON storage.
"""
import json, os
from datetime import datetime
from crewai.tools import BaseTool

EMAIL_FILE = os.path.join(os.path.dirname(__file__), "..", "outputs", "email_campaigns.json")

def _load():
    if os.path.exists(EMAIL_FILE):
        with open(EMAIL_FILE) as f: return json.load(f)
    return {"campaigns": [], "sequences": []}

def _save(data):
    os.makedirs(os.path.dirname(EMAIL_FILE), exist_ok=True)
    with open(EMAIL_FILE, "w") as f: json.dump(data, f, indent=2)


class EmailCreateCampaignTool(BaseTool):
    name: str = "Email Campaign Creator"
    description: str = "Create an email campaign. Input: JSON with subject_line, preview_text, body, segment."
    def _run(self, campaign_json: str) -> str:
        try:    data = json.loads(campaign_json)
        except: data = {"subject_line": campaign_json}
        emails = _load()
        campaign = {"id": f"camp{len(emails['campaigns'])+1}", "created": datetime.now().isoformat(), "status": "draft", **data}
        emails["campaigns"].append(campaign)
        _save(emails)
        return f"[MOCK MAILCHIMP] Campaign draft created: '{data.get('subject_line','Untitled')}'"


class EmailCreateSequenceTool(BaseTool):
    name: str = "Email Sequence Creator"
    description: str = "Create a drip email sequence. Input: JSON with sequence_name, trigger, emails list."
    def _run(self, sequence_json: str) -> str:
        try:    data = json.loads(sequence_json)
        except: data = {"sequence_name": sequence_json}
        emails = _load()
        seq = {"id": f"seq{len(emails['sequences'])+1}", "created": datetime.now().isoformat(), **data}
        emails["sequences"].append(seq)
        _save(emails)
        n = len(data.get("emails", []))
        return f"[MOCK MAILCHIMP] Sequence '{data.get('sequence_name','?')}' created with {n} emails"
