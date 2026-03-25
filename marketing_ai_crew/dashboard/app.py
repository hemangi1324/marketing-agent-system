"""
dashboard/app.py — Flask web UI
Run: python dashboard/app.py
Open: http://localhost:5000
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json, threading
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

jobs = {}  # in-memory job store

AGENT_INFO = {
    "content":           {"name": "Content & Branding",   "tier": 1, "color": "#22c55e", "icon": "✍️",  "coverage": "Full"},
    "social":            {"name": "Social Media",          "tier": 1, "color": "#22c55e", "icon": "📱",  "coverage": "Full"},
    "leads":             {"name": "Lead Generation",       "tier": 1, "color": "#22c55e", "icon": "🎯",  "coverage": "Full"},
    "analytics":         {"name": "Analytics & Research",  "tier": 1, "color": "#22c55e", "icon": "📊",  "coverage": "Full"},
    "email":             {"name": "Email Campaigns",       "tier": 1, "color": "#22c55e", "icon": "📧",  "coverage": "Full"},
    "ads":               {"name": "Campaigns & Ads",       "tier": 2, "color": "#f59e0b", "icon": "💰",  "coverage": "Partial"},
    "community":         {"name": "Community & Events",    "tier": 2, "color": "#f59e0b", "icon": "🤝",  "coverage": "Partial"},
    "product_marketing": {"name": "Product Marketing",     "tier": 2, "color": "#f59e0b", "icon": "🚀",  "coverage": "Partial"},
    "pr":                {"name": "PR & Reputation",       "tier": 3, "color": "#ef4444", "icon": "📰",  "coverage": "Human-led"},
    "brand_strategy":    {"name": "Brand Strategy",        "tier": 3, "color": "#ef4444", "icon": "🎨",  "coverage": "Human-led"},
}


def _run_job(job_id, agent_name, brief):
    jobs[job_id]["status"] = "running"
    try:
        from crews.marketing_crew import run_single_agent
        result = run_single_agent(agent_name=agent_name, brief=brief, verbose=False)
        jobs[job_id].update({"status": "done", "result": str(result), "finished": datetime.now().isoformat()})
    except Exception as e:
        jobs[job_id].update({"status": "error", "result": str(e), "finished": datetime.now().isoformat()})


@app.route("/")
def index():
    return render_template("index.html", agents=AGENT_INFO,
                           llm_model=os.getenv("LLM_MODEL", "llama3.1"))


@app.route("/api/run", methods=["POST"])
def run():
    data  = request.json
    name  = data.get("agent")
    brief = data.get("brief", "")
    if name not in AGENT_INFO:
        return jsonify({"error": f"Unknown agent: {name}"}), 400
    jid = f"{name}_{datetime.now().strftime('%H%M%S')}"
    jobs[jid] = {"id": jid, "agent": name, "brief": brief,
                 "status": "queued", "result": None, "started": datetime.now().isoformat()}
    t = threading.Thread(target=_run_job, args=(jid, name, brief), daemon=True)
    t.start()
    return jsonify({"job_id": jid})


@app.route("/api/job/<jid>")
def job_status(jid):
    j = jobs.get(jid)
    return jsonify(j) if j else (jsonify({"error": "not found"}), 404)


@app.route("/api/jobs")
def list_jobs():
    return jsonify(list(reversed(list(jobs.values()))))


@app.route("/api/outputs")
def list_outputs():
    d = os.path.join(os.path.dirname(__file__), "..", "outputs")
    files = []
    if os.path.exists(d):
        for f in sorted(os.listdir(d), reverse=True):
            if f.endswith((".md", ".json")):
                p = os.path.join(d, f)
                files.append({"name": f, "size": os.path.getsize(p),
                               "modified": datetime.fromtimestamp(os.path.getmtime(p)).isoformat()})
    return jsonify(files)


@app.route("/api/output/<filename>")
def get_output(filename):
    p = os.path.join(os.path.dirname(__file__), "..", "outputs", filename)
    if not os.path.exists(p): return jsonify({"error": "not found"}), 404
    with open(p) as f: return jsonify({"filename": filename, "content": f.read()})


if __name__ == "__main__":
    port = int(os.getenv("FLASK_PORT", 5000))
    print(f"\n  Marketing AI Crew Dashboard -> http://localhost:{port}\n")
    app.run(debug=True, port=port, threaded=True, use_reloader=False)
