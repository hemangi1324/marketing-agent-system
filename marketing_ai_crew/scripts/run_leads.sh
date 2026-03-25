#!/bin/bash
# Run the Lead Generation agent
cd "$(dirname "$0")/.."
INDUSTRY="${1:-fintech}"
echo "Finding leads in: $INDUSTRY"
python main.py --agent leads --task "Find 3 qualified prospects in the $INDUSTRY space for our SaaS product"
