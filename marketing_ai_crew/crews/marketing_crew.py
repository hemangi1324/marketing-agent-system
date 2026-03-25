"""
crews/marketing_crew.py
Orchestrates agents. Run one agent, a tier, or the full crew.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from crewai import Crew, Process
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

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
        "[bold]Running all 10 marketing agents sequentially.[/bold]\nThis will take several minutes on local Ollama.",
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
