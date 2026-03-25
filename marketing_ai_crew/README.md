# 🤖 Marketing AI Crew
### Gemini Powered · High Quality Output

A full multi-agent marketing automation system built with CrewAI.
10 agents mapped to every marketing function — content, social, leads,
analytics, email, ads, community, product marketing, PR, and brand strategy.

---

## 💰 Cost Breakdown

| Component         | What's Used              | Cost  |
|-------------------|--------------------------|-------|
| LLM               | Google Gemini 2.5 Flash  | Paid API / Free Tier available |
| Web search        | DuckDuckGo               | FREE  |
| CRM               | Local JSON mock          | FREE  |
| Social scheduling | Local JSON mock          | FREE  |
| Email campaigns   | Local JSON mock          | FREE  |
| Ad management     | Local JSON mock          | FREE  |
| Framework         | CrewAI (open source)     | FREE  |
| Dashboard         | Flask                    | FREE  |
| Hosting           | Your own machine         | FREE  |

---

## 📁 Project Structure

```
marketing_ai_crew/
│
├── main.py                    ← CLI entry point
├── check_setup.py             ← Verify setup before running
├── requirements.txt
├── .env                       ← LLM config (Gemini)
├── Makefile                   ← Shortcuts: make run, make dashboard, etc.
│
├── config/
│   ├── settings.py            ← LLM switcher
│   └── brand_guidelines.md    ← Edit this with YOUR brand voice
│
├── agents/
│   └── all_agents.py          ← All 10 agents defined here
│
├── tasks/
│   └── task_factory.py        ← Task prompts for each agent
│
├── tools/
│   ├── search_tool.py         ← DuckDuckGo (FREE, no key)
│   ├── file_tool.py           ← Brand guidelines reader + output saver
│   ├── mock_crm_tool.py       ← Simulated HubSpot → outputs/crm_contacts.json
│   ├── mock_social_tool.py    ← Simulated Buffer  → outputs/social_queue.json
│   ├── mock_email_tool.py     ← Simulated Mailchimp → outputs/email_campaigns.json
│   ├── mock_ads_tool.py       ← Simulated Google Ads → outputs/ad_campaigns.json
│   └── mock_analytics_tool.py ← Simulated GA4 with realistic mock data
│
├── crews/
│   └── marketing_crew.py      ← Orchestrator: run one agent, tier, or all
│
├── human_loop/
│   └── approval.py            ← Human-in-the-loop approval for Tier 2/3 tasks
│
├── scripts/
│   ├── run_content.sh         ← Quick shell shortcuts
│   ├── run_analytics.sh
│   └── run_all_tier1.sh
│
├── tests/
│   ├── test_tools.py          ← Unit tests for all tools
│   ├── test_agents.py         ← Agent instantiation tests
│   └── test_tasks.py          ← Task creation tests
│
├── outputs/                   ← All agent outputs saved here (auto-created)
│
└── dashboard/
    ├── app.py                 ← Flask web UI
    └── templates/
        └── index.html         ← Dashboard (dark theme, live polling)
```

---

## 🚀 Quick Start (3 steps)

### 1. Set your Gemini API Key
Rename `.env.example` to `.env` (or edit the existing `.env`) and drop your `GEMINI_API_KEY`:

```bash
GEMINI_API_KEY=AIzaSy...your-key-here...
```

### 2. Install Python dependencies
```bash
cd marketing_ai_crew
pip install -r requirements.txt
```

### 3. Verify & Run
```bash
# Check everything is working
python check_setup.py

# Run one agent (CLI)
python main.py --agent analytics

# OR launch the web dashboard
python dashboard/app.py
# Open http://localhost:5000
```

---

## 🎮 CLI Usage

```bash
# List all agents
python main.py --list

# Run specific agent (default brief)
python main.py --agent content
python main.py --agent leads
python main.py --agent analytics
python main.py --agent email
python main.py --agent ads
python main.py --agent pr

# Run with custom brief
python main.py --agent content --task "Write 3 captions for our Black Friday sale"
python main.py --agent leads  --task "Find fintech startups in Bangalore"

# Run an entire tier
python main.py --agent tier1   # All fully-automatable agents
python main.py --agent tier2   # All partial agents (will ask for approval)
python main.py --agent tier3   # All human-led agents

# Run everything (slow)
python main.py --agent all

# Quiet mode (no verbose agent logs)
python main.py --agent analytics --quiet
```

---

## 🔁 Switching Models

Edit `.env` — no code changes needed. Our defaults target Gemini:

```bash
LLM_PROVIDER=gemini

# Faster / Cost-effective
LLM_MODEL=gemini-2.5-flash

# Advanced Reasoning
LLM_MODEL=gemini-1.5-pro
```

---

## 🔧 Replacing Mock Tools with Real APIs

Each mock tool has the real API call commented right inside it:

```python
# tools/mock_crm_tool.py
def _run(self, contact_json):
    # ── REAL HubSpot (uncomment + add HUBSPOT_API_KEY to .env): ──
    # import hubspot
    # client = hubspot.Client.create(api_key=os.getenv("HUBSPOT_API_KEY"))
    # return client.crm.contacts.basic_api.create(...)
    # ──────────────────────────────────────────────────────────────

    # Mock version (current):
    ...
```

---

## 🧪 Running Tests

```bash
python -m pytest tests/ -v
```

---

## 📊 Agent Reference

| Key               | Agent                | Tier | Coverage  | Build Type     |
|-------------------|----------------------|------|-----------|----------------|
| content           | Content & Branding   | 1    | Full      | Skill          |
| social            | Social Media         | 1    | Full      | Separate Agent |
| leads             | Lead Generation      | 1    | Full      | Separate Agent |
| analytics         | Analytics & Research | 1    | Full      | Skill          |
| email             | Email Campaigns      | 1    | Full      | Skill          |
| ads               | Campaigns & Ads      | 2    | Partial   | Separate Agent |
| community         | Community & Events   | 2    | Partial   | Skill          |
| product_marketing | Product Marketing    | 2    | Partial   | Skill          |
| pr                | PR & Reputation      | 3    | Human-led | Skill only     |
| brand_strategy    | Brand Strategy       | 3    | Human-led | Research only  |
