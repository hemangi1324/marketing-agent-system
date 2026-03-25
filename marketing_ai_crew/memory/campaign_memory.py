import sys
import os

# Fix module resolution — must be before any local imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ── TODO: swap these 2 lines when M2 finishes db/session.py ─────────────────
# from db.session import save_memory, get_memory
def get_memory(festival_tag, year): return None
def save_memory_db(campaign_id, festival_tag, mortem_dict): pass
# ─────────────────────────────────────────────────────────────────────────────

# ── Local JSON fallback path ──────────────────────────────────────────────────
# Memories are saved here until M2's DB is ready
# This also ensures memories persist between runs during the hackathon demo
MEMORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "memory_store.json")


# ── Internal helpers ──────────────────────────────────────────────────────────
def _load_store() -> dict:
    """Loads the entire memory store from disk. Returns empty dict if file doesn't exist."""
    if not os.path.exists(MEMORY_FILE):
        return {}
    try:
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def _save_store(store: dict) -> None:
    """Saves the entire memory store to disk."""
    with open(MEMORY_FILE, "w") as f:
        json.dump(store, f, indent=2)


# ── Public API ────────────────────────────────────────────────────────────────
def save_campaign_memory(campaign_id: int, festival_tag: str, mortem_dict: dict) -> None:
    """
    Saves a campaign post-mortem to memory.
    Keyed by festival_tag so the next campaign for the same festival can read it.

    Args:
        campaign_id  : int — ID of the campaign that just finished
        festival_tag : str — e.g. "diwali", "valentines", "generic"
        mortem_dict  : dict with keys what_worked, what_failed,
                       market_context, recommendation
    """

    store = _load_store()

    memory_entry = {
        "festival_tag"  : festival_tag,
        "campaign_id"   : campaign_id,
        "what_worked"   : mortem_dict.get("what_worked", ""),
        "what_failed"   : mortem_dict.get("what_failed", ""),
        "market_context": mortem_dict.get("market_context", ""),
        "recommendation": mortem_dict.get("recommendation", ""),
        "saved_at"      : datetime.now().isoformat()
    }

    # Always overwrite with latest — Strategy Agent should use most recent memory
    store[festival_tag] = memory_entry
    _save_store(store)

    # Also try saving to DB (no-op until M2 is ready)
    save_memory_db(campaign_id, festival_tag, mortem_dict)

    print(f"[CampaignMemory] Saved memory for festival: {festival_tag}")


def get_campaign_memory(festival_tag: str) -> dict | None:
    """
    Retrieves the last post-mortem for a given festival.
    Called by the Strategy Agent at the start of each campaign.

    Args:
        festival_tag : str — e.g. "diwali", "valentines", "generic"

    Returns:
        dict with memory fields, or None if no memory exists for this festival
    """

    # Try DB first (no-op returns None until M2 is ready)
    db_memory = get_memory(festival_tag, year=datetime.now().year)
    if db_memory:
        return db_memory

    # Fall back to local JSON store
    store = _load_store()
    memory = store.get(festival_tag, None)

    if memory:
        print(f"[CampaignMemory] Found memory for festival: {festival_tag}")
    else:
        print(f"[CampaignMemory] No memory found for festival: {festival_tag}")

    return memory


def get_all_memories() -> dict:
    """
    Returns all stored memories.
    Useful for the dashboard to show memory state.
    """
    return _load_store()


def clear_memory(festival_tag: str = None) -> None:
    """
    Clears memory for a specific festival, or all memories if no tag given.
    Useful for demo resets.

    Args:
        festival_tag : str or None — if None, clears everything
    """
    if festival_tag is None:
        _save_store({})
        print("[CampaignMemory] All memories cleared.")
    else:
        store = _load_store()
        if festival_tag in store:
            del store[festival_tag]
            _save_store(store)
            print(f"[CampaignMemory] Memory cleared for festival: {festival_tag}")
        else:
            print(f"[CampaignMemory] No memory found for festival: {festival_tag}")


# ── Quick test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":

    print("── Test 1: Save a Diwali post-mortem ───────────")
    save_campaign_memory(
        campaign_id=99,
        festival_tag="diwali",
        mortem_dict={
            "what_worked"   : "Urgency tone improved open rate by 2%",
            "what_failed"   : "Image was too dark, CTA button had low clicks",
            "market_context": "Diwali week, very high competition from Flipkart and Amazon",
            "recommendation": "Use brighter image with a bold orange CTA button"
        }
    )

    print("\n── Test 2: Retrieve Diwali memory ──────────────")
    memory = get_campaign_memory("diwali")
    print(json.dumps(memory, indent=2))

    print("\n── Test 3: Retrieve memory for unknown festival ─")
    memory = get_campaign_memory("holi")
    print(f"Result: {memory}")

    print("\n── Test 4: Get all memories ─────────────────────")
    all_memories = get_all_memories()
    print(json.dumps(all_memories, indent=2))

    print("\n── Test 5: Save a second festival ───────────────")
    save_campaign_memory(
        campaign_id=100,
        festival_tag="valentines",
        mortem_dict={
            "what_worked"   : "Romantic subject line doubled open rate",
            "what_failed"   : "Discount was too small to drive conversions",
            "market_context": "Valentine's week, moderate competition",
            "recommendation": "Increase discount to at least 30% for Valentine's"
        }
    )

    print("\n── Test 6: All memories after second save ────────")
    all_memories = get_all_memories()
    print(json.dumps(all_memories, indent=2))