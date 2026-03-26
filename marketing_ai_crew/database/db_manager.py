"""
database/db_manager.py
-----------------------
Lightweight JSON-file-backed database manager.

Stores all campaign data, logs, metrics and decisions in structured
JSON files under outputs/db/. Each "collection" is one JSON file.

Design principles:
  - No external database dependency (SQLite/Postgres swap-ready via subclass)
  - Thread-safe (file lock per write operation)
  - Single source of truth: every agent reads/writes here
  - All outputs are reusable for future campaign runs

Collections:
  campaigns      — full CampaignState records
  agent_steps    — per-step audit logs
  risk_scores    — risk results per campaign
  analytics      — analytics outputs per campaign
  email_campaigns— email send records (extends existing email_send_log)
  slack_log      — sent Slack alerts (idempotency)
  telegram_log   — sent Telegram messages (idempotency)
"""

import os
import json
import logging
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger("db_manager")

# ── Storage directory ──────────────────────────────────────────────────────────
_BASE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "outputs", "db"
)

# One lock per collection to minimise contention
_locks: Dict[str, threading.Lock] = {}


def _get_lock(collection: str) -> threading.Lock:
    if collection not in _locks:
        _locks[collection] = threading.Lock()
    return _locks[collection]


def _collection_path(collection: str) -> str:
    os.makedirs(_BASE_DIR, exist_ok=True)
    return os.path.join(_BASE_DIR, f"{collection}.json")


def _load(collection: str) -> Dict[str, Any]:
    path = _collection_path(collection)
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        logger.warning("Could not read collection '%s', returning empty.", collection)
        return {}


def _save(collection: str, data: Dict[str, Any]) -> None:
    path = _collection_path(collection)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
    except OSError as exc:
        logger.error("Failed to write collection '%s': %s", collection, exc)


# ── Public API ─────────────────────────────────────────────────────────────────

def write(collection: str, record_id: str, data: Dict[str, Any]) -> None:
    """
    Write / overwrite a record in a collection.

    Args:
        collection : collection name (maps to a JSON file)
        record_id  : unique string key for this record
        data       : dict to store (will be JSON-serialized)
    """
    data["_updated_at"] = datetime.now().isoformat()
    with _get_lock(collection):
        store = _load(collection)
        store[str(record_id)] = data
        _save(collection, store)
    logger.debug("DB write — %s[%s]", collection, record_id)


def read(collection: str, record_id: str) -> Optional[Dict[str, Any]]:
    """
    Read a single record from a collection.

    Returns:
        dict if found, None otherwise
    """
    with _get_lock(collection):
        store = _load(collection)
    return store.get(str(record_id))


def query(collection: str, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """
    Return all records in a collection, optionally filtered.

    Args:
        filters : {field: value} all conditions must match (AND logic)

    Returns:
        list of matching record dicts
    """
    with _get_lock(collection):
        store = _load(collection)

    records = list(store.values())
    if not filters:
        return records

    result = []
    for record in records:
        if all(record.get(k) == v for k, v in filters.items()):
            result.append(record)
    return result


def append_log(collection: str, entry: Dict[str, Any]) -> None:
    """
    Append an entry to a log collection (records stored as a list, not a dict).
    Used for audit trails and send-logs where order matters.
    """
    entry["_logged_at"] = datetime.now().isoformat()
    log_path = os.path.join(_BASE_DIR, f"{collection}.jsonl")
    os.makedirs(_BASE_DIR, exist_ok=True)
    with _get_lock(collection):
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, default=str) + "\n")
        except OSError as exc:
            logger.error("Failed to append to log '%s': %s", collection, exc)


def exists(collection: str, record_id: str) -> bool:
    """Return True if a record with this ID exists in the collection."""
    return read(collection, record_id) is not None


def get_recent(collection: str, n: int = 5) -> List[Dict[str, Any]]:
    """
    Return the n most recently updated records in a collection.
    """
    records = query(collection)
    records.sort(key=lambda r: r.get("_updated_at", ""), reverse=True)
    return records[:n]


def delete(collection: str, record_id: str) -> bool:
    """Delete a record. Returns True if deleted, False if not found."""
    with _get_lock(collection):
        store = _load(collection)
        if str(record_id) in store:
            del store[str(record_id)]
            _save(collection, store)
            return True
    return False
