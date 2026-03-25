#!/bin/bash
# Run the Analytics agent and open the report
cd "$(dirname "$0")/.."
echo "Running Analytics agent..."
python main.py --agent analytics
echo ""
echo "Latest report:"
ls -t outputs/analytics_*.md 2>/dev/null | head -1 | xargs cat 2>/dev/null || echo "No report yet"
