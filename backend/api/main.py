# """
# backend/api/main.py
# -------------------
# FastAPI application for the Agentic Marketing System.

# Demo Flow:
# 1. User enters a prompt → creates campaign → agents generate content → pending approval.
# 2. User approves → execution (email, Telegram, etc.).
# 3. User clicks "Check Performance" → system simulates receiving analytics data → analytics agent writes memory → campaign healed.
# """

# import asyncio
# import json
# from typing import Optional

# from fastapi import FastAPI, BackgroundTasks, HTTPException, Request
# from fastapi.responses import StreamingResponse

# from backend.config import DATABASE_URL, GEMINI_API_KEY, CTR_THRESHOLD_EMAIL
# from backend.db import database
# from backend.db.models import (
#     PromptRequest, PromptResponse,
#     ApprovalRequest, RejectionRequest,
#     CampaignResponse, GeneratedAssetsResponse, ReasoningLogEntry
# )

# # Import agent functions (these will be provided by the agent team)
# from marketing_ai_crew.crews.marketing_crew import run_campaign_pipeline
# from marketing_ai_crew.agents.email_dispatch_agent import run_execution
# from marketing_ai_crew.agents.analytics_agent import run_analytics   # this should use LLM to generate memory

# app = FastAPI(title="Agentic Marketing System", version="1.0")

# # ---------------------------------------------------------------------
# # Health check
# # ---------------------------------------------------------------------
# @app.get("/health")
# async def health():
#     return {"status": "ok"}

# # ---------------------------------------------------------------------
# # Campaign listing
# # ---------------------------------------------------------------------
# @app.get("/campaigns", response_model=list[CampaignResponse])
# async def list_campaigns():
#     """
#     Return all campaigns for the single company (Nykaa, company_id=1).
#     """
#     campaigns = database.get_campaigns_for_company(1)
#     return campaigns

# # ---------------------------------------------------------------------
# # Manual prompt
# # ---------------------------------------------------------------------
# @app.post("/prompt", response_model=PromptResponse)
# async def manual_prompt(req: PromptRequest, background_tasks: BackgroundTasks):
#     """
#     Create a new campaign from a free‑text prompt and start the agent pipeline.
#     """
#     # 1. Log the prompt
#     prompt_id = database.log_prompt_request(1, req.user_prompt)

#     # 2. Get default brand and audience for the company
#     brand = database.get_brand_profile(1)
#     audiences = database.get_audience_segments(1)
#     if not brand or not audiences:
#         raise HTTPException(500, "Missing brand or audience data. Please seed the database.")

#     # 3. Create a new campaign record
#     campaign_id = database.create_campaign(
#         company_id=1,
#         brand_profile_id=brand["id"],
#         audience_segment_id=audiences[0]["id"],  # use first audience segment
#         name=req.user_prompt[:50],               # truncate for display
#         channel="multi",
#         campaign_type="manual_prompt",
#         triggered_by="manual_prompt",
#         manual_prompt=req.user_prompt,
#         ctr=0.0,
#         open_rate=0.0,
#         industry_avg_ctr=2.09,
#         budget_inr=100000
#     )

#     # 4. Update prompt request with campaign_id
#     database.update_prompt_request(prompt_id, campaign_id, "manual", "processing")

#     # 5. Start the agent pipeline in background (first attempt)
#     background_tasks.add_task(run_campaign_pipeline, campaign_id, 1)

#     return PromptResponse(
#         campaign_id=campaign_id,
#         prompt_id=prompt_id,
#         status="processing",
#         message="Campaign created. Agents are working on it."
#     )

# # ---------------------------------------------------------------------
# # Approval endpoints
# # ---------------------------------------------------------------------
# @app.post("/approve/{approval_id}")
# async def approve_campaign(approval_id: int, req: ApprovalRequest, background_tasks: BackgroundTasks):
#     """
#     Human approves the pending content. Triggers execution.
#     """
#     # 1. Resolve approval
#     database.resolve_approval(approval_id, "approved", req.decided_by, human_edits=req.edited_content)

#     # 2. Get approval details to know campaign and asset
#     approval = database.get_pending_approval(approval_id)
#     if not approval:
#         raise HTTPException(404, "Approval not found")

