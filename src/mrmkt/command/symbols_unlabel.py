"""Symbol catalog commands (import/list/label/unlabel)."""



from mrmkt.command import symbols_app
from mrmkt.command.symbols_common import _change_symbol_tags


@symbols_app.command("unlabel")
def unlabel_symbols(symbols: str, tag: str) -> None:
    _change_symbol_tags(symbols, tag, add=False)
