"""
main.py — CLI entry point

Usage examples:
  python main.py                              # Show menu + run content agent (default)
  python main.py --agent analytics            # Run analytics agent
  python main.py --agent leads --task "Find fintech SaaS prospects"
  python main.py --agent all                  # Full crew (slow on local)
  python main.py --agent tier1               # Run tier 1 only
  python main.py --list                       # Show all agents
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import click
from rich.console import Console
from dotenv import load_dotenv

load_dotenv()
console = Console()


@click.command()
@click.option("--agent", "-a", default="content",
    help="Agent key: content|social|leads|analytics|email|ads|community|product_marketing|pr|brand_strategy|tier1|tier2|tier3|all|email-pipeline")
@click.option("--task",  "-t", default="", help="Task brief. Leave blank for default.")
@click.option("--quiet", "-q", is_flag=True, default=False)
@click.option("--list",  "-l", "list_agents", is_flag=True, default=False)
@click.option("--campaign-id", "-c", default=1, type=int,
    help="Campaign ID for email pipeline logging (default: 1).")
@click.option("--schedule", is_flag=True, default=False,
    help="Start the APScheduler daemon for event-based campaign scheduling.")
@click.option("--run-now", is_flag=True, default=False,
    help="Trigger the scheduler's daily campaign check immediately (use with --schedule).")
def main(agent, task, quiet, list_agents, campaign_id, schedule, run_now):
    """Marketing AI Crew — AI agents for every marketing channel"""
    from crews.marketing_crew import run_single_agent, run_full_crew, run_tier, print_menu

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
        print_menu()
        return

    verbose = not quiet

    # ── Email pipeline mode ─────────────────────────────────────────────────
    if agent == "email-pipeline":
        from crews.marketing_crew import run_email_campaign_pipeline
        run_email_campaign_pipeline(brief=task, campaign_id=campaign_id, verbose=verbose)
        return

    if agent == "all":
        run_full_crew(verbose=verbose)
    elif agent.startswith("tier"):
        run_tier(tier=int(agent.replace("tier", "")), verbose=verbose)
    else:
        run_single_agent(agent_name=agent, brief=task, verbose=verbose)


if __name__ == "__main__":
    main()
