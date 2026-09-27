"""Tiingo websocket source for best-bid/ask quote updates."""

import json
import os
from collections.abc import Callable
from datetime import datetime

import websocket

from mrmkt.command.base import Log
from mrmkt.common.clock import ET
from mrmkt.ext.tiingo_prices import TIINGO_API_KEY_ENV_VAR
from mrmkt.gateway import PriceSource, Quote

THRESHOLD_LEVEL = 5
BASE_URL = "wss://api.tiingo.com"
EQUITY_ENDPOINT = "equity/intraday"
EQUITY_THRESHOLD_LEVEL = 4


def subscribe_message(api_key: str, threshold_level: int = THRESHOLD_LEVEL) -> dict:
    """Subscribe payload; threshold filters how much of the firehose arrives."""
    return {
        "eventName": "subscribe",
        "authorization": api_key,
        "eventData": {"thresholdLevel": threshold_level},
    }


class TiingoStreamSource(PriceSource):
    """Tiingo websocket -> normalized quotes.

    Shared parsing base for the two named streams below. The endpoints
    have no per-symbol subscription: they stream the whole firehose, so
    this adapter filters frames to the requested symbols locally. IEX
    top-of-book elements are dicts carrying ``bidPrice`` / ``askPrice``
    (with ``mid``, ``tngoLast`` and ``last`` fallbacks); consolidated
    equity elements are positional arrays
    ``[date, ticker, spread, bidSize, bidPrice, refPrice, askPrice, askSize]``
    (threshold 4). Reference-price-only arrays (threshold 6) carry no
    bid/ask and are skipped. Elements with no usable price are skipped.
    """

    #: Stream this class (or subclass) connects to unless overridden.
    default_endpoint: str = "iex"
    #: Threshold filter for this stream unless overridden.
    default_threshold_level: int = THRESHOLD_LEVEL

    def __init__(
        self,
        api_key: str | None,
        clock_now,
        *,
        connect=None,
        log: Log,
        endpoint: str | None = None,
        threshold_level: int | None = None,
    ):
        if not api_key:
            raise ValueError(
                f"{TIINGO_API_KEY_ENV_VAR} environment variable is not set"
            )
        self.api_key = api_key
        self.clock_now = clock_now
        self._connect = connect or self._default_connect
        self._ws_app = None
        self.log = log
        self.endpoint = endpoint if endpoint is not None else self.default_endpoint
        self.threshold_level = (
            threshold_level
            if threshold_level is not None
            else self.default_threshold_level
        )

    @classmethod
    def from_env(
        cls,
        clock_now,
        *,
        connect=None,
        log: Log,
        endpoint: str | None = None,
        threshold_level: int | None = None,
    ) -> "TiingoStreamSource":
        """Build from the ``TIINGO_API_KEY`` environment variable."""
        return cls(
            os.environ.get(TIINGO_API_KEY_ENV_VAR),
            clock_now,
            connect=connect,
            log=log,
            endpoint=endpoint if endpoint is not None else cls.default_endpoint,
            threshold_level=(
                threshold_level
                if threshold_level is not None
                else cls.default_threshold_level
            ),
        )

    def _default_connect(self, handler) -> None:
        payload = subscribe_message(self.api_key, self.threshold_level)
        app = websocket.WebSocketApp(
            f"{BASE_URL}/{self.endpoint}",
            on_open=lambda ws: ws.send(json.dumps(payload)),
            on_message=lambda ws, raw: handler(raw),
        )
        self._ws_app = app
        app.run_forever()

    def close(self) -> None:
        """Release a retained stream so subscribe can return."""
        app, self._ws_app = self._ws_app, None
        if app is not None:
            app.close()

    def subscribe(
        self, symbols: list[str], feed: str, *, on_quote: Callable[[Quote], None]
    ) -> None:
        """Subscribe and block on the stream (returns on disconnect).

        ``feed`` is accepted for interface compatibility and ignored:
        Tiingo exposes a single equity stream.
        """
        wanted = set(symbols)

        stream = self.endpoint.rsplit("/", 1)[-1]
        self.log(f"Connecting to {BASE_URL}/{self.endpoint}")
        self.log(f"Subscribing to {stream} {', '.join(symbols)}")

        def handle_raw(raw: str) -> None:
            self._handle_message(raw, wanted, on_quote)

        self._connect(handle_raw)

    def _handle_message(self, raw: str, symbols: set[str], on_quote) -> None:
        import sys

        self.log(f"tiingo raw: {raw}")
        try:
            message = json.loads(raw)
            if not isinstance(message, dict):
                return
            if message.get("messageType") != "A":
                # Heartbeats and informational frames carry no quotes.
                return
            data = message.get("data")
            if not isinstance(data, list):
                # Subscription acks carry an id, not quote elements.
                return
            for element in data:
                if not isinstance(element, (dict, list, tuple)):
                    continue
                if _element_ticker(element) not in symbols:
                    continue
                quote = self._to_quote(element)
                if quote is not None:
                    on_quote(quote)
        except Exception as error:
            # Never let a bad message kill the stream; report and continue.
            print(f"tiingo message skipped: {error}", file=sys.stderr, flush=True)

    def _to_quote(self, element: dict | list | tuple) -> Quote | None:
        """Map one quote element; None when unusable."""
        if isinstance(element, (list, tuple)):
            return self._to_equity_quote(element)
        return self._to_top_of_book_quote(element)

    def _to_equity_quote(self, element: list | tuple) -> Quote | None:
        """Map one consolidated-equity array.

        ``[date, ticker, spread, bidSize, bidPrice, refPrice, askPrice,
        askSize]`` (threshold 4). Shorter reference-price-only arrays
        (threshold 6) carry no bid/ask and are skipped.
        """
        if len(element) < 7:
            return None
        symbol = element[1]
        if not isinstance(symbol, str):
            return None
        bid = _to_float(element[4] if element[4] is not None else element[5])
        ask = _to_float(element[6] if element[6] is not None else element[5])
        if bid is None or ask is None:
            return None
        return Quote(
            symbol=symbol, bid=bid, ask=ask, timestamp=self._to_stamp(element[0])
        )

    def _to_top_of_book_quote(self, element: dict) -> Quote | None:
        """Map one top-of-book element; None when unusable."""
        symbol = element.get("ticker")
        if not isinstance(symbol, str):
            return None
        bid = _to_float(
            _first_present(element, ("bidPrice", "mid", "tngoLast", "last"))
        )
        ask = _to_float(
            _first_present(element, ("askPrice", "mid", "tngoLast", "last"))
        )
        if bid is None or ask is None:
            return None
        stamp = element.get("quoteTimestamp") or element.get("timestamp")
        return Quote(symbol=symbol, bid=bid, ask=ask, timestamp=self._to_stamp(stamp))

    def _to_stamp(self, stamp):
        """Parse an ISO timestamp, falling back to the clock."""
        if isinstance(stamp, str):
            try:
                stamp = datetime.fromisoformat(stamp)
            except ValueError:
                stamp = self.clock_now()
        elif not isinstance(stamp, datetime):
            stamp = self.clock_now()
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=ET)
        return stamp


class TiingoIex(TiingoStreamSource):
    """IEX top-of-book quote stream (dict elements)."""

    default_endpoint: str = "iex"
    default_threshold_level: int = THRESHOLD_LEVEL


class TiingoFirehose(TiingoStreamSource):
    """Consolidated equity firehose (positional array elements)."""

    default_endpoint: str = EQUITY_ENDPOINT
    default_threshold_level: int = EQUITY_THRESHOLD_LEVEL


def _element_ticker(element: dict | list | tuple):
    """Ticker for either element shape; None when absent."""
    if isinstance(element, dict):
        return element.get("ticker")
    return element[1] if len(element) > 1 else None


def _to_float(value: object) -> float | None:
    """Best-effort numeric conversion; None when unusable."""
    if isinstance(value, bool):
        return None
    if not isinstance(value, (int, float, str)):
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _first_present(element: dict, keys: tuple) -> object:
    """First key present with a non-None value, else None."""
    for key in keys:
        value = element.get(key)
        if value is not None:
            return value
    return None
