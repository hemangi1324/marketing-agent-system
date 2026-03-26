# Marketing AI Crew — System Architecture Explanation

## 1. Final Architecture Overview

The refactored system is a **production-ready, modular, multi-agent marketing pipeline** built on CrewAI. It follows a clean layered architecture:

```
┌─────────────────────────────────────────────────────────────────┐
│                    CLI Entry Point (main.py)                     │
├─────────────────────────────────────────────────────────────────┤
│              UniversalOrchestrator (orchestrator/)              │
│         Sequential Mode ──────── Dynamic Mode                   │
├──────────────┬──────────────┬──────────────┬───────────────────┤
│  Strategy    │   Content    │    Risk      │    Analytics       │
│   Agent      │    Agent     │   Agent      │     Agent          │
├──────────────┴──────────────┴──────────────┴───────────────────┤
│                Communication Layer (Email + Slack + Telegram)   │
├─────────────────────────────────────────────────────────────────┤
│            Schemas Layer (Pydantic — type-safe exchange)        │
├─────────────────────────────────────────────────────────────────┤
│         Database Layer (db_manager + campaign_store)            │
│                    outputs/db/ (JSON files)                      │
├─────────────────────────────────────────────────────────────────┤
│                    Tools (SMTP, Slack, Telegram, mock_*)        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Agent Responsibilities

### Strategy Agent (`agents/strategy_agent.py`)
- **Role:** Campaign Strategy Director
- **Input:** Campaign brief, festival_tag, historical context from DB
- **Output:** `StrategyOutput` — campaign_theme, tone, key_messages, platform_priorities
- **Key feature:** Reads past campaign post-mortems from DB to avoid repeating mistakes

### Content Agent (`agents/content_agent.py`)
- **Role:** Content and Copy Specialist
- **Input:** Brief + `StrategyOutput` injected into task description
- **Output:** `ContentOutput` — EmailContent (subject, body, preview) + SocialContent (Instagram, Twitter, LinkedIn)
- **Key feature:** Strategy-directed copy — follows the theme, tone and key messages exactly

### Risk Agent (`agents/risk_agent.py`)
- **Role:** Brand Safety & Risk Analyst
- **Input:** Content dict from Content Agent
- **Output:** `RiskOutput` — brand_safety, legal_risk, cultural_sensitivity scores + `green_light` flag
- **Key feature:** If `green_light=False` → Slack alert sent + email blocked
- **New:** `run_risk_check_structured()` — Pydantic-typed variant persisting to DB

### Analytics Agent (`agents/analytics_agent.py`)
- **Role:** Campaign Performance Analyst
- **Input:** Old/new CTR metrics + optional festival context
- **Output:** `AnalyticsOutput` — healed status, post-mortem, recommendations
- **Key feature:** Saves post-mortem to campaign memory for future festival campaigns
- **New:** `run_analytics_structured()` — Pydantic-typed variant with auto DB save

---

## 3. Data Flow Between Agents

```
Campaign Brief (user)
        │
        ▼
[Strategy Agent] → StrategyOutput.to_context_string()
        │                    │
        │            injected into task description
        ▼
[Content Agent] → ContentOutput
        │              │
        │         .to_risk_dict()         (backward compat)
        ▼              │
[Risk Agent] ──────────┘
        │
        ├── green_light = True  → Email Dispatch (SMTP)
        │                       → Telegram ad (optional)
        │
        └── green_light = False → Slack alert
                                → Emails BLOCKED
        │
        ▼
[Analytics Agent] → AnalyticsOutput + PostMortem saved to DB
```

---

## 4. Shared State Design

**File:** `orchestrator/state.py`

`SharedState` wraps the `CampaignState` Pydantic model and is the single container for all pipeline data:

```python
class CampaignState(BaseModel):
    campaign_id: int
    brief: str
    festival_tag: Optional[str]
    strategy_output: Optional[Dict]    # populated by Strategy Agent
    content_output: Optional[Dict]     # populated by Content Agent
    risk_output: Optional[Dict]        # populated by Risk Agent
    communication_output: Optional[Dict]  # populated after email/slack/telegram
    analytics_output: Optional[Dict]   # populated by Analytics Agent
    green_light: Optional[bool]        # set by Risk Agent
    pipeline_blocked: bool             # True if email was blocked
    step_logs: List[AgentStepLog]      # full audit trail
