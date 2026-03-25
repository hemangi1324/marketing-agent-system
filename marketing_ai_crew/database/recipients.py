"""
database/recipients.py
-----------------------
Manages email recipient lists for marketing campaigns.

TODAY (no database):
    Returns a hardcoded list. Edit HARDCODED_RECIPIENTS below to add your real addresses.

FUTURE (with database):
    Swap get_recipients() to call get_recipients_from_db() instead.
    See the TODO block below — it handles SQLite, PostgreSQL, and MySQL.
"""

import re
import logging
from typing import List, Dict, Optional

logger = logging.getLogger("recipients")

# ══════════════════════════════════════════════════════════════════════════════
#  ✏️  EDIT THIS LIST to add your real recipient email addresses
#      Format: {"name": "Display Name", "email": "address@example.com"}
# ══════════════════════════════════════════════════════════════════════════════
HARDCODED_RECIPIENTS: List[Dict[str, str]] = [
    {"name": "Suhani Satav",   "email": "suhanisatav81@gmail.com"},
    {"name": "Shravani Sawant",   "email": "sawantshravani2836@gmail.com"},
    # Add as many recipients as needed:
    # {"name": "John Doe",       "email": "john.doe@example.com"},
    # {"name": "Jane Smith",     "email": "jane.smith@example.com"},
]

# ── Email format validator ─────────────────────────────────────────────────────
_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")


def validate_email(address: str) -> bool:
    """Return True if address looks like a valid email format."""
    return bool(_EMAIL_RE.match(address.strip()))


def _filter_valid(recipients: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Remove any recipients with invalid or missing email addresses."""
    valid = []
    for r in recipients:
        email = r.get("email", "").strip()
        if validate_email(email):
            valid.append({"name": r.get("name", ""), "email": email})
        else:
            logger.warning("Skipping invalid recipient email: '%s'", email)
    return valid


# ══════════════════════════════════════════════════════════════════════════════
#  DATABASE INTEGRATION HOOK
#
#  When you add a database, replace the body of get_recipients() with a call
#  to one of these functions. The pipeline code never needs to change.
#
#  ── SQLite (built-in, no extra install) ──────────────────────────────────────
#     import sqlite3
#     def get_recipients_from_db(campaign_type=None):
#         conn = sqlite3.connect("marketing.db")
#         cur  = conn.cursor()
#         if campaign_type:
#             cur.execute(
#                 "SELECT name, email FROM subscribers WHERE campaign_type=? AND active=1",
#                 (campaign_type,)
#             )
#         else:
#             cur.execute("SELECT name, email FROM subscribers WHERE active=1")
#         rows = cur.fetchall()
#         conn.close()
#         return [{"name": row[0], "email": row[1]} for row in rows]
#
#  ── PostgreSQL (pip install psycopg2-binary) ──────────────────────────────────
#     import psycopg2, os
#     def get_recipients_from_db(campaign_type=None):
#         conn = psycopg2.connect(os.getenv("DATABASE_URL"))
#         cur  = conn.cursor()
#         query = "SELECT name, email FROM subscribers WHERE active = TRUE"
#         params = ()
#         if campaign_type:
#             query += " AND campaign_type = %s"
#             params = (campaign_type,)
#         cur.execute(query, params)
#         rows = cur.fetchall()
#         conn.close()
#         return [{"name": r[0], "email": r[1]} for r in rows]
#
#  ── MySQL (pip install mysql-connector-python) ────────────────────────────────
#     import mysql.connector, os
#     def get_recipients_from_db(campaign_type=None):
#         conn = mysql.connector.connect(
#             host=os.getenv("DB_HOST"), user=os.getenv("DB_USER"),
#             password=os.getenv("DB_PASS"), database=os.getenv("DB_NAME")
#         )
#         cur = conn.cursor()
#         if campaign_type:
#             cur.execute(
#                 "SELECT name, email FROM subscribers WHERE campaign_type=%s AND active=1",
#                 (campaign_type,)
#             )
#         else:
#             cur.execute("SELECT name, email FROM subscribers WHERE active=1")
#         rows = cur.fetchall()
#         conn.close()
#         return [{"name": r[0], "email": r[1]} for r in rows]
# ══════════════════════════════════════════════════════════════════════════════


def get_recipients(campaign_type: Optional[str] = None) -> List[Dict[str, str]]:
    """
    Return a list of recipient dicts: [{"name": ..., "email": ...}, ...]

    Args:
        campaign_type: optional filter (ignored in hardcoded mode; used by DB queries).

    Returns:
        Validated list of recipients with valid email addresses.

    TO SWITCH TO DATABASE:
        Replace the body of this function with:
            return _filter_valid(get_recipients_from_db(campaign_type))
    """
    # ── Hardcoded mode (current) ──────────────────────────────────────────────
    recipients = _filter_valid(HARDCODED_RECIPIENTS)
    if not recipients:
        logger.warning(
            "Recipient list is empty. "
            "Edit HARDCODED_RECIPIENTS in database/recipients.py to add real addresses."
        )
    else:
        logger.info("Loaded %d recipients (hardcoded mode).", len(recipients))
    return recipients


# ── Manual test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Recipients loaded:")
    for r in get_recipients():
        status = "✅" if validate_email(r["email"]) else "❌"
        print(f"  {status}  {r['name']:30s} <{r['email']}>")

    print("\nEmail validation tests:")
    tests = ["good@example.com", "bad-address", "also@bad", "valid.name+tag@domain.co.in"]
    for t in tests:
        print(f"  {'✅' if validate_email(t) else '❌'}  {t}")
