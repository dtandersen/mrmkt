"""Page objects for the read-only web view (Playwright)."""

import http.client
import json
import re
from urllib.parse import urlsplit


def _cells(html):
    return re.findall(r"<td>(.*?)</td>", html)


def _events_complete(lines, want=2):
    """True once raw lines hold ``want`` full SSE events."""
    count = 0
    seen_data = False
    for line in lines:
        text = line.strip()
        if text.startswith(b"data:"):
            seen_data = True
        elif not text and seen_data:
            count += 1
            seen_data = False
            if count >= want:
                return True
    return False


class SymbolsPage:
    """The ``/fragments/symbols`` table fragment."""

    def __init__(self, page, base_url):
        self._page = page
        self._base_url = base_url
        self._status = None

    def open(self, query=""):
        response = self._page.goto(f"{self._base_url}/fragments/symbols{query}")
        self._status = response.status if response is not None else None

    def status(self):
        return self._status

    def rows(self):
        cells = _cells(self._page.content())
        return [
            (cells[index], cells[index + 1], cells[index + 2])
            for index in range(0, len(cells), 3)
        ]

    def empty_text(self):
        return self._page.text_content("body")


class PricesPage:
    """The ``/fragments/prices`` table fragment."""

    def __init__(self, page, base_url):
        self._page = page
        self._base_url = base_url
        self._status = None

    def open(self, query=""):
        response = self._page.goto(f"{self._base_url}/fragments/prices{query}")
        self._status = response.status if response is not None else None

    def status(self):
        return self._status

    def rows(self):
        cells = _cells(self._page.content())
        return [
            (cells[index], cells[index + 1], cells[index + 5])
            for index in range(0, len(cells), 7)
        ]

    def empty_text(self):
        return self._page.text_content("body")


class TriggersPage:
    """The ``/fragments/triggers`` table fragment."""

    def __init__(self, page, base_url):
        self._page = page
        self._base_url = base_url
        self._status = None

    def open(self, query=""):
        response = self._page.goto(f"{self._base_url}/fragments/triggers{query}")
        self._status = response.status if response is not None else None

    def status(self):
        return self._status

    def names(self):
        return _cells(self._page.content())[0::5]

    def empty_text(self):
        return self._page.text_content("body")


class ChartDataPage:
    """The ``/fragments/prices/chart`` JSON series."""

    def __init__(self, page, base_url):
        self._page = page
        self._base_url = base_url
        self._status = None

    def open(self, query=""):
        response = self._page.goto(f"{self._base_url}/fragments/prices/chart{query}")
        self._status = response.status if response is not None else None

    def status(self):
        return self._status

    def bars(self):
        return json.loads(self._page.text_content("body"))


class SymbolLookupPage:
    """The ``/fragments/symbols/lookup`` JSON list."""

    def __init__(self, page, base_url):
        self._page = page
        self._base_url = base_url
        self._status = None

    def open(self, query=""):
        response = self._page.goto(f"{self._base_url}/fragments/symbols/lookup{query}")
        self._status = response.status if response is not None else None

    def status(self):
        return self._status

    def tickers(self):
        return json.loads(self._page.text_content("body"))


class IndexPage:
    """The ``/`` shell page with HTMX-loaded sections."""

    def __init__(self, page, base_url):
        self._page = page
        self._base_url = base_url
        self._status = None

    def open(self):
        response = self._page.goto(f"{self._base_url}/")
        self._status = response.status if response is not None else None

    def status(self):
        return self._status

    def section_fragment(self, name):
        return self._page.get_attribute(f"#{name}", "hx-get")

    def has_chart(self):
        return self._page.query_selector("#spx-chart") is not None

    def chart_symbol_default(self):
        return self._page.get_attribute("#chart-symbol", "value")


class LivePricesPage:
    """The ``/fragments/prices/live`` event stream over raw HTTP.

    The stream never settles, so Playwright navigation cannot be used;
    instead the first bytes are read with a short timeout and the
    connection is closed.
    """

    def __init__(self, base_url):
        self._base_url = base_url
        self._status = None
        self._content_type = None
        self._events_text = ""

    def open(self, query=""):
        parts = urlsplit(self._base_url)
        assert parts.hostname is not None and parts.port is not None
        connection = http.client.HTTPConnection(parts.hostname, parts.port, timeout=3)
        try:
            connection.request("GET", f"/fragments/prices/live{query}")
            response = connection.getresponse()
            self._status = response.status
            self._content_type = response.getheader("Content-Type")
            self._events_text = self._read_available(response)
        finally:
            connection.close()

    @staticmethod
    def _read_available(response):
        chunks = []
        try:
            while not _events_complete(chunks):
                line = response.fp.readline(65537)
                if not line:
                    break
                chunks.append(line)
        except TimeoutError:
            pass  # noqa: S110 -- stream stays open; we only need the first events
        return b"".join(chunks).decode("utf-8", errors="replace")

    def status(self):
        return self._status

    def content_type(self):
        return self._content_type

    def events_text(self):
        return self._events_text
