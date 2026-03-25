#!/bin/bash
# Run all Tier 1 (fully automatable) agents sequentially
cd "$(dirname "$0")/.."
echo "========================================="
echo "  Running Tier 1 — All Automatable Agents"
echo "========================================="
echo ""
python main.py --agent tier1
echo ""
echo "Done! Check outputs/ folder for all results."
ls outputs/*.md 2>/dev/null | tail -10
