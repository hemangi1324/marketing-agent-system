"""
tools/mock_crm_tool.py
Simulates HubSpot CRM with local JSON storage.
To use real HubSpot: replace _run() body with HubSpot API calls.
"""
import json, os
from datetime import datetime
from crewai.tools import BaseTool

CRM_FILE = os.path.join(os.path.dirname(__file__), "..", "outputs", "crm_contacts.json")

def _load():
    if os.path.exists(CRM_FILE):
        with open(CRM_FILE) as f: return json.load(f)
    return {"contacts": [], "email_log": []}

def _save(data):
    os.makedirs(os.path.dirname(CRM_FILE), exist_ok=True)
    with open(CRM_FILE, "w") as f: json.dump(data, f, indent=2)


class CRMCreateContactTool(BaseTool):
    name: str = "CRM Create Contact"
    description: str = (
        "Add a prospect to the CRM. "
        "Input: JSON string with name, email, company, role, notes."
    )
    def _run(self, contact_json: str) -> str:
        try:    data = json.loads(contact_json)
        except: data = {"raw": contact_json}
        crm = _load()
        contact = {"id": f"c{len(crm['contacts'])+1}", "created": datetime.now().isoformat(), **data}
        crm["contacts"].append(contact)
        _save(crm)
        return f"[MOCK CRM] Contact added: {data.get('name','?')} @ {data.get('company','?')}"


class CRMListContactsTool(BaseTool):
    name: str = "CRM List Contacts"
    description: str = "List all contacts currently in the CRM."
    def _run(self, query: str = "") -> str:
        crm = _load()
        if not crm["contacts"]: return "CRM is empty."
        lines = [f"CRM: {len(crm['contacts'])} contacts"]
        for c in crm["contacts"]:
            lines.append(f"  - {c.get('name')} | {c.get('company')} | {c.get('email','no email')}")
        return "\n".join(lines)


class CRMLogEmailTool(BaseTool):
    name: str = "CRM Log Email"
    description: str = "Log an email sent to a contact. Input: JSON with contact_id, subject, body."
    def _run(self, email_json: str) -> str:
        try:    data = json.loads(email_json)
        except: data = {"raw": email_json}
        crm = _load()
        crm["email_log"].append({"logged": datetime.now().isoformat(), **data})
        _save(crm)
        return f"[MOCK CRM] Email logged: '{data.get('subject','(no subject)')}'"
