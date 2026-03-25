"""
run_email_pipeline.py
----------------------
Standalone one-command runner for the email campaign pipeline.

Usage:
    # Basic run with default brief:
    python run_email_pipeline.py

    # With a custom brief:
    python run_email_pipeline.py --brief "Announce our summer sale — 30% off annual plans"

    # With a campaign ID:
    python run_email_pipeline.py --campaign-id 5 --brief "Weekly product tips newsletter"

    # Quiet mode (less verbose CrewAI output):
    python run_email_pipeline.py --quiet

What this does:
    1. Runs the Email Campaign Agent to generate email content
    2. Runs the Risk Agent to validate the content
    3. If risk passes → sends real emails via SMTP
    4. If risk fails  → blocks and logs the reason (NO emails sent)
    5. Prints a rich summary to the terminal
    6. Logs every send attempt to: outputs/email_send_log.jsonl
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

load_dotenv()
console = Console()


@click.command()
@click.option(
    "--brief", "-b", default="",
    help="Campaign brief describing what the email should be about. Leave blank for default.",
)
@click.option(
    "--campaign-id", "-c", default=1, type=int,
    help="Campaign ID for logging and tracking (default: 1).",
)
@click.option(
    "--quiet", "-q", is_flag=True, default=False,
    help="Suppress verbose CrewAI agent output.",
)
def main(brief, campaign_id, quiet):
    """
    Marketing AI Crew — Email Campaign Pipeline Runner

    Runs: Content Agent → Risk Agent → SMTP Email Dispatch
    """
    from crews.marketing_crew import run_email_campaign_pipeline

    console.print(Panel(
        "[bold]Marketing AI Crew — Email Campaign Pipeline[/bold]\n"
        "Content Agent → Risk Agent → SMTP Email Dispatch\n\n"
        f"Campaign ID : #{campaign_id}\n"
        f"Brief       : {brief or '(default brief will be used)'}",
        title="[bold magenta]📧 Starting Pipeline[/bold magenta]",
        border_style="magenta",
    ))

    result = run_email_campaign_pipeline(
        brief=brief,
        campaign_id=campaign_id,
        verbose=not quiet,
    )

    # Final summary
    dispatch = result.get("dispatch_result", {})
    risk     = result.get("risk_result", {})
    content  = result.get("content_dict", {})

    console.print("\n")
    console.print(Panel(
        f"[bold]Subject:[/bold]      {content.get('email_subject', 'N/A')}\n"
        f"[bold]Risk green_light:[/bold] {risk.get('green_light')}\n"
        f"[bold]Blocked:[/bold]      {dispatch.get('blocked', False)}\n"
        f"[bold]Emails sent:[/bold]  {dispatch.get('sent', 0)}\n"
        f"[bold]Emails failed:[/bold]{dispatch.get('failed', 0)}\n\n"
        "📄 Full send log: [cyan]outputs/email_send_log.jsonl[/cyan]\n"
        "📄 Scheduler state: [cyan]outputs/scheduler_state.json[/cyan]",
        title="[bold green]✅ Pipeline Complete[/bold green]",
        border_style="green",
    ))

    # Exit with error code if emails were blocked or failed
    if dispatch.get("blocked"):
        sys.exit(1)


if __name__ == "__main__":
    main()