```

**How context flows:**
- After each agent runs, `state.update_*()` is called
- `state.to_context_string()` serialises the current state into a human-readable string
- This string is **prepended** to the next agent's task description
- Agents read the context from their task — no Python object passing between agents

**Persistence:** `SharedState._persist()` calls `campaign_store.save_campaign()` after every update — crash-safe.

---

## 5. Pydantic Schema Usage

**Directory:** `schemas/`

| Schema File | Models | Used By |
|---|---|---|
| `campaign.py` | `CampaignInput`, `CampaignState`, `CampaignOutput` | Orchestrator |
| `content.py` | `EmailContent`, `SocialContent`, `ContentOutput` | Content Agent |
| `risk.py` | `RiskInput`, `RiskOutput` | Risk Agent |
| `analytics.py` | `AnalyticsInput`, `AnalyticsOutput`, `PostMortem` | Analytics Agent |
| `strategy.py` | `StrategyInput`, `StrategyOutput` | Strategy Agent |
| `communication.py` | `EmailPayload`, `SlackPayload`, `TelegramPayload`, `CommResult` | Orchestrator comms layer |

**Backward compatibility:** All schemas include `from_dict()` and `to_dict()` / `to_risk_dict()` methods that convert to/from the flat dicts used by the existing pipeline. **No existing code was broken.**

---

## 6. Orchestrator Operation

**File:** `orchestrator/orchestrator.py`

**Entry point:**
```python
orch = UniversalOrchestrator()
result = orch.run_pipeline(brief="...", campaign_id=100, mode="sequential")
```

**Sequential pipeline (5 steps):**
1. Strategy Agent → `state.update_strategy()`
2. Content Agent → `state.update_content()`
3. Risk Agent → `state.update_risk()` → sets `green_light`
4. Communication: Email (if green) + Slack (if not green) + Telegram (if green + configured)
5. Analytics Agent → `state.update_analytics()`

**Dynamic mode:** Runs sequential first. If `green_light=False` and `can_delegate()`, re-runs content generation with an adjusted brief that incorporates the failure reason.

**Loop prevention:** `SharedState.delegation_count` — hard cap of 3, enforced by `can_delegate()`.

**Idempotency:** Checks `campaign_store.campaign_exists(campaign_id)` before running. Skip if already exists (override with `force_rerun=True`).

**Retry logic:** Each agent step is wrapped in `_with_retry()` — handles 503/429 transient API errors with up to 3 retries and 12-second delays.

---

## 7. Database Interaction Loop

**Architecture:** JSON-file-backed store in `outputs/db/` (production: swap `db_manager` for SQLAlchemy/psycopg2).

```
Campaign Start
    │
    ▼
campaign_store.campaign_exists(id)  ──  If exists → idempotency guard
    │
Each agent step:
    │
    ├── READ: campaign_store.build_historical_context()  ← informs Strategy Agent
    ├── WRITE: campaign_store.save_campaign(state_dict) ← after every agent step
    ├── WRITE: campaign_store.log_agent_step(...)        ← audit trail (append-only)
    ├── WRITE: campaign_store.save_risk_result(...)      ← after Risk Agent
    └── WRITE: campaign_store.save_analytics_result(...) ← after Analytics Agent

Campaign Memory:
    └── memory/campaign_memory.py → saves post-mortems keyed by festival_tag
        └── Future campaigns with same festival_tag read this first
