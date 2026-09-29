from __future__ import annotations

from pathlib import Path

import yaml

CONFIG_DIR_NAME = ".mrmkt"


def find_config_file(name: str, start: Path | None = None) -> Path | None:
    """Locate a config file for this checkout.

    Search ``.mrmkt/<name>`` from ``start`` (default: cwd) upward toward
    the filesystem root, git-style. If no ``.mrmkt`` copy exists anywhere
    up the tree, fall back to the legacy bare ``./<name>`` next to the
    invocation directory so old checkouts keep working.
    """
    origin = (start or Path.cwd()).resolve()
    for directory in (origin, *origin.parents):
        candidate = directory / CONFIG_DIR_NAME / name
        if candidate.is_file():
            return candidate
    legacy = (start or Path.cwd()) / name
    return legacy if legacy.is_file() else None


def read_config(start: Path | None = None) -> dict:
    found = find_config_file("config.yaml", start)
    if found is None:
        raise FileNotFoundError("config.yaml not found (.mrmkt/ or cwd)")
    try:
        text = found.read_text()
    except OSError as error:
        raise FileNotFoundError(f"config.yaml not readable at {found}") from error
    # use safe_load instead load
    return yaml.safe_load(text)
