"""
tests/test_orchestrator.py
Tests for SharedState and UniversalOrchestrator (no LLM calls — fully mocked).
Run: python -m pytest tests/test_orchestrator.py -v
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import tempfile
import shutil
from unittest.mock import patch, MagicMock


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def temp_db_dir(tmp_path, monkeypatch):
    """Redirect DB writes to a temp directory so tests don't pollute outputs/db/."""
    import database.db_manager as db_manager
    monkeypatch.setattr(db_manager, "_BASE_DIR", str(tmp_path / "db"))


# ── SharedState tests ─────────────────────────────────────────────────────────

class TestSharedState:

    def setup_method(self):
        """Reset DB between tests."""
        pass

    def test_init(self):
        with patch("database.campaign_store.build_historical_context", return_value="No history"):
            from orchestrator.state import SharedState
            state = SharedState(campaign_id=1, brief="Test brief")
            assert state.campaign_id == 1
            assert state.brief == "Test brief"
            assert state.green_light is None

    def test_update_strategy(self):
        with patch("database.campaign_store.build_historical_context", return_value=""):
            with patch("database.campaign_store.save_campaign"):
                with patch("database.campaign_store.log_agent_step"):
                    from orchestrator.state import SharedState
                    state = SharedState(campaign_id=2, brief="Brief")
                    state.update_strategy({"campaign_theme": "Summer Sale", "tone": "fun"})
                    assert state.to_dict()["strategy_output"]["campaign_theme"] == "Summer Sale"

    def test_update_risk_green(self):
        with patch("database.campaign_store.build_historical_context", return_value=""):
            with patch("database.campaign_store.save_campaign"):
                with patch("database.campaign_store.log_agent_step"):
                    from orchestrator.state import SharedState
                    state = SharedState(campaign_id=3, brief="Brief")
                    state.update_risk({"green_light": True, "brand_safety": 9, "legal_risk": 8, "cultural_sensitivity": 9})
                    assert state.green_light is True
                    assert state.is_blocked() is False

    def test_update_risk_blocked(self):
        with patch("database.campaign_store.build_historical_context", return_value=""):
            with patch("database.campaign_store.save_campaign"):
                with patch("database.campaign_store.log_agent_step"):
                    from orchestrator.state import SharedState
                    state = SharedState(campaign_id=4, brief="Brief")
                    state.update_risk({"green_light": False, "flag_reason": "Too aggressive"})
                    assert state.green_light is False
                    assert state.is_blocked() is True

    def test_delegation_control(self):
        with patch("database.campaign_store.build_historical_context", return_value=""):
            with patch("database.campaign_store.save_campaign"):
                with patch("database.campaign_store.log_agent_step"):
                    from orchestrator.state import SharedState
                    state = SharedState(campaign_id=5, brief="Brief")
                    assert state.can_delegate() is True
                    state.increment_delegation()
                    state.increment_delegation()
                    state.increment_delegation()
                    assert state.can_delegate() is False

    def test_context_string(self):
        with patch("database.campaign_store.build_historical_context", return_value=""):
            with patch("database.campaign_store.save_campaign"):
                with patch("database.campaign_store.log_agent_step"):
                    from orchestrator.state import SharedState
                    state = SharedState(campaign_id=6, brief="Diwali camp", festival_tag="diwali")
                    ctx = state.to_context_string()
                    assert "6" in ctx
                    assert "Diwali camp" in ctx
                    assert "diwali" in ctx


# ── DB Manager tests ──────────────────────────────────────────────────────────

class TestDbManager:

    def test_write_and_read(self):
        import database.db_manager as db
        db.write("test_col", "key1", {"name": "Alice", "score": 9})
        record = db.read("test_col", "key1")
        assert record is not None
        assert record["name"] == "Alice"
        assert record["score"] == 9

    def test_read_missing(self):
        import database.db_manager as db
        result = db.read("test_col", "nonexistent_key_xyz")
        assert result is None

    def test_query_with_filter(self):
        import database.db_manager as db
        db.write("campaigns_test", "c1", {"status": "done", "val": 1})
        db.write("campaigns_test", "c2", {"status": "pending", "val": 2})
        db.write("campaigns_test", "c3", {"status": "done", "val": 3})
        results = db.query("campaigns_test", filters={"status": "done"})
        assert len(results) == 2

    def test_exists(self):
        import database.db_manager as db
        db.write("exists_test", "mykey", {"x": 1})
        assert db.exists("exists_test", "mykey") is True
        assert db.exists("exists_test", "nothere") is False

    def test_get_recent(self):
        import database.db_manager as db
        for i in range(7):
            db.write("recent_test", str(i), {"i": i})
        recent = db.get_recent("recent_test", n=3)
        assert len(recent) == 3

    def test_delete(self):
        import database.db_manager as db
        db.write("del_test", "todelete", {"data": "value"})
        assert db.exists("del_test", "todelete") is True
        deleted = db.delete("del_test", "todelete")
        assert deleted is True
        assert db.exists("del_test", "todelete") is False


# ── Campaign Store tests ──────────────────────────────────────────────────────

class TestCampaignStore:

    def test_save_and_load(self):
        from database import campaign_store
        state = {"campaign_id": 99, "brief": "Test", "green_light": True}
        campaign_store.save_campaign(99, state)
        loaded = campaign_store.load_campaign(99)
        assert loaded is not None
        assert loaded["brief"] == "Test"

    def test_campaign_exists(self):
        from database import campaign_store
        campaign_store.save_campaign(100, {"campaign_id": 100, "brief": "Exists"})
        assert campaign_store.campaign_exists(100) is True
        assert campaign_store.campaign_exists(99999) is False

    def test_save_risk_result(self):
        from database import campaign_store
        campaign_store.save_risk_result(50, {"brand_safety": 8, "green_light": True})
        result = campaign_store.load_risk_result(50)
        assert result["brand_safety"] == 8

    def test_save_analytics_result(self):
        from database import campaign_store
        campaign_store.save_analytics_result(60, {"healed": True, "new_ctr": 1.5})
        result = campaign_store.load_analytics_result(60)
        assert result["healed"] is True

    def test_build_historical_context_empty(self):
        from database import campaign_store
        ctx = campaign_store.build_historical_context(festival_tag="christmas")
        assert isinstance(ctx, str)
        assert len(ctx) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