#     campaign_id = approval["campaign_id"]
#     asset_id = approval["asset_id"]

#     # 3. Run execution in background
#     background_tasks.add_task(run_execution, campaign_id, approval_id, asset_id)

#     return {"status": "approved", "message": "Execution started."}

# @app.post("/reject/{approval_id}")
# async def reject_campaign(approval_id: int, req: RejectionRequest):
#     """
#     Human rejects the pending content.
#     """
#     database.resolve_approval(approval_id, "rejected", req.decided_by, rejection_reason=req.rejection_reason)
#     return {"status": "rejected", "message": "Campaign rejected."}

# # ---------------------------------------------------------------------
# # Performance check (manual trigger for demo)
# # ---------------------------------------------------------------------
# @app.post("/check_healing/{campaign_id}")
# async def check_healing(campaign_id: int, background_tasks: BackgroundTasks):
#     """
#     Simulate receiving new performance data (e.g., from analytics API).
#     This triggers the analytics agent which uses an LLM to generate insights,
#     stores a performance snapshot, writes memory, and marks campaign as healed.
#     """
#     # For demo, we simulate a new CTR (above industry average)
#     new_ctr = 2.5
#     background_tasks.add_task(run_analytics, campaign_id, new_ctr)
#     return {"status": "healing_triggered", "message": "Analytics agent started. This simulates receiving real performance data."}

# # ---------------------------------------------------------------------
# # Streaming reasoning logs (SSE)
# # ---------------------------------------------------------------------
# @app.get("/stream/{campaign_id}")
# async def stream_reasoning(campaign_id: int):
#     """
#     Server‑Sent Events endpoint that pushes new reasoning log entries as they appear.
#     """
#     async def event_generator():
#         last_id = 0
#         while True:
#             logs = database.get_reasoning_since(campaign_id, last_id)
#             for log in logs:
#                 yield f"data: {json.dumps(log)}\n\n"
#                 last_id = log["id"]
#             await asyncio.sleep(1)   # poll every second

#     return StreamingResponse(event_generator(), media_type="text/event-stream")

# # ---------------------------------------------------------------------
# # Get pending approval for a campaign (used by UI to show content)
# # ---------------------------------------------------------------------
# @app.get("/pending/{campaign_id}")
# async def get_pending_approval(campaign_id: int):
#     """
#     Returns the latest pending approval for a campaign, including generated assets and risk scores.
#     """
#     with database.get_conn() as conn:
#         with conn.cursor() as cur:
#             cur.execute("""
#                 SELECT pa.id AS approval_id, pa.status,
#                        ga.*, ra.*
#                 FROM pending_approvals pa
#                 JOIN generated_assets ga ON pa.asset_id = ga.id
#                 JOIN risk_assessments ra ON pa.risk_id = ra.id
#                 WHERE pa.campaign_id = %s AND pa.status = 'pending'
#                 ORDER BY pa.created_at DESC LIMIT 1
#             """, (campaign_id,))
#             row = cur.fetchone()
#             if not row:
#                 return {"pending": False}
#             result = dict(row)
#             # Convert JSON fields that might be stored as strings
#             json_fields = ["instagram_hashtags", "email_subject_variants", "trending_hooks_used", "human_edits", "market_trends_json"]
#             for field in json_fields:
#                 if field in result and result[field]:
#                     if isinstance(result[field], str):
#                         try:
#                             result[field] = json.loads(result[field])
#                         except:
#                             pass
#             return result

# # ---------------------------------------------------------------------
# # Simple log retrieval (alternative to SSE for simpler UI)
# # ---------------------------------------------------------------------
# @app.get("/logs/{campaign_id}")
# async def get_logs(campaign_id: int, limit: int = 20):
#     """
#     Returns the last `limit` reasoning log entries for a campaign.
#     """
#     logs = database.get_reasoning_since(campaign_id, 0)
#     return logs[-limit:] if len(logs) > limit else logs

# # ---------------------------------------------------------------------
# # (Optional) Telegram webhook stub – for future integration
# # ---------------------------------------------------------------------
# @app.post("/telegram_webhook")
# async def telegram_webhook(request: Request):
#     """
#     Placeholder for receiving Telegram bot updates.
#     """
#     data = await request.json()
#     # ... handle incoming messages (e.g., approve via Telegram)
#     return {"ok": True}





