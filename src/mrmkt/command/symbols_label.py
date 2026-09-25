"""Symbol label command."""

from mrmkt.command.symbols_common import TagChangeResult, apply_symbol_tags


class LabelSymbols:
    """Tag stored symbols; reports counts for the CLI to render."""

    def __init__(self, repository):
        self.repository = repository

    def execute(self, symbols: str, tag: str) -> TagChangeResult:
        return apply_symbol_tags(self.repository, symbols, tag, add=True)
