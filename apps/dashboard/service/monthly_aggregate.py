# apps/analytics/services/monthly.py

from datetime import datetime
from collections import defaultdict
from dateutil.relativedelta import relativedelta


# ---------------------------
# EXISTING (UNCHANGED)
# ---------------------------

def get_last_6_months():
    today = datetime.utcnow().replace(day=1)
    months = []
    for i in range(6, 0, -1):
        m = today - relativedelta(months=i)
        months.append(m.strftime("%b"))
    return months


def normalize(value, max_value):
    if max_value <= 0:
        return 0
    return round((value / max_value) * 100, 2)


def build_performance_overview(monthly_views: dict):
    months = get_last_6_months()
    max_views = max([monthly_views.get(m, 0) for m in months] or [1])

    overview = []
    for m in months:
        overview.append({
            "month": m,
            "score": normalize(monthly_views.get(m, 0), max_views)
        })
    return overview


# ---------------------------
# NEW: MONTHLY AGGREGATION
# ---------------------------

def _month_key(dt: datetime):
    return dt.strftime("%b")


def get_monthly_views_for_user(platforms_data: list):
    """
    platforms_data = output of analyze_platform()
    Uses monthly_items inside platform dict
    """
    combined = defaultdict(int)

    for p in platforms_data:
        items = p.get("monthly_items", [])
        for it in items:
            dt = it.get("published_at") or it.get("created_time")
            if not dt:
                continue
            combined[_month_key(dt)] += int(it.get("views", 0) or 0)

    return dict(combined)
