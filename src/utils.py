from datetime import datetime, timezone, timedelta

WIB = timezone(timedelta(hours=7))

def now_wib() -> datetime:
    """Return current datetime in WIB (UTC+7)"""
    return datetime.now(WIB)

def to_wib(dt: datetime) -> datetime:
    """Convert any datetime to WIB (UTC+7). Naive datetimes assumed UTC."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(WIB)