"""
backend/api/main.py
-------------------
FastAPI application for the Agentic Marketing System.

Endpoints:
- GET /campaigns                  : List all campaigns
- GET /campaigns/{campaign_id}    : Get single campaign (NEW)
- POST /prompt                     : Create campaign from text prompt
- POST /approve/{approval_id}      : Approve pending content
- POST /reject/{approval_id}       : Reject pending content
- POST /check_healing/{campaign_id}: Simulate performance improvement (with attempt-based CTR)
- GET /stream/{campaign_id}        : SSE streaming of reasoning logs (stops at terminal state)
- GET /pending/{campaign_id}       : Get pending approval (uses helper)
- GET /logs/{campaign_id}          : Simple log retrieval
- GET /health                      : Health check
"""

import asyncio
import json
from typing import Optional

from fastapi import FastAPI, BackgroundTasks, HTTPException, Request
from fastapi.responses import StreamingResponse

from backend.config import DATABASE_URL, GEMINI_API_KEY, CTR_THRESHOLD_EMAIL
from backend.db import database
from backend.db.models import (
    PromptRequest, PromptResponse,
    ApprovalRequest, RejectionRequest,
    CampaignResponse, GeneratedAssetsResponse, ReasoningLogEntry
)

# Import agent functions (adjust paths as needed)
from marketing_ai_crew.crews.marketing_crew import run_campaign_pipeline
from marketing_ai_crew.agents.email_dispatch_agent import run_execution
from marketing_ai_crew.agents.analytics_agent import run_analytics

app = FastAPI(title="Agentic Marketing System", version="1.0")

# ---------------------------------------------------------------------
# Helper: Simulate CTR based on attempt number (replaces hardcoded 2.5)
# ---------------------------------------------------------------------
def simulate_ctr(attempt: int) -> float:
    """
    Return a realistic CTR progression based on the healing attempt number.
    Used in /check_healing to show the learning effect.
    """
    progression = {1: 0.6, 2: 1.4, 3: 2.5}
    return progression.get(attempt, 2.5)

# ---------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------
@app.get("/health")
async def health():
    return {"status": "ok"}

# ---------------------------------------------------------------------
# Campaign listing
# ---------------------------------------------------------------------
@app.get("/campaigns", response_model=list[CampaignResponse])
async def list_campaigns():
    campaigns = database.get_campaigns_for_company(1)
    return campaigns

