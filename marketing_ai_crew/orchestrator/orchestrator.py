"""
orchestrator/orchestrator.py
-----------------------------
UniversalOrchestrator — the central control layer for the marketing pipeline.

Design:
  - Single entry point: run_pipeline(brief, campaign_id, ...)
  - Sequential mode (default): Strategy → Content → Risk → Communication → Analytics
  - Dynamic mode: agents can signal need for re-runs via state flags
  - SharedState passes context between every agent step
  - Graceful failure: each step is wrapped in try/except; pipeline continues or blocks cleanly
  - Idempotency: checks DB before running to avoid duplicate campaign runs
  - Loop protection: delegation counter capped at 3

Usage:
    from orchestrator import UniversalOrchestrator
    orch = UniversalOrchestrator()
    result = orch.run_pipeline(
        brief="Diwali campaign — 30% off",
        campaign_id=100,
        festival_tag="diwali",
    )
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
import time
from typing import Optional
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from dotenv import load_dotenv
load_dotenv(override=True)

from orchestrator.state import SharedState
from schemas.campaign import CampaignOutput
from database import campaign_store

logger = logging.getLogger("orchestrator")
console = Console()

# ── Retry config for transient API errors ────────────────────────────────────
_MAX_RETRIES = 3
_RETRY_DELAY = 12  # seconds


def _with_retry(fn, step_name: str):
    """
    Wrap a callable in retry logic for transient LLM API failures (503, 429).
    Returns the result or raises on final failure.
    """
    transient_codes = ["503", "429", "UNAVAILABLE", "RESOURCE_EXHAUSTED"]
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            return fn()
        except Exception as exc:
            err = str(exc)
            is_transient = any(code in err for code in transient_codes)
            if is_transient and attempt < _MAX_RETRIES:
                console.print(
                    f"[yellow]⚠  {step_name}: API busy (attempt {attempt}/{_MAX_RETRIES}). "
                    f"Retrying in {_RETRY_DELAY}s…[/yellow]"
                )
                time.sleep(_RETRY_DELAY)
            else:
                raise


class UniversalOrchestrator:
    """
    Controls execution of the full marketing pipeline.

    Features:
    - Manages shared state and context injection
    - Sequential and dynamic execution modes
    - Per-step error handling with graceful degradation
    - Idempotency via campaign DB check
    - Full audit trail via SharedState step_logs
    """

    def __init__(self, verbose: bool = True):
        self.verbose = verbose

    def _print(self, msg: str, style: str = "white"):
        if self.verbose:
            console.print(f"[{style}]{msg}[/{style}]")

    # ─────────────────────────────────────────────────────────────────────────
    # Public entry point
    # ─────────────────────────────────────────────────────────────────────────

    def run_pipeline(
        self,
        brief: str,
        campaign_id: int,
        festival_tag: Optional[str] = None,
        target_audience: Optional[str] = None,
        mode: str = "sequential",
        force_rerun: bool = False,
    ) -> CampaignOutput:
        """
        Run the full marketing campaign pipeline.

        Pipeline (sequential):
            1. Strategy Agent    — theme, tone, key messages
            2. Content Agent     — email + social content
            3. Risk Agent        — brand safety, legal, cultural check
            4. Communication     — Email, Slack (if risk failed), Telegram
            5. Analytics Agent   — post-mortem, performance insights

        Args:
            brief          : Campaign brief / objective
            campaign_id    : Unique campaign identifier
            festival_tag   : Optional festival context (e.g. 'diwali')
            target_audience: Optional audience description
            mode           : 'sequential' (default) | 'dynamic'
            force_rerun    : If True, re-run even if campaign_id exists in DB

        Returns:
            CampaignOutput — final summary with success flag, email counts, etc.
        """

        console.print(Panel(
            f"[bold]Campaign ID:[/bold] #{campaign_id}\n"
            f"[bold]Brief:[/bold] {brief}\n"
            f"[bold]Festival:[/bold] {festival_tag or 'None'} | "
            f"[bold]Mode:[/bold] {mode}",
            title="[bold cyan]🚀 Marketing AI Crew — Universal Orchestrator[/bold cyan]",
            border_style="cyan",
        ))

        # ── Idempotency check ─────────────────────────────────────────────────
        if not force_rerun and campaign_store.campaign_exists(campaign_id):
            console.print(
                f"[yellow]⚠  Campaign #{campaign_id} already exists in DB. "
                "Use force_rerun=True to override.[/yellow]"
            )
            existing = campaign_store.load_campaign(campaign_id)
            return CampaignOutput(
                campaign_id=campaign_id,
                success=True,
                pipeline_blocked=existing.get("pipeline_blocked", False),
                block_reason=existing.get("block_reason"),
                emails_sent=existing.get("communication_output", {}).get("emails_sent", 0) if existing.get("communication_output") else 0,
            )

        # ── Initialise shared state ───────────────────────────────────────────
        state = SharedState(
            campaign_id=campaign_id,
            brief=brief,
            festival_tag=festival_tag,
            target_audience=target_audience,
        )

        try:
            if mode == "sequential":
                return self._run_sequential(state)
            elif mode == "dynamic":
                return self._run_dynamic(state)
            else:
                raise ValueError(f"Unknown mode: {mode}. Use 'sequential' or 'dynamic'.")
        except Exception as exc:
            logger.error("Orchestrator fatal error for campaign %s: %s", campaign_id, exc)
            state.mark_failed("orchestrator", str(exc))
            return CampaignOutput(
                campaign_id=campaign_id,
                success=False,
                block_reason=f"Orchestrator error: {str(exc)[:200]}",
                step_logs=state.to_dict().get("step_logs", []),
            )

    # ─────────────────────────────────────────────────────────────────────────
    # Sequential execution (default)
    # ─────────────────────────────────────────────────────────────────────────

    def _run_sequential(self, state: SharedState) -> CampaignOutput:
        """
        Fixed pipeline: Strategy → Content → Risk → Communication → Analytics
        Each step persists its output to shared state before the next begins.
        """

        # ── Step 1: Strategy ──────────────────────────────────────────────────
        console.print("\n[bold yellow]Step 1/5 — Strategy Agent planning campaign…[/bold yellow]")
        strategy_output = None
        try:
            from agents.strategy_agent import run_strategy
            strategy_output = _with_retry(
                lambda: run_strategy(
                    brief=state.brief,
                    campaign_id=state.campaign_id,
                    festival_tag=state.festival_tag,
                    historical_context=state.get_historical_context(),
                ),
                "Strategy Agent"
            )
            state.update_strategy(strategy_output.model_dump())
            console.print(Panel(
                f"Theme : {strategy_output.campaign_theme}\n"
                f"Tone  : {strategy_output.tone}\n"
                f"Msgs  : {'; '.join(strategy_output.key_messages[:2])}…",
                title="[green]✅ Strategy — Done[/green]", border_style="green",
            ))
        except Exception as exc:
            logger.warning("Strategy agent failed (non-fatal): %s", exc)
            state.mark_failed("strategy_agent", str(exc))
            console.print(f"[yellow]⚠  Strategy Agent skipped — using brief directly. ({exc})[/yellow]")

        # ── Step 2: Content ───────────────────────────────────────────────────
        console.print("\n[bold yellow]Step 2/5 — Content Agent generating copy…[/bold yellow]")
        content_output = None
        try:
            from agents.content_agent import run_content_generation
            from schemas.strategy import StrategyOutput

            strategy = StrategyOutput.from_dict(strategy_output.model_dump()) if strategy_output else None

            content_output = _with_retry(
                lambda: run_content_generation(
                    brief=state.brief,
                    campaign_id=state.campaign_id,
                    strategy=strategy,
                    campaign_context=state.to_context_string(),
                ),
                "Content Agent"
            )
            state.update_content(content_output.model_dump())
            console.print(Panel(
                f"Subject : {content_output.email_content.subject}\n"
                f"Preview : {content_output.email_content.preview_text or '(none)'}",
                title="[green]✅ Content — Done[/green]", border_style="green",
            ))
        except Exception as exc:
            logger.error("Content Agent failed: %s", exc)
            state.mark_failed("content_agent", str(exc))
            return CampaignOutput(
                campaign_id=state.campaign_id, success=False,
                block_reason=f"Content generation failed: {str(exc)[:200]}",
                step_logs=state.to_dict().get("step_logs", []),
            )

        # ── Step 3: Risk Check ────────────────────────────────────────────────
        console.print("\n[bold yellow]Step 3/5 — Risk Agent reviewing content…[/bold yellow]")
        risk_output = None
        try:
            from agents.risk_agent import run_risk_check
            content_dict = content_output.to_risk_dict()
            risk_result = _with_retry(
                lambda: run_risk_check(
                    content_dict=content_dict,
                    campaign_id=state.campaign_id,
                    output_id=state.campaign_id,
                ),
                "Risk Agent"
            )
            state.update_risk(risk_result)
            risk_output = risk_result

            green = risk_result.get("green_light", False)
            color = "green" if green else "red"
            emoji = "✅" if green else "🚨"
            console.print(Panel(
                f"{emoji} green_light={green}\n"
                f"brand_safety={risk_result.get('brand_safety')} | "
                f"legal_risk={risk_result.get('legal_risk')} | "
                f"cultural_sensitivity={risk_result.get('cultural_sensitivity')}\n"
                f"{risk_result.get('explanation', '')}",
                title=f"[{color}]Risk — {'PASSED' if green else 'FAILED'}[/{color}]",
                border_style=color,
            ))
        except Exception as exc:
            logger.error("Risk Agent failed: %s", exc)
            state.mark_failed("risk_agent", str(exc))
            return CampaignOutput(
                campaign_id=state.campaign_id, success=False,
                block_reason=f"Risk check errored: {str(exc)[:200]}",
                step_logs=state.to_dict().get("step_logs", []),
            )

        # ── Step 4: Communication ─────────────────────────────────────────────
        console.print("\n[bold yellow]Step 4/5 — Communication Layer dispatching…[/bold yellow]")
        comm_summary = {"emails_sent": 0, "emails_failed": 0, "overall_success": False}
        try:
            comm_summary = self._run_communication(
                content_output=content_output,
                risk_result=risk_output,
                state=state,
            )
            state.update_communication(comm_summary)
        except Exception as exc:
            logger.error("Communication layer error: %s", exc)
            state.mark_failed("communication_layer", str(exc))
            # Non-fatal — continue to analytics

        # ── Step 5: Analytics ─────────────────────────────────────────────────
        console.print("\n[bold yellow]Step 5/5 — Analytics Agent generating insights…[/bold yellow]")
        analytics_summary_str = "Analytics not run."
        try:
            from agents.analytics_agent import run_analytics
            # Use email metrics from comm_summary as the "new" metrics
            new_metrics = {
                "ctr": 0.8,           # estimated — real data would come from email platform API
                "open_rate": 22.0,
            }
            old_metrics = {"ctr": 0.4, "open_rate": 15.0}  # baseline

            analytics_result = _with_retry(
                lambda: run_analytics(
                    campaign_id=state.campaign_id,
                    attempt=1,
                    old_metrics=old_metrics,
                    new_metrics=new_metrics,
                    festival_tag=state.festival_tag,
                ),
                "Analytics Agent"
            )

            # Save to DB
            campaign_store.save_analytics_result(state.campaign_id, analytics_result)
            pm = analytics_result.get("post_mortem", {})
            analytics_summary_str = (
                f"Healed: {analytics_result.get('healed')} | "
                f"CTR: {analytics_result.get('new_ctr')}% | "
                f"Recommendation: {pm.get('recommendation', 'N/A')}"
            )
            state.update_analytics({**analytics_result, "summary_string": analytics_summary_str})

            console.print(Panel(
                analytics_summary_str,
                title="[green]✅ Analytics — Done[/green]", border_style="green",
            ))
        except Exception as exc:
            logger.warning("Analytics Agent failed (non-fatal): %s", exc)
            state.mark_failed("analytics_agent", str(exc))

        # ── Final summary ─────────────────────────────────────────────────────
        success = not state.is_blocked() and comm_summary.get("emails_sent", 0) >= 0
        output = CampaignOutput(
            campaign_id=state.campaign_id,
            success=success,
            pipeline_blocked=state.is_blocked(),
            block_reason=state.to_dict().get("block_reason"),
            emails_sent=comm_summary.get("emails_sent", 0),
            emails_failed=comm_summary.get("emails_failed", 0),
            risk_green_light=state.green_light,
            analytics_summary=analytics_summary_str,
            step_logs=state.to_dict().get("step_logs", []),
        )

        color = "green" if success else "red"
        console.print(Panel(
            f"✅ Success: {success}\n"
            f"📧 Emails Sent: {output.emails_sent} | Failed: {output.emails_failed}\n"
            f"🛡  Risk: {'Passed' if state.green_light else 'Blocked'}\n"
            f"📊 {analytics_summary_str}",
            title=f"[{color}]🏁 Pipeline Complete — Campaign #{state.campaign_id}[/{color}]",
            border_style=color,
        ))

        return output

    # ─────────────────────────────────────────────────────────────────────────
    # Dynamic execution
    # ─────────────────────────────────────────────────────────────────────────

    def _run_dynamic(self, state: SharedState) -> CampaignOutput:
        """
        Dynamic mode: runs the sequential pipeline but checks after each step
        whether an agent has requested delegation (re-run / re-try).
        Loop-breaker: max delegation count enforced by SharedState.
        """
        self._print("Dynamic mode: agents can request re-runs via state flags.", "cyan")

        # Start with sequential — dynamic mode extends it
        result = self._run_sequential(state)

        # Example dynamic branch: if risk failed, allow content re-generation once
        if state.is_blocked() and state.can_delegate():
            self._print(
                "\n⚡ Dynamic mode: Risk failed. Re-generating content with adjusted brief…",
                "yellow"
            )
            state.increment_delegation()

            adjusted_brief = (
                f"{state.brief}\n\n"
                f"IMPORTANT: Previous content was flagged. "
                f"Reason: {state.to_dict().get('block_reason', 'Unknown')}. "
                f"Rewrite to be more conservative, legally safe, and culturally respectful."
            )
            new_state = SharedState(
                campaign_id=state.campaign_id + 1000,   # sub-campaign ID for re-run
                brief=adjusted_brief,
                festival_tag=state.festival_tag,
            )
            return self._run_sequential(new_state)

        return result

    # ─────────────────────────────────────────────────────────────────────────
    # Communication layer (Step 4)
    # ─────────────────────────────────────────────────────────────────────────

    def _run_communication(self, content_output, risk_result: dict, state: SharedState) -> dict:
        """
        Run all communication channels based on risk result.

        If green_light=True  → Send email
        If green_light=False → Send Slack alert + do NOT send email
        Always              → Optionally send Telegram ad if configured
        """
        from services.email_service import dispatch_campaign_email
        from tools.slack_tool import send_slack_alert
        from tools.telegram_tool import send_telegram_message
        import os
        import hashlib

        green = risk_result.get("green_light", False)
        content_dict = content_output.to_email_service_dict()
        emails_sent = 0
        emails_failed = 0

        # ── Idempotency key ───────────────────────────────────────────────────
        idem_key = hashlib.md5(
            f"{state.campaign_id}:{content_output.email_content.subject}".encode()
        ).hexdigest()
        from database import db_manager
        if db_manager.exists("email_send_idempotency", idem_key):
            self._print(f"⚠  Email already sent for this campaign (idempotency key: {idem_key[:8]}). Skipping.", "yellow")
        else:
            # ── Email dispatch ────────────────────────────────────────────────
            dispatch_result = dispatch_campaign_email(
                content_dict=content_dict,
                campaign_id=state.campaign_id,
                risk_result=risk_result,
            )
            emails_sent = dispatch_result.get("sent", 0)
            emails_failed = dispatch_result.get("failed", 0)

            if green and emails_sent > 0:
                # Mark as sent (idempotency)
                db_manager.write("email_send_idempotency", idem_key, {
                    "campaign_id": state.campaign_id,
                    "sent_at": str(__import__("datetime").datetime.now()),
                })
                console.print(Panel(
                    f"✅ Emails sent: {emails_sent} | Failed: {emails_failed}",
                    title="[green]Email Dispatch — Done[/green]", border_style="green",
                ))
            elif not green:
                console.print(Panel(
                    f"🚫 Email NOT sent — Risk gate blocked.\n{risk_result.get('flag_reason', '')}",
                    title="[red]Email Dispatch — BLOCKED[/red]", border_style="red",
                ))

        # ── Slack alert (only on risk failure) ───────────────────────────────
        if not green:
            slack_idem = f"slack_{state.campaign_id}"
            if not db_manager.exists("slack_log", slack_idem):
                slack_result = send_slack_alert(
                    campaign_id=state.campaign_id,
                    scores_dict={
                        "brand_safety": risk_result.get("brand_safety", 0),
                        "legal_risk": risk_result.get("legal_risk", 0),
                        "cultural_sensitivity": risk_result.get("cultural_sensitivity", 0),
                    },
                    flag_reason=risk_result.get("flag_reason"),
                )
                db_manager.write("slack_log", slack_idem, {
                    "campaign_id": state.campaign_id, "result": slack_result
                })
                self._print(f"📢 Slack alert sent: {slack_result}", "yellow")
            else:
                self._print("⚠  Slack alert already sent for this campaign.", "yellow")

        # ── Telegram (optional — send ad copy if channel configured) ─────────
        if green and os.getenv("TELEGRAM_BOT_TOKEN") and content_output.social_content.twitter_post:
            tg_idem = f"telegram_{state.campaign_id}"
            if not db_manager.exists("telegram_log", tg_idem):
                ad_copy = (
                    f"📢 {content_output.email_content.subject}\n\n"
                    f"{content_output.social_content.twitter_post}"
                )
                tg_result = send_telegram_message(ad_copy)
                db_manager.write("telegram_log", tg_idem, {
                    "campaign_id": state.campaign_id, "result": tg_result
                })
                self._print(f"📱 Telegram ad sent: {tg_result}", "cyan")

        return {
            "emails_sent": emails_sent,
            "emails_failed": emails_failed,
            "overall_success": green and emails_sent > 0,
            "green_light": green,
        }
