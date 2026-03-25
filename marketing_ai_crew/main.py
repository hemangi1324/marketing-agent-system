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
    help="Agent key: content|social|leads|analytics|email|ads|community|product_marketing|pr|brand_strategy|tier1|tier2|tier3|all")
@click.option("--task",  "-t", default="", help="Task brief. Leave blank for default.")
@click.option("--quiet", "-q", is_flag=True, default=False)
@click.option("--list",  "-l", "list_agents", is_flag=True, default=False)
def main(agent, task, quiet, list_agents):
    """Marketing AI Crew — 100% free with Ollama + Llama 3"""
    from crews.marketing_crew import run_single_agent, run_full_crew, run_tier, print_menu

    if list_agents:
        print_menu()
        return

    verbose = not quiet

    if agent == "all":
        run_full_crew(verbose=verbose)
    elif agent.startswith("tier"):
        run_tier(tier=int(agent.replace("tier", "")), verbose=verbose)
    else:
        run_single_agent(agent_name=agent, brief=task, verbose=verbose)


if __name__ == "__main__":
    main()