# ---------------------------------------------------------------------
# Single campaign (NEW)
# ---------------------------------------------------------------------
@app.get("/campaigns/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(campaign_id: int):
    campaign = database.get_campaign(campaign_id)
    if not campaign:
        raise HTTPException(404, "Campaign not found")
    return campaign

# ---------------------------------------------------------------------
# Manual prompt
# ---------------------------------------------------------------------
@app.post("/prompt", response_model=PromptResponse)
async def manual_prompt(req: PromptRequest, background_tasks: BackgroundTasks):
    # 1. Log prompt
    prompt_id = database.log_prompt_request(1, req.user_prompt)

    # 2. Get default brand and audience
    brand = database.get_brand_profile(1)
    audiences = database.get_audience_segments(1)
    if not brand or not audiences:
        raise HTTPException(500, "Missing brand or audience data. Please seed the database.")

    # 3. Create campaign
    campaign_id = database.create_campaign(
        company_id=1,
        brand_profile_id=brand["id"],
        audience_segment_id=audiences[0]["id"],
        name=req.user_prompt[:50],
        channel="multi",
        campaign_type="manual_prompt",
        triggered_by="manual_prompt",
        manual_prompt=req.user_prompt,
        ctr=0.0,
        open_rate=0.0,
        industry_avg_ctr=2.09,
        budget_inr=100000
    )

    # 4. Update prompt request
    database.update_prompt_request(prompt_id, campaign_id, "manual", "processing")

    # 5. Start pipeline in background with safe wrapper
    async def safe_pipeline(cid: int, attempt: int):
        try:
            await run_campaign_pipeline(cid, attempt)
        except Exception as e:
            database.update_campaign_status(cid, "failed")
            database.save_reasoning("System", f"Pipeline failed: {str(e)}", cid)
    background_tasks.add_task(safe_pipeline, campaign_id, 1)

    return PromptResponse(
        campaign_id=campaign_id,
        prompt_id=prompt_id,
        status="processing",
        message="Campaign created. Agents are working on it."
    )

# ---------------------------------------------------------------------
# Approval endpoints
# ---------------------------------------------------------------------
@app.post("/approve/{approval_id}")
async def approve_campaign(approval_id: int, req: ApprovalRequest, background_tasks: BackgroundTasks):
    # Idempotency check
    existing = database.get_pending_approval(approval_id)
    if existing and existing.get("status") != "pending":
        raise HTTPException(409, "Approval already resolved")

    # Resolve approval
    database.resolve_approval(approval_id, "approved", req.decided_by, human_edits=req.edited_content)

    # Get details
    approval = database.get_pending_approval(approval_id)  # Note: now approved, but we need campaign/asset
    if not approval:
        raise HTTPException(404, "Approval not found")
    campaign_id = approval["campaign_id"]
    asset_id = approval["asset_id"]

    # Run execution in background with safe wrapper
    async def safe_execution(cid: int, aid: int, asset: int):
        try:
            await run_execution(cid, aid, asset)
        except Exception as e:
            database.update_campaign_status(cid, "failed")
            database.save_reasoning("System", f"Execution failed: {str(e)}", cid)
    background_tasks.add_task(safe_execution, campaign_id, approval_id, asset_id)

    return {"status": "approved", "message": "Execution started."}

@app.post("/reject/{approval_id}")
async def reject_campaign(approval_id: int, req: RejectionRequest):
    # Idempotency check
    existing = database.get_pending_approval(approval_id)
    if existing and existing.get("status") != "pending":
        raise HTTPException(409, "Approval already resolved")
    database.resolve_approval(approval_id, "rejected", req.decided_by, rejection_reason=req.rejection_reason)
    return {"status": "rejected", "message": "Campaign rejected."}

# ---------------------------------------------------------------------
# Performance check (simulated healing) – with attempt-based CTR
# ---------------------------------------------------------------------
@app.post("/check_healing/{campaign_id}")
async def check_healing(campaign_id: int, background_tasks: BackgroundTasks):
    campaign = database.get_campaign(campaign_id)
    if not campaign:
        raise HTTPException(404, "Campaign not found")
    # Determine next attempt number (current heal_attempts + 1)
    attempt = campaign.get("heal_attempts", 0) + 1
    new_ctr = simulate_ctr(attempt)
    background_tasks.add_task(run_analytics, campaign_id, new_ctr)
    return {"status": "healing_triggered", "message": f"Analytics agent started with simulated CTR={new_ctr}%"}

# ---------------------------------------------------------------------
# Streaming reasoning logs (SSE) with termination condition
# ---------------------------------------------------------------------
@app.get("/stream/{campaign_id}")
async def stream_reasoning(campaign_id: int):
    async def event_generator():
        last_id = 0
        while True:
            # Stop streaming when campaign reaches a terminal state
            if database.is_campaign_terminal(campaign_id):
                yield f"event: done\ndata: \n\n"
                break
            logs = database.get_reasoning_since(campaign_id, last_id)
            for log in logs:
                yield f"data: {json.dumps(log)}\n\n"
                last_id = log["id"]
            await asyncio.sleep(2)  # poll every 2 seconds (reduced load)
    return StreamingResponse(event_generator(), media_type="text/event-stream")

# ---------------------------------------------------------------------
# Get pending approval for a campaign (uses new helper)
# ---------------------------------------------------------------------
@app.get("/pending/{campaign_id}")
async def get_pending_approval(campaign_id: int):
    result = database.get_pending_approval_full(campaign_id)
    if not result:
        return {"pending": False}
    return result

# ---------------------------------------------------------------------
# Simple log retrieval (optional)
# ---------------------------------------------------------------------
@app.get("/logs/{campaign_id}")
async def get_logs(campaign_id: int, limit: int = 20):
    logs = database.get_reasoning_since(campaign_id, 0)
    return logs[-limit:] if len(logs) > limit else logs

# ---------------------------------------------------------------------
# (Optional) Telegram webhook stub
# ---------------------------------------------------------------------
@app.post("/telegram_webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    # Handle incoming messages (optional)
    return {"ok": True}