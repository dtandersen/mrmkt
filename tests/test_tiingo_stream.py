"""Adapter tests for the Tiingo IEX websocket source (scripted frames)."""

import json
from datetime import UTC, datetime

from hamcrest import assert_that, equal_to
from tests.fakes import CapturingLog

from mrmkt.command.watch import Quote
from mrmkt.ext.tiingo_stream import TiingoStreamSource

MOMENT = datetime(2022, 4, 4, 14, 0, tzinfo=UTC)


def make_source(frames, clock_now=None, log=None, **source_kwargs):
    calls = []

    def fake_connect(handler):
        calls.append(handler)
        for frame in frames:
            handler(frame)

    source = TiingoStreamSource(
        "test-key",
        clock_now if clock_now is not None else (lambda: MOMENT),
        connect=fake_connect,
        log=log if log is not None else CapturingLog(),
        **source_kwargs,
    )
    return source, calls


def frame(*elements, message_type="A"):
    return json.dumps(
        {"service": "iex", "messageType": message_type, "data": list(elements)}
    )


def element(symbol="AAA", **fields):
    row = {"ticker": symbol, "quoteTimestamp": MOMENT.isoformat()}
    row.update(fields)
    return row


def test_top_of_book_frame_forwards_subscribed_symbols_only():
    source, calls = make_source(
        [
            frame(
                element("AAA", bidPrice=106.0, askPrice=107.0),
                element("BBB", bidPrice=206.0, askPrice=207.0),
            )
        ]
    )
    received = []
    source.subscribe(["AAA"], "iex", on_quote=received.append)
    assert_that(len(calls), equal_to(1))
    assert_that(
        received,
        equal_to([Quote(symbol="AAA", bid=106.0, ask=107.0, timestamp=MOMENT)]),
    )


def test_heartbeat_and_subscription_ack_are_ignored():
    source, _calls = make_source(
        [
            frame(message_type="H"),
            json.dumps(
                {
                    "service": "iex",
                    "messageType": "I",
                    "data": "test-subscription-id",
                }
            ),
        ]
    )
    received = []
    source.subscribe(["AAA"], "iex", on_quote=received.append)
    assert_that(received, equal_to([]))


def test_missing_sides_fall_back_then_skip():
    source, _calls = make_source(
        [
            frame(
                element("AAA", mid=106.5),
                element("AAA", bidPrice=None, askPrice=None),
            )
        ]
    )
    received = []
    source.subscribe(["AAA"], "iex", on_quote=received.append)
    assert_that(
        received,
        equal_to([Quote(symbol="AAA", bid=106.5, ask=106.5, timestamp=MOMENT)]),
    )


def test_missing_timestamp_falls_back_to_clock():
    fallback = datetime(2022, 4, 4, 12, 0, tzinfo=UTC)
    source, _calls = make_source(
        [frame(element("AAA", bidPrice=106.0, askPrice=107.0, quoteTimestamp=None))],
        clock_now=lambda: fallback,
    )
    received = []
    source.subscribe(["AAA"], "iex", on_quote=received.append)
    assert_that(
        received,
        equal_to([Quote(symbol="AAA", bid=106.0, ask=107.0, timestamp=fallback)]),
    )


def test_malformed_frame_is_skipped_without_killing_the_stream():
    import io
    from contextlib import redirect_stderr

    source, _calls = make_source(
        [
            "not-json",
            frame(element("AAA", bidPrice=106.0, askPrice=107.0)),
        ]
    )
    received = []
    stderr = io.StringIO()
    with redirect_stderr(stderr):
        source.subscribe(["AAA"], "iex", on_quote=received.append)
    assert_that(len(received), equal_to(1))
    assert_that("skipped" in stderr.getvalue(), equal_to(True))


def test_missing_api_key_is_rejected():
    import pytest

    with pytest.raises(ValueError, match="TIINGO_API_KEY"):
        TiingoStreamSource(None, lambda: MOMENT, log=CapturingLog())


def test_subscribe_message_uses_threshold_filter():
    from mrmkt.ext.tiingo_stream import THRESHOLD_LEVEL, subscribe_message

    assert_that(
        subscribe_message("test-key"),
        equal_to(
            {
                "eventName": "subscribe",
                "authorization": "test-key",
                "eventData": {"thresholdLevel": THRESHOLD_LEVEL},
            }
        ),
    )


def test_logs_connection_and_subscribed_symbols():
    raw = frame(element("AAA", bidPrice=106.0, askPrice=107.0))
    log = CapturingLog()
    source, _calls = make_source([raw], log=log)
    source.subscribe(["AAA", "BBB"], "iex", on_quote=lambda quote: None)

    assert_that(
        log.lines,
        equal_to(
            [
                "Connecting to wss://api.tiingo.com/iex",
                "Subscribing to iex AAA, BBB",
                f"tiingo raw: {raw}",
            ]
        ),
    )


def test_from_env_reads_api_key():
    import os

    from mrmkt.ext.tiingo_prices import TIINGO_API_KEY_ENV_VAR

    saved = os.environ.get(TIINGO_API_KEY_ENV_VAR)
    os.environ[TIINGO_API_KEY_ENV_VAR] = "env-key"
    try:
        source = TiingoStreamSource.from_env(lambda: MOMENT, log=CapturingLog())
        assert_that(source.api_key, equal_to("env-key"))
    finally:
        if saved is None:
            os.environ.pop(TIINGO_API_KEY_ENV_VAR, None)
        else:
            os.environ[TIINGO_API_KEY_ENV_VAR] = saved


def equity_element(symbol="AAA", **overrides):
    row = [MOMENT.isoformat(), symbol, 0.0004, 100, 106.0, 106.5, 107.0, 200]
    for key, value in overrides.items():
        row[
            {
                "date": 0,
                "ticker": 1,
                "spread": 2,
                "bidSize": 3,
                "bidPrice": 4,
                "refPrice": 5,
                "askPrice": 6,
                "askSize": 7,
            }[key]
        ] = value
    return row


def test_equity_array_frame_maps_bid_ask():
    source, _calls = make_source([frame(equity_element())])
    received = []
    source.subscribe(["AAA"], "cons", on_quote=received.append)
    assert_that(
        received,
        equal_to([Quote(symbol="AAA", bid=106.0, ask=107.0, timestamp=MOMENT)]),
    )


def test_equity_array_falls_back_to_reference_price():
    source, _calls = make_source([frame(equity_element(bidPrice=None, askPrice=None))])
    received = []
    source.subscribe(["AAA"], "cons", on_quote=received.append)
    assert_that(
        received,
        equal_to([Quote(symbol="AAA", bid=106.5, ask=106.5, timestamp=MOMENT)]),
    )


def test_equity_reference_only_array_is_skipped():
    source, _calls = make_source([frame([MOMENT.isoformat(), "AAA", 106.5])])
    received = []
    source.subscribe(["AAA"], "cons", on_quote=received.append)
    assert_that(received, equal_to([]))


def test_equity_endpoint_names_stream_in_log():
    from mrmkt.ext.tiingo_stream import EQUITY_ENDPOINT

    raw = frame(equity_element())
    log = CapturingLog()
    source, _calls = make_source([raw], log=log, endpoint=EQUITY_ENDPOINT)
    source.subscribe(["AAA"], "cons", on_quote=lambda quote: None)
    assert_that(
        log.lines,
        equal_to(
            [
                "Connecting to wss://api.tiingo.com/equity/intraday",
                "Subscribing to intraday AAA",
                f"tiingo raw: {raw}",
            ]
        ),
    )
