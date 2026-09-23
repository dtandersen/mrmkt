# Maintenance and provider worklist

Follow-up items captured from the parallel-session cleanup review. This file is
only a worklist: do not remove or refactor the queued components until each
item is authorized and its tests/reference checks are complete.

## Tier 1 — queued dead-code cleanup

The following were reported as dead (no imports/tests or active CLI entrypoints)
and are candidates for removal. Before each deletion, verify references and run
the relevant/full test suite. Preserve the tested indicator module where noted.

- [ ] `src/mrmkt/backend/` — both files are reported as empty.
- [ ] `src/mrmkt/ext/tiingo_realtime.py` and `src/mrmkt/repo/realtime.py` —
  reported dead real-time stub chain.
- [ ] `src/mrmkt/common/config.py` — reported used only by dead scratch code.
- [ ] Root scripts: `bt_test.py`, `socket_test.py`, `tiingo2.py` (contains a
  hardcoded token URL), and `sortino.py`.
- [ ] Keep `src/mrmkt/indicator/sortino.py`; it is tested and is not part of the
  root-script cleanup.

## Tier 2 — preserve and promote Tiingo

- [ ] Do **not** delete Tiingo. Refactor `src/mrmkt/ext/tiingo.py` into a
  first-class price provider on the same footing as Alpaca, selectable from the
  supported CLI `--provider` option.
- [ ] Keep `tests/test_tiingo.py` passing and add provider/CLI integration tests
  for selection, configuration, and error handling.

## Open triage — no action until user decision

Decide whether to rewire these into supported workflows or remove them:

- FMP extension (`src/mrmkt/ext/fmp.py`)
- FinancialLoader use case
- PriceLoader use case
- Buffett model and RunModel

Do not delete these pending that decision. Record the intended supported use
(or explicit deprecation) for each before changing it.
