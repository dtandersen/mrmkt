# Maintenance and provider worklist

Follow-up items captured from the parallel-session cleanup review. This file is
only a worklist: do not remove or refactor the queued components until each
item is authorized and its tests/reference checks are complete.

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
