# ============================================================
# Makefile — Marketing AI Crew shortcuts
# Usage: make <target>
# ============================================================

.PHONY: help setup check run dashboard test clean \
        content social leads analytics email \
        ads community product pr brand \
        tier1 tier2 tier3 all

# ── Default: show help ──────────────────────────────────────
help:
	@echo ""
	@echo "  Marketing AI Crew — Make Commands"
	@echo "  =================================="
	@echo ""
	@echo "  Setup"
	@echo "    make setup       Install Python dependencies"
	@echo "    make check       Verify Ollama is running + model is ready"
	@echo ""
	@echo "  Run Agents (CLI)"
	@echo "    make content     Content & Branding agent"
	@echo "    make social      Social Media agent"
	@echo "    make leads       Lead Generation agent"
	@echo "    make analytics   Analytics & Research agent"
	@echo "    make email       Email Campaigns agent"
	@echo "    make ads         Campaigns & Ads agent"
	@echo "    make community   Community & Events agent"
	@echo "    make product     Product Marketing agent"
	@echo "    make pr          PR & Reputation agent"
	@echo "    make brand       Brand Strategy agent"
	@echo ""
	@echo "  Run Groups"
	@echo "    make tier1       All Tier 1 agents (fully automatable)"
	@echo "    make tier2       All Tier 2 agents (partial)"
	@echo "    make tier3       All Tier 3 agents (human-led)"
	@echo "    make all         All 10 agents (takes a while)"
	@echo ""
	@echo "  Dashboard"
	@echo "    make dashboard   Launch web UI at http://localhost:5000"
	@echo ""
	@echo "  Dev"
	@echo "    make test        Run all tests"
	@echo "    make clean       Remove generated output files"
	@echo ""

# ── Setup ───────────────────────────────────────────────────
setup:
	pip install -r requirements.txt
	@echo "Done! Now run: make check"

check:
	python check_setup.py

# ── Individual Agents ───────────────────────────────────────
content:
	python main.py --agent content

social:
	python main.py --agent social

leads:
	python main.py --agent leads

analytics:
	python main.py --agent analytics

email:
	python main.py --agent email

ads:
	python main.py --agent ads

community:
	python main.py --agent community

product:
	python main.py --agent product_marketing

pr:
	python main.py --agent pr

brand:
	python main.py --agent brand_strategy

# ── Groups ──────────────────────────────────────────────────
tier1:
	python main.py --agent tier1

tier2:
	python main.py --agent tier2

tier3:
	python main.py --agent tier3

all:
	python main.py --agent all

# ── Dashboard ───────────────────────────────────────────────
dashboard:
	@echo "Starting dashboard at http://localhost:5000"
	python dashboard/app.py

# ── Dev ─────────────────────────────────────────────────────
test:
	python -m pytest tests/ -v

test-tools:
	python -m pytest tests/test_tools.py -v -k "not search"

test-agents:
	python -m pytest tests/test_agents.py -v

test-tasks:
	python -m pytest tests/test_tasks.py -v

clean:
	find outputs/ -name "*.md" -delete
	find outputs/ -name "*.json" -not -name ".gitkeep" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@echo "Outputs cleaned."

list:
	python main.py --list
