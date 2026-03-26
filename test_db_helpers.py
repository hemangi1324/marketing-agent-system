import os
os.environ["PYTHONPATH"] = "."  # ensure backend is importable

from backend.db.database import (
    get_trends, get_memory, get_current_attempt, save_reasoning,
    get_reasoning_since, get_latest_assets, get_campaign
)

# 1. Test get_trends
trends = get_trends(limit=5)
print("Trends:", trends)

# 2. Test get_memory (adjust festival_tag and year to match your seed)
memory = get_memory(festival_tag="pink_friday", year=2023)
print("Memory:", memory)

# 3. Test get_current_attempt (use a real campaign id)
campaign_id = 1  # change to your seeded campaign id
attempt = get_current_attempt(campaign_id)
print(f"Current attempt for campaign {campaign_id}: {attempt}")

# 4. Test save_reasoning
log_id = save_reasoning("TestAgent", "This is a test thought", campaign_id)
print(f"Saved reasoning log id: {log_id}")

# 5. Test get_reasoning_since
new_logs = get_reasoning_since(campaign_id, since_id=log_id-1)
print("New logs:", new_logs)

# 6. Test get_latest_assets (optional)
assets = get_latest_assets(campaign_id)
print("Latest assets:", assets)

# 7. Test get_campaign (optional)
campaign = get_campaign(campaign_id)
print("Campaign:", campaign)