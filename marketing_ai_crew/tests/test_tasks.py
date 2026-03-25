"""
tests/test_tasks.py
Tests that all tasks are created with correct structure.
Run: python -m pytest tests/test_tasks.py -v
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from unittest.mock import patch, MagicMock
from dotenv import load_dotenv
load_dotenv()

MOCK_LLM = MagicMock()

@pytest.fixture(autouse=True)
def mock_llm():
    with patch("config.settings.get_llm", return_value=MOCK_LLM):
        yield


def test_task_factory_has_all_agents():
    from tasks.task_factory import TASK_MAP
    expected = {"content","social","leads","analytics","email",
                "ads","community","product_marketing","pr","brand_strategy"}
    assert set(TASK_MAP.keys()) == expected
    print(f"\n  TASK_MAP has all 10 agents: OK")


def test_default_briefs_for_all_agents():
    from tasks.task_factory import DEFAULT_BRIEFS, TASK_MAP
    for name in TASK_MAP:
        assert name in DEFAULT_BRIEFS, f"Missing default brief for {name}"
        assert len(DEFAULT_BRIEFS[name]) > 10
    print(f"\n  All default briefs present: OK")


@pytest.mark.parametrize("agent_name", [
    "content", "social", "leads", "analytics", "email",
    "ads", "community", "product_marketing", "pr", "brand_strategy"
])
def test_task_creation(agent_name):
    from agents.all_agents import get_all_agents
    from tasks.task_factory import get_task
    agents = get_all_agents()
    task = get_task(agent_name, agents[agent_name], "Test brief")
    assert task.description
    assert task.expected_output
    assert task.agent is not None
    print(f"\n  {agent_name}: task created, "
          f"desc={len(task.description)} chars, "
          f"output='{task.expected_output[:50]}...'")


def test_task_unknown_agent_raises():
    from agents.all_agents import get_all_agents
    from tasks.task_factory import get_task
    agents = get_all_agents()
    with pytest.raises(ValueError, match="Unknown agent"):
        get_task("nonexistent_agent", agents["content"])
    print(f"\n  Unknown agent raises ValueError: OK")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
