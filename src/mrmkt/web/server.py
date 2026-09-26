"""Import-string entrypoint for serving the web view.

Uvicorn's reloader (and multi-worker mode) requires the application as an
import string so child processes can re-import it on every change. This
module therefore builds its own :class:`~mrmkt.composition.AppContext`;
a reloaded child cannot inherit the CLI's in-memory dependencies. The
non-reload path in ``mrmkt.cli.main`` keeps using the CLI-owned context.
"""

from mrmkt.composition import create_app_context
from mrmkt.web.app import create_web_app

_env = create_app_context()
app = create_web_app(lambda: _env)
app.on_shutdown.append(_env.close)