```

**Collections (outputs/db/):**
| File | Purpose |
|---|---|
| `campaigns.json` | Full CampaignState snapshots |
| `risk_scores.json` | Risk results per campaign |
| `analytics.json` | Analytics outputs per campaign |
| `email_send_idempotency.json` | Prevents duplicate email sends |
| `slack_log.json` | Prevents duplicate Slack alerts |
| `telegram_log.json` | Prevents duplicate Telegram messages |
| `agent_steps.jsonl` | Append-only audit trail |

---

## 8. Communication Layer Design

Triggered in `orchestrator.py → _run_communication()`:

| Channel | Trigger Condition | Idempotency |
|---|---|---|
| **Email (SMTP)** | `green_light = True` | MD5 hash of `campaign_id + subject` stored in `email_send_idempotency.json` |
| **Slack Alert** | `green_light = False` | `slack_log.json` keyed by `campaign_id` |
| **Telegram Ad** | `green_light = True` AND `TELEGRAM_BOT_TOKEN` set | `telegram_log.json` keyed by `campaign_id` |

**Structured payloads:** `SlackPayload`, `TelegramPayload` schemas ensure type-safe payloads. All channels are backward-compatible with the existing `send_slack_alert()` and `send_telegram_message()` functions.

---

## 9. Execution Pipeline

### Default: Sequential via CLI
```bash
python main.py --orchestrator --task "Diwali sale — 30% off" --campaign-id 100 --festival diwali
```

### Dynamic Mode
```bash
python main.py --orchestrator --mode dynamic --task "Holi campaign" --campaign-id 101
```

### Legacy email pipeline (unchanged)
```bash
python main.py --agent email-pipeline --task "Promotional email" --campaign-id 50
```

### Single agent (unchanged)
```bash
python main.py --agent content --task "Write captions for product launch"
```

**Execution flow flag summary:**

| Flag | Effect |
|---|---|
| `--orchestrator` | Use UniversalOrchestrator (5-step pipeline) |
| `--mode sequential` | Fixed pipeline (default) |
| `--mode dynamic` | Risk failure triggers content re-generation |
| `--festival diwali` | Injects festival_tag for historical context lookup |
| `--force-rerun` | Bypass idempotency check, re-run existing campaign_id |

---

## 10. Performance Optimizations

| Optimization | Implementation |
|---|---|
| **LLM singleton** | `config/settings.py` uses `@lru_cache(maxsize=1)` — LLM created once per process |
| **Lazy agent construction** | Agent objects created only when `get_*_agent()` is called, not at import time |
| **Retry for transient errors** | `_with_retry()` handles 503/429 without crashing |
| **Idempotent sends** | Email, Slack, Telegram each maintain a log — no duplicate sends |
| **Context as string** | SharedState serialises to string for LLMs — avoids Python object serialization overhead |
| **Append-only audit log** | `agent_steps.jsonl` — O(1) writes, no full-file rewrites |
| **Thread-safe DB** | Per-collection `threading.Lock` — safe for concurrent use |
| **Non-fatal failures** | Strategy and Analytics agent failures degrade gracefully; Content and Risk failures block pipeline |
| **Reusable historical context** | `build_historical_context()` reads DB once and formats — reduces LLM context token usage |

---

## 11. Key Design Decisions

### Why JSON-file DB (not SQLite/PostgreSQL)?
- **Zero external dependencies** — runs on any machine without setup
- **Production swap-ready** — `db_manager.py` has a clean interface; swap `_load()/_save()` for any ORM
- **Human-readable** — outputs can be inspected directly

### Why string context injection (not Python object passing)?
- CrewAI agents work via task descriptions — the LLM reads text, not Python objects
- Injecting `state.to_context_string()` into task descriptions is the idiomatic CrewAI pattern
- Avoids serialization complexity and maintains agent independence

### Why keep existing flat-dict pipeline intact?
- `email-pipeline` command still works exactly as before
- All tools and services remain unchanged
- Zero risk of breaking existing demo/scheduler functionality
- Pydantic schemas wrap the flat dicts via `from_dict()` / `to_risk_dict()` bridges

### Why `allow_delegation=False` on all agents?
- CrewAI delegation is unpredictable — agents may call the wrong agent or loop
- Dynamic delegation is managed explicitly by the Orchestrator's `_run_dynamic()` with hard limits
- This ensures **predictability and traceability** in every run
