"""Accidental-peek audit for strategy ``generate()`` code.

Parses strategy source with ``ast`` and flags operations that can read
future bars:

- ``rolling(..., center=True)`` — centered windows blend future bars in.
- ``shift`` / ``pct_change`` / ``diff`` with a negative period — an
  explicit look forward.
- ``rank()`` over the time axis (``axis=0`` or the pandas default) on a
  full-history frame — the rank at bar *t* then depends on future bars.
  Cross-sectional ``rank(axis=1)`` is fine and not flagged.

Scope is deliberately narrow: this catches *accidental* peeks in
otherwise past-only code. It will not catch deliberate cheating
(obfuscated offsets, dynamic windows) or universe-level lookahead
(survivorship, restatements, strategy-selection bias). Paper trading
remains the real backstop.

Run on bundled strategies via the test-suite, or ad hoc on experiment
files::

    python -m mrmkt.backtest.nopeek user-scripts/my_idea.py
"""

from __future__ import annotations

import ast
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class Finding:
    lineno: int
    rule: str
    detail: str


_LOOKAHEAD_FUNCS = {"shift", "pct_change", "diff"}
_AUDITED_METHODS = _LOOKAHEAD_FUNCS | {"rolling", "rank"}


def _is_negative_int(node: ast.AST) -> bool:
    sign = 1
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        sign = -1
        node = node.operand
    elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.UAdd):
        node = node.operand
    return (
        isinstance(node, ast.Constant)
        and isinstance(node.value, int)
        and not isinstance(node.value, bool)
        and sign * node.value < 0
    )


def _is_true(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Constant) and isinstance(node.value, bool) and node.value
    )


class _Visitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.findings: list[Finding] = []
        self.aliases: dict[str, str] = {}

    def visit_Assign(self, node: ast.Assign) -> None:
        # `shift = close.shift` then `shift(-1)` reads the future through
        # a local name. Track simple method aliases (still accidental-looking
        # code); deliberately obfuscated lookahead stays out of scope.
        value = node.value
        if isinstance(value, ast.Attribute) and value.attr in _AUDITED_METHODS:
            for target in node.targets:
                if isinstance(target, ast.Name):
                    self.aliases[target.id] = value.attr
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        func = node.func
        if isinstance(func, ast.Attribute):
            name = func.attr
        elif isinstance(func, ast.Name):
            name = self.aliases.get(func.id)
        else:
            name = None
        if name == "rolling":
            for kw in node.keywords:
                if kw.arg == "center" and _is_true(kw.value):
                    self.findings.append(
                        Finding(
                            node.lineno,
                            "centered-window",
                            "rolling(center=True) blends future bars into the window",
                        )
                    )
        elif name in _LOOKAHEAD_FUNCS:
            periods = node.args[0] if node.args else None
            for kw in node.keywords:
                if kw.arg == "periods":
                    periods = kw.value
            if periods is not None and _is_negative_int(periods):
                self.findings.append(
                    Finding(
                        node.lineno,
                        "negative-period",
                        f"{name}() with a negative period reads future bars",
                    )
                )
        elif name == "rank":
            axis = None
            for kw in node.keywords:
                if kw.arg == "axis":
                    axis = kw.value
            if axis is None:
                self.findings.append(
                    Finding(
                        node.lineno,
                        "time-axis-rank",
                        "rank() defaults to axis=0 (over time): ranks at bar t "
                        "depend on future bars; use rank(axis=1) for cross-sections",
                    )
                )
            elif isinstance(axis, ast.Constant) and (
                axis.value == 0 or axis.value == "index"
            ):
                self.findings.append(
                    Finding(
                        node.lineno,
                        "time-axis-rank",
                        "rank over the time axis ranks history: values at bar t "
                        "depend on future bars; use rank(axis=1) for cross-sections",
                    )
                )
        self.generic_visit(node)


def audit_source(source: str) -> list[Finding]:
    """Flag future-referencing ops in a source string."""
    try:
        tree = ast.parse(source)
    except SyntaxError as error:
        return [Finding(error.lineno or 0, "unparseable", f"cannot parse: {error}")]
    visitor = _Visitor()
    visitor.visit(tree)
    return sorted(visitor.findings, key=lambda f: f.lineno)


def audit_path(path: str) -> list[Finding]:
    """Flag future-referencing ops in a source file."""
    try:
        with open(path, encoding="utf-8") as handle:
            return audit_source(handle.read())
    except OSError as error:
        raise OSError(f"cannot read {path}: {error}") from error


def main(argv: list[str]) -> int:
    if not argv:
        print("usage: python -m mrmkt.backtest.nopeek <file.py> [...]", file=sys.stderr)
        return 2
    failed = False
    for path in argv:
        try:
            findings = audit_path(path)
        except OSError as error:
            print(f"{path}: cannot read ({error})", file=sys.stderr)
            failed = True
            continue
        if findings:
            failed = True
            for finding in findings:
                print(f"{path}:{finding.lineno}: [{finding.rule}] {finding.detail}")
        else:
            print(f"{path}: clean")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
