"""Shared helpers for stored trigger-set commands."""


def _default_set_name() -> str:
    import secrets

    return f"triggerset-{secrets.randbelow(900000) + 100000}"
