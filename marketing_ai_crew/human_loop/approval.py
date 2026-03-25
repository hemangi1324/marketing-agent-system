"""
human_loop/approval.py

Human-in-the-loop approval gate for Tier 2 (Partial) and Tier 3 (Human-led) agents.

How it works:
  - Tier 2 agents (ads, community, product_marketing) generate output,
    then pause and ask a human to approve before "acting" (posting, spending, etc.)
  - Tier 3 agents (pr, brand_strategy) always produce DRAFT output only.

Usage in a task callback:
    from human_loop.approval import request_approval
    task = Task(..., callback=request_approval)

Standalone usage:
    approved = request_approval(task_output)
"""

import os
import json
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

console = Console()

APPROVAL_LOG = os.path.join(
    os.path.dirname(__file__), "..", "outputs", "approval_log.json"
)


def _load_log():
    if os.path.exists(APPROVAL_LOG):
        with open(APPROVAL_LOG) as f:
            return json.load(f)
    return []


def _save_log(log):
    os.makedirs(os.path.dirname(APPROVAL_LOG), exist_ok=True)
    with open(APPROVAL_LOG, "w") as f:
        json.dump(log, f, indent=2)


def request_approval(task_output) -> bool:
    """
    Called as a CrewAI task callback.
    Displays the agent output and asks for human approval.
    Returns True if approved, False if rejected.

    Usage:
        task = Task(description="...", agent=ads_agent, callback=request_approval)
    """
    output_text = str(task_output)

    console.print("\n")
    console.print(Panel(
        output_text[:2000] + ("..." if len(output_text) > 2000 else ""),
        title="[bold yellow]⚠️  HUMAN REVIEW REQUIRED[/bold yellow]",
        border_style="yellow",
        subtitle="Tier 2/3 agent output — review before approving",
    ))

    console.print(
        "\n[bold yellow]This agent has produced output that requires your review.[/bold yellow]\n"
        "  • For [cyan]ads agents[/cyan]: check budget recommendations before approving\n"
        "  • For [cyan]community agents[/cyan]: personalise outreach emails before sending\n"
        "  • For [cyan]PR agents[/cyan]: all output is DRAFT — never publish directly\n"
    )

    approved = Confirm.ask("[bold]Do you approve this output?[/bold]", default=False)
    notes    = ""

    if not approved:
        notes = Prompt.ask("Rejection reason (optional)", default="")

    # Log the decision
    log = _load_log()
    log.append({
        "timestamp": datetime.now().isoformat(),
        "approved": approved,
        "notes": notes,
        "output_preview": output_text[:500],
    })
    _save_log(log)

    if approved:
        console.print("[bold green]✓ Approved — output logged.[/bold green]\n")
    else:
        console.print(f"[bold red]✗ Rejected.[/bold red]"
                      + (f" Reason: {notes}" if notes else "") + "\n")

    return approved


def auto_flag_for_review(output_text: str, agent_name: str) -> str:
    """
    Wraps any output text with a clear human-review header.
    Used by Tier 3 agents (PR, brand strategy) to mark all output as draft.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    header = (
        f"\n{'='*60}\n"
        f"⚠️  DRAFT OUTPUT — HUMAN REVIEW REQUIRED\n"
        f"Agent: {agent_name}\n"
        f"Generated: {timestamp}\n"
        f"Status: DO NOT PUBLISH OR SEND WITHOUT REVIEW\n"
        f"{'='*60}\n\n"
    )
    return header + output_text


def get_approval_history() -> list:
    """Returns full approval log for dashboard display."""
    return _load_log()


# ── Standalone demo ───────────────────────────────────────────
if __name__ == "__main__":
    demo_output = """
AD PERFORMANCE ANALYSIS
=======================
Campaign 'Lead Gen - Free Trial' is underperforming (ROAS: 0.8x).

RECOMMENDATION: Pause campaign_id=c003 and reallocate $30/day budget
to campaign 'Brand Awareness Q1' which shows 3.2% CTR.

⚠️  BUDGET CHANGE — requires human approval before execution.
"""
    approved = request_approval(demo_output)
    print(f"\nDecision: {'APPROVED' if approved else 'REJECTED'}")
