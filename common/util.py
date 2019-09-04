import datetime


def to_date(d: str) -> datetime.date:
    try:
        return datetime.date.fromisoformat(d)
    except ValueError:
        return datetime.date.fromisoformat(d + "-01")
