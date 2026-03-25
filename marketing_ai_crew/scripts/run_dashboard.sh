#!/bin/bash
# Start the web dashboard
cd "$(dirname "$0")/.."
echo "Starting Marketing AI Crew Dashboard..."
echo "Open http://localhost:5000 in your browser"
echo ""
python dashboard/app.py
