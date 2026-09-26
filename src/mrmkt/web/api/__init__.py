"""JSON API controllers (DTOs in, DTOs out, never entities)."""

from litestar import Controller

from mrmkt.web.api.triggers import ApiTriggersController

__all__ = ["API_CONTROLLERS", "ApiTriggersController"]

API_CONTROLLERS: list[type[Controller]] = [ApiTriggersController]
"""Every JSON API controller; the app and codegen consume this list."""
