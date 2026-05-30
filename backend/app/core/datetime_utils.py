from datetime import UTC, datetime


def ensure_utc(dt: datetime | None) -> datetime | None:
    """Return dt with UTC tzinfo. Converts naive datetimes; passes through None."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt
