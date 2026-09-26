"""Contract test: the checked-in OpenAPI spec matches the live schema.

The generated client derives from api/openapi.json; pinning the two
together means a forgotten regen fails here instead of drifting
silently. Run from the package root (same convention as alpaca.yaml).
"""

import json
from pathlib import Path

from hamcrest import assert_that, equal_to
from litestar.serialization.msgspec_hooks import encode_json

from mrmkt.common.inmemfinrepo import InMemoryFinancialRepository
from mrmkt.composition import cli_dependencies_for_testing
from mrmkt.web.app import create_web_app


def test_checked_in_spec_matches_live_schema():
    deps = cli_dependencies_for_testing(repository=InMemoryFinancialRepository())
    app = create_web_app(lambda: deps)
    live = json.loads(encode_json(app.openapi_schema.to_schema(), None))
    checked = json.loads(Path("api/openapi.json").read_text())
    assert_that(checked, equal_to(live))
