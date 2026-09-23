import dataclasses
import datetime
import json


def to_date(d: str) -> datetime.date:
    try:
        return datetime.date.fromisoformat(d)
    except ValueError:
        return datetime.date.fromisoformat(d + "-01")


def to_datetime_utc(d: str) -> datetime:
    x = datetime.datetime.strptime(d, '%Y-%m-%d %H:%M:%S')
    epoch = datetime.datetime(1970, 1, 1)
    x1 = datetime.datetime.fromtimestamp((x - epoch).total_seconds(), datetime.timezone.utc)
    return x1


def to_datetime(d: str) -> datetime:
    x = datetime.datetime.strptime(d, '%Y-%m-%d %H:%M:%S')
    return x


def to_iso(d: datetime.date) -> str:
    return d.strftime("%Y-%m-%d")


class EnhancedJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if dataclasses.is_dataclass(o):
            return dataclasses.asdict(o)
        elif isinstance(o, (datetime.date, datetime.datetime)):
            return o.isoformat()

        return super().default(o)
