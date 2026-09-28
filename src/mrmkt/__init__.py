from mrmkt import ext as ext

__all__ = ["ext", "connect", "MrMkt"]


def __getattr__(name: str):
    """Lazily expose the scripting facade, keeping ``import mrmkt`` light."""
    if name in ("connect", "MrMkt"):
        from mrmkt import scripting

        return getattr(scripting, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
