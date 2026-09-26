"""Page objects for the read-only web view (Playwright)."""

import json
import re


def _cells(html):
    return re.findall(r"<td>(.*?)</td>", html)


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
