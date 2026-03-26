"""
crews/marketing_crew.py
Orchestrates agents. Run one agent, a tier, or the full crew.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
import re
from crewai import Crew, Process
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from agents.all_agents import get_all_agents
from tasks.task_factory import get_task, DEFAULT_BRIEFS, TASK_MAP

console = Console()

AGENT_META = {
    "content":           ("Content & Branding",    1, "Full",      "green"),
    "social":            ("Social Media",           1, "Full",      "green"),
    "leads":             ("Lead Generation",        1, "Full",      "green"),
    "analytics":         ("Analytics & Research",   1, "Full",      "green"),
    "email":             ("Email Campaigns",        1, "Full",      "green"),
    "ads":               ("Campaigns & Ads",        2, "Partial",   "yellow"),
    "community":         ("Community & Events",     2, "Partial",   "yellow"),
    "product_marketing": ("Product Marketing",      2, "Partial",   "yellow"),
    "pr":                ("PR & Reputation",        3, "Human-led", "red"),
    "brand_strategy":    ("Brand Strategy",         3, "Human-led", "red"),
}

TIER_AGENTS = {
    1: ["content", "social", "leads", "analytics", "email", "risk", "analytics"],
    2: ["ads", "community", "product_marketing"],
    3: ["pr", "brand_strategy"],
}


def run_single_agent(agent_name: str, brief: str = "", verbose: bool = True):
    agents = get_all_agents()
    if agent_name not in agents:
        raise ValueError(f"Unknown agent '{agent_name}'. Options: {list(agents.keys())}")

    meta = AGENT_META[agent_name]
    console.print(Panel(
        f"[bold]Agent:[/bold] [{meta[3]}]{meta[0]}[/{meta[3]}]  "
        f"[bold]Tier:[/bold] {meta[1]}  [bold]Coverage:[/bold] {meta[2]}\n"
        f"[bold]Brief:[/bold] {brief or DEFAULT_BRIEFS[agent_name]}",
        title="[bold cyan]Marketing AI Crew — Ollama + Llama 3[/bold cyan]",
        border_style="cyan",
    ))

    agent = agents[agent_name]
    task  = get_task(agent_name, agent, brief)

    crew = Crew(
        agents=[agent], tasks=[task],
        process=Process.sequential, verbose=verbose,
    )
    result = crew.kickoff()
    console.print(Panel(str(result), title=f"[green]Done: {meta[0]}[/green]", border_style="green"))
    return result


def run_tier(tier: int, briefs: dict = None, verbose: bool = True):
    names = TIER_AGENTS.get(tier, [])
    if not names:
        raise ValueError(f"Tier must be 1, 2, or 3.")
    briefs  = briefs or {}
    agents  = get_all_agents()
    console.print(Panel(
        f"Running Tier {tier} agents: {', '.join(names)}",
        title=f"[bold yellow]Tier {tier} Crew[/bold yellow]", border_style="yellow",
    ))
    sel_agents = [agents[n] for n in names]
    sel_tasks  = [get_task(n, agents[n], briefs.get(n, "")) for n in names]
    crew = Crew(agents=sel_agents, tasks=sel_tasks, process=Process.sequential, verbose=verbose)
    return crew.kickoff()


def run_full_crew(briefs: dict = None, verbose: bool = True):
    console.print(Panel(
        "[bold]Running all 10 marketing agents sequentially.[/bold]\n",
        title="[bold magenta]Full Marketing Crew[/bold magenta]", border_style="magenta",
    ))
    agents = get_all_agents()
    briefs = briefs or {}
    all_agents = list(agents.values())
    all_tasks  = [get_task(n, agents[n], briefs.get(n, "")) for n in agents]
    crew = Crew(agents=all_agents, tasks=all_tasks, process=Process.sequential, verbose=verbose)
    result = crew.kickoff()
    console.print(Panel("All agents done! Check the outputs/ folder.", border_style="green"))
    return result


# ══════════════════════════════════════════════════════════════════════════════
#  EMAIL CAMPAIGN PIPELINE: Content Agent → Risk Check → SMTP Send
# ══════════════════════════════════════════════════════════════════════════════

def _extract_content_dict(raw_output: str) -> dict:
    """
    Parse the content agent's raw markdown/text output into a structured dict.
    Looks for labelled sections (email subject, body, instagram, twitter).
    Falls back to using the whole output as the email body.
    """
    text = str(raw_output).strip()

    def _find(patterns, fallback=""):
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE | re.DOTALL)
            if m:
                return m.group(1).strip()
        return fallback

    email_subject = _find([
        r"(?:email subject(?:s?|\s*line?s?)[:\s*\-]+)([^\n]+)",
        r"subject[:\s]+([^\n]+)",
        r"##?\s*email subject[:\s]*\n+([^\n]+)",
    ])

    email_body = _find([
        r"email body[:\s*]*\n+(.+?)(?=\n##|\n\*\*instagram|\n\*\*twitter|\Z)",
        r"body[:\s*]*\n+(.+?)(?=\n##|\n\*\*|\Z)",
    ], fallback=text[:1500] if not email_subject else "")

    instagram_caption = _find([
        r"instagram caption[s]?[:\s*]*\n+([^\n]+(?:\n(?!\n)[^\n]+)*)",
        r"instagram[:\s]+([^\n]+)",
    ])

    twitter_post = _find([
        r"twitter(?:/x)?\s*post[:\s*]*\n+([^\n]+(?:\n(?!\n)[^\n]+)*)",
        r"twitter[:\s]+([^\n]+)",
    ])

    if not email_subject:
        # Grab first non-empty line as subject
        for line in text.split("\n"):
            line = line.strip().lstrip("#*- ")
            if len(line) > 10:
                email_subject = line[:120]
                break

    if not email_body:
        email_body = text[:2000]

    return {
        "email_subject":     email_subject,
        "email_body":        email_body,
        "instagram_caption": instagram_caption,
        "twitter_post":      twitter_post,
    }


def run_email_campaign_pipeline(
    brief: str = "",
    campaign_id: int = 1,
    verbose: bool = True,
) -> dict:
    """
    Full end-to-end email campaign pipeline:
        1. Content Agent generates email content (subject + body + social copy)
        2. Risk Agent validates the content (brand safety, legal, cultural)
        3. If green_light=True  → dispatch real emails via SMTP
           If green_light=False → block and log the reason; NO emails sent

    Args:
        brief       : campaign brief describing what the email should convey
        campaign_id : numeric ID used for logging and email headers
        verbose     : whether to print CrewAI step output

    Returns:
        dict with pipeline results:
            content_dict   — parsed content from the agent
            risk_result    — full risk assessment dict
            dispatch_result — email send summary (sent, failed, blocked)
    """
    from agents.risk_agent import run_risk_check
    from services.email_service import dispatch_campaign_email

    brief = brief or DEFAULT_BRIEFS.get("email", "Write a promotional email campaign.")

    console.print(Panel(
        f"[bold]Campaign ID:[/bold] #{campaign_id}\n"
        f"[bold]Brief:[/bold] {brief}",
        title="[bold cyan]📧 Email Campaign Pipeline[/bold cyan]",
        border_style="cyan",
    ))

    # ── Step 1: Content Agent ─────────────────────────────────────────────────
    console.print("\n[bold yellow]Step 1/3 — Content Agent generating email…[/bold yellow]")
    agents = get_all_agents()
    content_agent = agents["email"]
    content_task  = get_task("email", content_agent, brief)

    content_crew = Crew(
        agents=[content_agent],
        tasks=[content_task],
        process=Process.sequential,
        verbose=verbose,
    )
    import time

    _MAX_RETRIES = 3
    _RETRY_DELAY = 15  # seconds between retries on transient errors

    raw_output = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            raw_output = content_crew.kickoff()
            break  # success — exit retry loop
        except Exception as exc:
            err_str = str(exc)
            is_transient = any(code in err_str for code in ["503", "429", "UNAVAILABLE", "RESOURCE_EXHAUSTED"])
            if is_transient and attempt < _MAX_RETRIES:
                console.print(
                    f"[yellow]⚠  Gemini API busy (attempt {attempt}/{_MAX_RETRIES}). "
                    f"Retrying in {_RETRY_DELAY}s…[/yellow]"
                )
                time.sleep(_RETRY_DELAY)
            else:
                console.print(f"[red]❌  Content Agent failed after {attempt} attempt(s): {err_str[:200]}[/red]")
                raise

    content_dict = _extract_content_dict(str(raw_output))

    console.print(Panel(
        f"[bold]Subject:[/bold] {content_dict.get('email_subject', '(not found)')}\n"
        f"[bold]Body preview:[/bold] {content_dict.get('email_body', '')[:200]}…",
        title="[green]Content Agent — Done[/green]",
        border_style="green",
    ))

    # ── Step 2: Risk Agent ────────────────────────────────────────────────────
    console.print("\n[bold yellow]Step 2/3 — Risk Agent reviewing content…[/bold yellow]")
    risk_result = run_risk_check(
        content_dict=content_dict,
        campaign_id=campaign_id,
        output_id=None,
    )

    green  = risk_result.get("green_light", False)
    scores = (
        f"brand_safety={risk_result.get('brand_safety')}  "
        f"legal_risk={risk_result.get('legal_risk')}  "
        f"cultural_sensitivity={risk_result.get('cultural_sensitivity')}"
    )
    color  = "green" if green else "red"
    emoji  = "✅" if green else "🚨"
    console.print(Panel(
        f"{emoji} green_light={green}\n{scores}\n"
        f"Explanation: {risk_result.get('explanation', '')}",
        title=f"[{color}]Risk Agent — {'PASSED' if green else 'FAILED'}[/{color}]",
        border_style=color,
    ))

    # ── Step 3: Dispatch ──────────────────────────────────────────────────────
    console.print("\n[bold yellow]Step 3/3 — Dispatching emails…[/bold yellow]")
    dispatch_result = dispatch_campaign_email(
        content_dict=content_dict,
        campaign_id=campaign_id,
        risk_result=risk_result,
    )

    blocked = dispatch_result.get("blocked", False)
    if blocked:
        console.print(Panel(
            f"🚫 Emails NOT sent — risk gate blocked.\n"
            f"Reason: {dispatch_result.get('block_reason', '')}",
            title="[red]Email Dispatch — BLOCKED[/red]",
            border_style="red",
        ))
    else:
        console.print(Panel(
            f"✅ Sent: {dispatch_result.get('sent', 0)}  "
            f"Failed: {dispatch_result.get('failed', 0)}  "
            f"Total: {dispatch_result.get('recipients', 0)}\n"
            f"Check outputs/email_send_log.jsonl for details.",
            title="[green]Email Dispatch — COMPLETE[/green]",
            border_style="green",
        ))

    return {
        "content_dict":    content_dict,
        "risk_result":     risk_result,
        "dispatch_result": dispatch_result,
    }


def print_menu():
    t = Table(title="Available Marketing Agents (Ollama + Llama 3)", show_lines=True)
    t.add_column("Key",      style="cyan",  no_wrap=True)
    t.add_column("Agent",    style="bold")
    t.add_column("Tier",     style="white")
    t.add_column("Coverage", style="white")
    t.add_column("Default Brief")
    for k, (name, tier, cov, color) in AGENT_META.items():
        t.add_row(k, f"[{color}]{name}[/{color}]", str(tier), cov, DEFAULT_BRIEFS[k])
    console.print(t)
