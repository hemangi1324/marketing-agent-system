"""
main.py — CLI entry point

Usage examples:
  python main.py                              # Show menu + run content agent (default)
  python main.py --agent analytics            # Run analytics agent
  python main.py --agent leads --task "Find fintech SaaS prospects"
  python main.py --agent all                  # Full crew (slow on local)
  python main.py --agent tier1               # Run tier 1 only
  python main.py --list                       # Show all agents
  python main.py --orchestrator --task "Diwali sale campaign" --campaign-id 100
  python main.py --orchestrator --mode dynamic --task "Holi promo" --campaign-id 101
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import click
from rich.console import Console
from dotenv import load_dotenv

load_dotenv()
console = Console()


@click.command()
@click.option("--agent", "-a", default="all",
    help="Agent key: content|analytics|brand_strategy|risk|all")
@click.option("--task",  "-t", default="", help="Task brief. Leave blank for default.")
@click.option("--quiet", "-q", is_flag=True, default=False)
@click.option("--list",  "-l", "list_agents", is_flag=True, default=False)
@click.option("--campaign-id", "-c", default=1, type=int,
    help="Campaign ID for email pipeline logging (default: 1).")
@click.option("--schedule", is_flag=True, default=False,
    help="Start the APScheduler daemon for event-based campaign scheduling.")
@click.option("--run-now", is_flag=True, default=False,
    help="Trigger the scheduler's daily campaign check immediately (use with --schedule).")
@click.option("--orchestrator", "-o", is_flag=True, default=False,
    help="Run the full pipeline via the UniversalOrchestrator (recommended).")
@click.option("--mode", default="sequential",
    type=click.Choice(["sequential", "dynamic"], case_sensitive=False),
    help="Orchestrator execution mode: sequential (default) or dynamic.")
@click.option("--festival", "-f", default=None,
    help="Festival tag for the orchestrator run (e.g. diwali, holi, christmas).")
@click.option("--force-rerun", is_flag=True, default=False,
    help="Force orchestrator to re-run even if campaign_id already exists in DB.")
def main(agent, task, quiet, list_agents, campaign_id, schedule, run_now,
         orchestrator, mode, festival, force_rerun):
    """Marketing AI Crew — AI agents for every marketing channel"""

    # ── Scheduler mode ──────────────────────────────────────────────────────
    if schedule:
        from scheduler.email_scheduler import start_scheduler, daily_campaign_check
        if run_now:
            console.print("[yellow]Running scheduler campaign check NOW…[/yellow]")
            daily_campaign_check()
        else:
            start_scheduler()   # blocks until Ctrl+C
        return

    if list_agents:
        from crews.marketing_crew import print_menu
        print_menu()
        return

    verbose = not quiet

    # ── Universal Orchestrator mode ──────────────────────────────────────────
    if orchestrator:
        from orchestrator import UniversalOrchestrator
        brief = task or "Create a compelling marketing campaign for our SaaS product"
        console.print(f"[cyan]🚀 Launching UniversalOrchestrator (mode={mode})…[/cyan]")
        orch = UniversalOrchestrator(verbose=verbose)
        result = orch.run_pipeline(
            brief=brief,
            campaign_id=campaign_id,
            festival_tag=festival,
            mode=mode,
            force_rerun=force_rerun,
        )
        console.print(f"\n[bold]Pipeline result:[/bold] success={result.success} | "
                      f"emails_sent={result.emails_sent}")
        return

    # ── Email pipeline mode ─────────────────────────────────────────────────
    # if agent == "email-pipeline":
    #     from crews.marketing_crew import run_email_campaign_pipeline
    #     run_email_campaign_pipeline(brief=task, campaign_id=campaign_id, verbose=verbose)
    #     return

    from crews.marketing_crew import run_single_agent, run_full_crew
    if agent == "all":
        run_full_crew(verbose=verbose)
    else:
        run_single_agent(agent_name=agent, brief=task, verbose=verbose)


if __name__ == "__main__":
    main()

