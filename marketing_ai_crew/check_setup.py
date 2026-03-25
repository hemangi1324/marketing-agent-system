#!/usr/bin/env python3
"""
check_setup.py — Verify basic setup before running agents.
"""
import os
import sys
from dotenv import load_dotenv

RED    = "\033[91m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RESET  = "\033[0m"

def main():
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key and api_key != "your_gemini_api_key_here":
        print(f"{GREEN}✓ GEMINI_API_KEY is set.{RESET}")
        print("Setup looks good! You can run the dashboard or agents.")
        sys.exit(0)
    else:
        print(f"{RED}✗ GEMINI_API_KEY is missing or invalid in .env{RESET}")
        print(f"{YELLOW}Please edit your .env file and add your Gemini API key.{RESET}")
        sys.exit(1)

if __name__ == "__main__":
    main()
