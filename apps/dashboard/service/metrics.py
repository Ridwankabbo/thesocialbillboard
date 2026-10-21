# apps/analytics/services/metrics.py

from datetime import datetime, timedelta, timezone


# ---------------------------
# EXISTING (UNCHANGED)
# ---------------------------

def engagement_rate(likes, comments, shares, views):
    views = max(views, 1)
    return round(((likes + comments*2 + shares*3) / views) * 100, 2)


def view_rate(views, followers):
    followers = max(followers, 1)
    return round((views / followers) * 100, 2)


def comment_rate(comments, views):
    views = max(views, 1)
    return round((comments / views) * 100, 2)


def trend(current, previous):
    if previous <= 0:
        return 0.0
    return round(((current - previous) / previous) * 100, 2)


def build_engagement_metrics(current, previous):
    curr_eng = engagement_rate(**current)
    prev_eng = engagement_rate(**previous)

    curr_view = view_rate(current["views"], current["followers"])
    prev_view = view_rate(previous["views"], previous["followers"])

    curr_comment = comment_rate(current["comments"], current["views"])
    prev_comment = comment_rate(previous["comments"], previous["views"])

    return {
        "engagement_rate": {
            "value": curr_eng,
            "trend": trend(curr_eng, prev_eng)
        },
        "view_rate": {
            "value": curr_view,
            "trend": trend(curr_view, prev_view)
        },
        "comment_rate": {
            "value": curr_comment,
            "trend": trend(curr_comment, prev_comment)
        }
    }


# ---------------------------
# NEW: 30d vs PREV 30d SOURCE
# ---------------------------

def _filter_items(items, days):
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=days)
    return [
        i for i in items
        if (i.get("published_at") or i.get("created_time")) >= start
    ]


def _aggregate(items):
    return {
        "likes": sum(int(i.get("likes", 0) or 0) for i in items),
        "comments": sum(int(i.get("comments", 0) or 0) for i in items),
        "shares": sum(int(i.get("shares", 0) or 0) for i in items),
        "views": sum(int(i.get("views", 0) or 0) for i in items),
    }


def get_30d_metrics(platforms_data: list, followers: int):
    """
    Returns: current_30d, previous_30d
    """
    current_items = []
    previous_items = []

    for p in platforms_data:
        items = p.get("monthly_items", [])
        current_items += _filter_items(items, 30)
        previous_items += _filter_items(items, 60)

    current = _aggregate(current_items)
    previous = _aggregate(previous_items)

    current["followers"] = followers
    previous["followers"] = followers

    return current, previous
