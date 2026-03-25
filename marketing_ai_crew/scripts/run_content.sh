#!/bin/bash
# Run the Content & Branding agent
cd "$(dirname "$0")/.."
echo "Running Content & Branding agent..."
python main.py --agent content --task "${1:-Write content for our latest product update}"
