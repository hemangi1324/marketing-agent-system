"""
tests/test_agents.py
Tests that all 10 agents instantiate correctly without running the LLM.
Run: python -m pytest tests/test_agents.py -v
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from dotenv import load_dotenv
load_dotenv()

# Patch LLM so tests run without Ollama
from unittest.mock import patch, MagicMock

MOCK_LLM = MagicMock()
MOCK_LLM.model_name = "mock-llama"


@pytest.fixture(autouse=True)
def mock_llm():
    with patch("config.settings.get_llm", return_value=MOCK_LLM):
        yield


def test_all_agents_importable():
    from agents.all_agents import get_all_agents
    agents = get_all_agents()
    assert len(agents) == 10, f"Expected 10 agents, got {len(agents)}"
    print(f"\n  Loaded {len(agents)} agents: {list(agents.keys())}")


@pytest.mark.parametrize("agent_name", [
    "content", "social", "leads", "analytics", "email",
    "ads", "community", "product_marketing", "pr", "brand_strategy"
])
def test_agent_has_required_fields(agent_name):
    from agents.all_agents import get_all_agents
    agents = get_all_agents()
    agent = agents[agent_name]
    assert agent.role,      f"{agent_name} missing role"
    assert agent.goal,      f"{agent_name} missing goal"
    assert agent.backstory, f"{agent_name} missing backstory"
    assert len(agent.tools) > 0, f"{agent_name} has no tools"
    print(f"\n  {agent_name}: role='{agent.role[:40]}...' tools={len(agent.tools)}")


def test_tier1_agents_have_brand_tool():
    """All Tier 1 agents must have the brand guidelines tool."""
    from agents.all_agents import get_all_agents
    from tools.file_tool import BrandGuidelinesTool
    agents = get_all_agents()
    tier1 = ["content", "social", "leads", "email"]
    for name in tier1:
        tool_types = [type(t).__name__ for t in agents[name].tools]
        assert "BrandGuidelinesTool" in tool_types, \
            f"{name} agent missing BrandGuidelinesTool"
    print(f"\n  All Tier 1 agents have BrandGuidelinesTool OK")


def test_leads_agent_has_crm_tools():
    """Lead gen agent must have CRM tools."""
    from agents.all_agents import get_all_agents
    agents = get_all_agents()
    tool_types = [type(t).__name__ for t in agents["leads"].tools]
    assert "CRMCreateContactTool" in tool_types
    assert "CRMListContactsTool" in tool_types
    print(f"\n  Lead gen agent has CRM tools: {tool_types}")


def test_ads_agent_has_performance_tool():
    from agents.all_agents import get_all_agents
    agents = get_all_agents()
    tool_types = [type(t).__name__ for t in agents["ads"].tools]
    assert "AdsGetPerformanceTool" in tool_types
    assert "AdsPauseCampaignTool" in tool_types
    print(f"\n  Ads agent has performance + pause tools OK")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
