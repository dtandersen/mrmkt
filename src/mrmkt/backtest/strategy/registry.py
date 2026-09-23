"""Strategy registry with k=v parsing and typed construction."""

from typing import TypeVar

from mrmkt.backtest.strategy.base import Strategy

T = TypeVar("T", bound=Strategy)

STRATEGIES: dict[str, type[Strategy]] = {}


def register(name: str):
    """Name a Strategy subclass so build_strategy() can find it.

    Applied as ``@register("name")`` where the strategy is defined;
    importing the module performs the registration.
    """
    key = name.strip().lower()
    if not key:
        raise ValueError("strategy name must not be blank")

    def decorator(cls: type[T]) -> type[T]:
        if key in STRATEGIES:
            raise ValueError(f"strategy {key!r} is already registered")
        STRATEGIES[key] = cls
        return cls

    return decorator


def parse_params(text: str | None) -> dict[str, str]:
    """Parse ``k=v,k2=v2`` into raw strings; blank means defaults."""
    if not text or not text.strip():
        return {}
    parsed = {}
    for chunk in text.split(","):
        if "=" not in chunk:
            raise ValueError(f"params must look like k=v,k2=v2, got {chunk.strip()!r}")
        key, _, value = chunk.partition("=")
        key, value = key.strip(), value.strip()
        if not key or not value:
            raise ValueError(f"params must look like k=v,k2=v2, got {chunk.strip()!r}")
        parsed[key] = value
    return parsed


def build_strategy(name: str, raw: dict[str, str]) -> Strategy:
    """Build a registered strategy, coercing raw ``k=v`` strings."""
    key = name.strip().lower()
    if key not in STRATEGIES:
        raise ValueError(f"unknown strategy {name!r} (choose from {sorted(STRATEGIES)})")
    cls = STRATEGIES[key]
    specs = cls.param_specs()
    unknown = sorted(k for k in raw if k not in specs)
    if unknown:
        raise ValueError(f"unknown params {unknown} for {name} (choose from {sorted(specs)})")
    return cls.construct({k: _coerce(specs[k].type, v, k) for k, v in raw.items()})


def _coerce(pytype: type, text: str, name: str):
    stripped = text.strip()
    if pytype is bool:
        if stripped.lower() in ("1", "true", "yes", "y", "on"):
            return True
        if stripped.lower() in ("0", "false", "no", "n", "off"):
            return False
        raise ValueError(f"param {name} must be true/false, got {text!r}")
    try:
        return pytype(stripped)
    except ValueError:
        raise ValueError(f"param {name} must be {pytype.__name__}, got {text!r}") from None
