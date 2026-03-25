"""
tools/mock_social_tool.py
Simulates Buffer social scheduling with local JSON.
"""
import json, os
from datetime import datetime
from crewai.tools import BaseTool

SOCIAL_FILE = os.path.join(os.path.dirname(__file__), "..", "outputs", "social_queue.json")

def _load():
    if os.path.exists(SOCIAL_FILE):
        with open(SOCIAL_FILE) as f: return json.load(f)
    return {"scheduled": [], "replies": []}

def _save(data):
    os.makedirs(os.path.dirname(SOCIAL_FILE), exist_ok=True)
    with open(SOCIAL_FILE, "w") as f: json.dump(data, f, indent=2)


class SocialScheduleTool(BaseTool):
    name: str = "Social Media Scheduler"
    description: str = (
        "Schedule a post to social media. "
        "Input: JSON with platform (instagram/linkedin/twitter), content, scheduled_at."
    )
    def _run(self, post_json: str) -> str:
        try:    data = json.loads(post_json)
        except: data = {"content": post_json, "platform": "instagram"}
        q = _load()
        post = {"id": f"p{len(q['scheduled'])+1}", "queued": datetime.now().isoformat(), **data}
        q["scheduled"].append(post)
        _save(q)
        return f"[MOCK BUFFER] Scheduled on {data.get('platform','social')}: \"{str(data.get('content',''))[:80]}...\""


class SocialGetQueueTool(BaseTool):
    name: str = "Social Queue Viewer"
    description: str = "View all scheduled social media posts."
    def _run(self, query: str = "") -> str:
        q = _load()
        if not q["scheduled"]: return "Queue is empty."
        lines = [f"Scheduled posts ({len(q['scheduled'])}):]"]
        for p in q["scheduled"]:
            lines.append(f"  [{p.get('platform','?').upper()}] {str(p.get('content',''))[:80]}...")
        return "\n".join(lines)
