"""Shared tag-universe resolution for read-only use cases.

Membership comes from current tag assignments: repositories carry no
historical tag snapshots, so callers must report the membership vintage
as current and must NOT label the historical universe point-in-time.
"""

MEMBERSHIP_VINTAGE_NOTE = (
    "current (tags are current assignments, not historical snapshots; "
    "the historical universe is NOT point-in-time)"
)


def resolve_universe(repository, include_tags: list[str], exclude_tags: list[str]) -> list[str]:
    """Union of include-tag symbols (or all symbols) minus excluded tags."""
    if include_tags:
        universe = {
            symbol
            for tag in include_tags
            for symbol in repository.get_symbols_by_tag(tag)
        }
    else:
        universe = set(repository.get_symbols())
    for tag in exclude_tags:
        universe -= set(repository.get_symbols_by_tag(tag))
    return sorted(universe)
