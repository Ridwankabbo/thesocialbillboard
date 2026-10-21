def platform_score(ai_score, engagement, growth):
    return round(
        (ai_score * 0.5) +
        (engagement * 0.3) +
        (growth * 0.2),
        2
    )


def build_platform_breakdown(platforms):
    """
    platforms = [
      {
        "platform": "YouTube",
        "ai_score": 86,
        "engagement": 6.2,
        "growth": 12.8
      }
    ]
    """

    return [
        {
            "platform": p["platform"],
            "value": platform_score(
                p["ai_score"],
                p["engagement"],
                p["growth"]
            )
        }
        for p in platforms
    ]
