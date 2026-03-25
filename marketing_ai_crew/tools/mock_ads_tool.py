"""
tools/mock_ads_tool.py
Simulates Google Ads with local JSON + preset mock data.
"""
import json, os, random
from datetime import datetime
from crewai.tools import BaseTool

ADS_FILE = os.path.join(os.path.dirname(__file__), "..", "outputs", "ad_campaigns.json")

SEED_CAMPAIGNS = [
    {"id": "c001", "name": "Brand Awareness Q1",    "status": "active", "budget": 50,  "spend": 38.2,  "clicks": 142, "conversions": 4,  "ctr": "3.2%"},
    {"id": "c002", "name": "Lead Gen - Free Trial",  "status": "active", "budget": 100, "spend": 99.8,  "clicks": 87,  "conversions": 12, "ctr": "2.1%"},
    {"id": "c003", "name": "Retargeting - Checkout", "status": "active", "budget": 30,  "spend": 8.4,   "clicks": 23,  "conversions": 1,  "ctr": "0.8%"},
]

def _load():
    if os.path.exists(ADS_FILE):
        with open(ADS_FILE) as f: return json.load(f)
    data = {"campaigns": SEED_CAMPAIGNS, "variations": []}
    os.makedirs(os.path.dirname(ADS_FILE), exist_ok=True)
    with open(ADS_FILE, "w") as f: json.dump(data, f, indent=2)
    return data

def _save(data):
    os.makedirs(os.path.dirname(ADS_FILE), exist_ok=True)
    with open(ADS_FILE, "w") as f: json.dump(data, f, indent=2)


class AdsGetPerformanceTool(BaseTool):
    name: str = "Ads Performance Reporter"
    description: str = "Get current performance for all ad campaigns (spend, clicks, conversions, CTR)."
    def _run(self, query: str = "") -> str:
        ads = _load()
        lines = ["Ad Campaign Performance:\n"]
        for c in ads["campaigns"]:
            roas = round(c["conversions"] * 29 / max(c["spend"], 0.01), 2)
            lines.append(
                f"  [{c['status'].upper()}] {c['name']}\n"
                f"  Budget: ${c['budget']}/day | Spent: ${c['spend']} | "
                f"Clicks: {c['clicks']} | Conversions: {c['conversions']} | "
                f"CTR: {c['ctr']} | ROAS: {roas}x\n"
            )
        return "\n".join(lines)


class AdsPauseCampaignTool(BaseTool):
    name: str = "Ads Pause Campaign"
    description: str = "Pause a campaign by ID. Always flag for human approval first. Input: campaign_id."
    def _run(self, campaign_id: str) -> str:
        ads = _load()
        for c in ads["campaigns"]:
            if c["id"] == campaign_id.strip():
                c["status"] = "paused"
                _save(ads)
                return f"[MOCK] Campaign '{c['name']}' paused. FLAGGED FOR HUMAN REVIEW."
        return f"Campaign '{campaign_id}' not found."


class AdsCreateVariationTool(BaseTool):
    name: str = "Ads Copy Variation Creator"
    description: str = "Log new ad copy variations for a campaign. Input: JSON with campaign_id, headlines, descriptions."
    def _run(self, variation_json: str) -> str:
        try:    data = json.loads(variation_json)
        except: data = {"raw": variation_json}
        ads = _load()
        ads.setdefault("variations", []).append({"created": datetime.now().isoformat(), **data})
        _save(ads)
        return f"[MOCK] {len(data.get('headlines', []))} ad variations saved for {data.get('campaign_id','?')}"
