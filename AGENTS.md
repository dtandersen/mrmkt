# Agent Instructions

## Sensitive Data

- Never stage or commit secrets or personally identifiable information (PII), even when asked to commit all changes.
- Exclude sensitive files from commits, tell the user what was excluded, and recommend rotating any credentials that were exposed.

Coordinate with other local pi sessions on related codebases. Use `/skill:pi-intercom` for patterns.

**When:** Same codebase (parallel work), reference codebase (consulting patterns), related repos (shared libraries).

**Not when:** Unrelated codebases, trivial questions, or when you can proceed independently.

**Principle:** Prefer `send` for notifications; `ask` only when blocked waiting for input.

Refer to [Architecture](architecture.md). Do not edit it with permission.