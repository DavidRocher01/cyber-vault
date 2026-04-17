def compute_assessment_score(items: dict[str, str], all_item_ids: set[str]) -> int:
    """Compute a 0-100 compliance score.

    Scoring: compliant=2pts, partial=1pt, non_compliant=0, 'na' excluded from denominator.
    Items absent from `items` default to non_compliant.
    """
    statuses = [items.get(item_id, "non_compliant") for item_id in all_item_ids]
    scorable = [s for s in statuses if s != "na"]
    if not scorable:
        return 0
    total = sum(2 if s == "compliant" else 1 if s == "partial" else 0 for s in scorable)
    max_pts = len(scorable) * 2
    return round(total / max_pts * 100) if max_pts else 0
