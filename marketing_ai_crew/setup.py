#!/usr/bin/env python3
"""
setup.py — One-click setup script
Run this once after unzipping the project.
Usage: python setup.py
"""

import sys
import os
import subprocess

RED    = "\033[91m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
BLUE   = "\033[94m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def ok(msg):  print(f"{GREEN}  ✓ {msg}{RESET}")
def err(msg): print(f"{RED}  ✗ {msg}{RESET}")
def info(msg):print(f"{BLUE}  → {msg}{RESET}")
def warn(msg):print(f"{YELLOW}  ⚠ {msg}{RESET}")
def head(msg):print(f"\n{BOLD}{msg}{RESET}\n{'─'*50}")


def check_python():
    head("Step 1 — Python Version")
    v = sys.version_info
    if v.major < 3 or (v.major == 3 and v.minor < 10):
        err(f"Python 3.10+ required. You have {v.major}.{v.minor}")
        err("Install from https://python.org")
        sys.exit(1)
    ok(f"Python {v.major}.{v.minor}.{v.micro}")


def check_pip():
    head("Step 2 — Install Dependencies")
    info("Running: pip install -r requirements.txt")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        err("pip install failed:")
        print(result.stderr[-1000:])
        sys.exit(1)
    ok("All Python dependencies installed")


def check_api_key():
    head("Step 3 — API Key Configuration")
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key and api_key != "your_gemini_api_key_here":
        ok("GEMINI_API_KEY is configured properly.")
        return True
    else:
        warn("GEMINI_API_KEY is missing or invalid in .env")
        info("Please open your .env file and add your Gemini API Key.")
        print()
        return False


def create_outputs_dir():
    head("Step 4 — Output Directory")
    os.makedirs("outputs", exist_ok=True)
    ok("outputs/ directory ready")


def final_summary(ready: bool):
    head("Setup Summary")
    if ready:
        print(f"{GREEN}{BOLD}  Everything is ready!{RESET}\n")
        print("  Run any of these:\n")
        print(f"  {BLUE}python main.py --list{RESET}              # See all 10 agents")
        print(f"  {BLUE}python main.py --agent analytics{RESET}   # Run analytics agent")
        print(f"  {BLUE}python main.py --agent content{RESET}     # Run content agent")
        print(f"  {BLUE}python dashboard/app.py{RESET}            # Launch web dashboard")
        print()
        print(f"  Or use shortcuts:")
        print(f"  {BLUE}make analytics{RESET}")
        print(f"  {BLUE}make dashboard{RESET}")
        print(f"  {BLUE}make tier1{RESET}")
        print()
    else:
        print(f"{YELLOW}{BOLD}  Setup incomplete — fix the warnings above, then run again.{RESET}")
        print()
        print("  Quick checklist:")
        print("  1. Open .env")
        print("  2. Replace 'your_gemini_api_key_here' with your real API key")
        print("  3. Run: python setup.py  (this script) again")
        print()


if __name__ == "__main__":
    print(f"\n{BOLD}  Marketing AI Crew — Setup{RESET}")
    print(f"  {'─'*40}")

    from dotenv import load_dotenv
    load_dotenv()

    check_python()
    check_pip()

    api_key_ready = check_api_key()
    create_outputs_dir()

    final_summary(ready=api_key_ready)
