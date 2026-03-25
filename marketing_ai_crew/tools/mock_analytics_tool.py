"""
tools/mock_analytics_tool.py
Simulates GA4 / Mixpanel with realistic mock data.
"""
import json, random
from datetime import datetime
from crewai.tools import BaseTool


class AnalyticsPullMetricsTool(BaseTool):
    name: str = "Analytics Metrics Puller"
    description: str = "Pull website performance metrics. Input: date range like 'last_7_days' or 'last_30_days'."

    def _run(self, date_range: str = "last_7_days") -> str:
        random.seed(42)
        metrics = {
            "date_range": date_range,
            "sessions": random.randint(3200, 5800),
            "users": random.randint(2800, 4900),
            "new_users_pct": f"{random.randint(55, 72)}%",
            "bounce_rate": f"{random.randint(38, 58)}%",
            "avg_session_duration": f"{random.randint(2,4)}m {random.randint(10,59)}s",
            "top_pages": [
                {"page": "/pricing",  "views": 2100, "conversions": 98},
                {"page": "/features", "views": 1450, "conversions": 42},
                {"page": "/blog/automate-small-business", "views": 980, "conversions": 28},
            ],
            "conversions": {
                "free_trial_signups": random.randint(80, 180),
                "demo_requests": random.randint(25, 65),
                "paid_upgrades": random.randint(12, 35),
                "conversion_rate": f"{round(random.uniform(2.1, 4.8), 1)}%",
            },
            "traffic_sources": {
                "organic_search": "42%", "paid_ads": "25%",
                "social": "16%", "email": "11%", "direct": "6%",
            },
            "email": {
                "campaigns_sent": 3,
                "avg_open_rate": f"{random.randint(24, 38)}%",
                "avg_click_rate": f"{random.randint(4, 9)}%",
            },
        }
        return json.dumps(metrics, indent=2)


class AnalyticsTrendsTool(BaseTool):
    name: str = "Trend Analyzer"
    description: str = "Compare current vs previous period for a metric. Input: metric name like 'sessions'."

    def _run(self, metric_name: str = "sessions") -> str:
        random.seed(hash(metric_name) % 100)
        current  = random.randint(3000, 6000)
        previous = random.randint(2500, 5500)
        change   = round(((current - previous) / previous) * 100, 1)
        trend    = "UP" if change > 0 else "DOWN"
        insight  = (
            "Strong growth. Consider increasing ad spend." if change > 10
            else "Stable. Monitor next 7 days." if abs(change) < 5
            else "Notable decline. Investigate traffic sources."
        )
        return (
            f"Trend: {metric_name} is {trend} {abs(change)}% vs previous period.\n"
            f"Current: {current:,} | Previous: {previous:,}\n"
            f"Insight: {insight}"
        )
