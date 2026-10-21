from datetime import datetime
import math
from dateutil.relativedelta import relativedelta


def get_last_6_months():
    """
    Returns last 6 completed months (excluding current month)
    Example:
      Today = 2026-09-18
      → ["Mar", "Apr", "May", "Jun", "Jul", "Aug"]
    """
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
    """
    monthly_views example:
    {
      "Mar": 420000,
      "Apr": 480000,
      "May": 450000,
      "Jun": 520000,
      "Jul": 600000,
      "Aug": 680000
    }
    """

    months = get_last_6_months()

    max_views = max(
        [monthly_views.get(m, 0) for m in months] or [1]
    )

    overview = []
    for m in months:
        score = normalize(monthly_views.get(m, 0), max_views)
        overview.append({
            "month": m,
            "score": score
        })

    return overview
