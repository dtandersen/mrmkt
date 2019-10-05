import dataclasses
import datetime
import json


def to_date(d: str) -> datetime.date:
    try:
        return datetime.date.fromisoformat(d)
    except ValueError:
        return datetime.date.fromisoformat(d + "-01")


def to_iso(d: datetime.date) -> str:
    return d.strftime("%Y-%m-%d")


class EnhancedJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if dataclasses.is_dataclass(o):
            return dataclasses.asdict(o)
        elif isinstance(o, (datetime.date, datetime.datetime)):
            return o.isoformat()

        return super().default(o)
