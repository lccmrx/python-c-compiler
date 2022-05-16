import parser.utils as p
import tree.nodes as nodes

from core.errors import error_collector
from parser.utils import (add_range, log_error, ParserError,
                                 raise_error)

def parse(tokens_to_parse):
    p.best_error = None
    p.tokens = tokens_to_parse

    with log_error():
        return parse_root(0)[0]

    error_collector.add(p.best_error)
    return None


@add_range
def parse_root(index):
    """Parse the given tokens into an AST."""
    items = []
    while True:
        with log_error():
            item, index = parse_func_definition(index)
            items.append(item)
            continue

        with log_error():
            item, index = parse_declaration(index)
            items.append(item)
            continue

        # If neither parse attempt above worked, break
        break

    # If there are tokens that remain unparsed, complain
    if not p.tokens[index:]:
        return nodes.Root(items), index
    else:
        raise_error("unexpected token", index, ParserError.AT)
