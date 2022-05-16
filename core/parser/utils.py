
from contextlib import contextmanager
import copy

from core.errors import CompilerError, Range

tokens = None

class SimpleSymbolTable:
    def __init__(self):
        self.symbols = []
        self.new_scope()

    def new_scope(self):
        self.symbols.append({})

    def end_scope(self):
        self.symbols.pop()

    def add_symbol(self, identifier, is_typedef):
        self.symbols[-1][identifier.content] = is_typedef

    def is_typedef(self, identifier):
        name = identifier.content
        for table in self.symbols[::-1]:
            if name in table:
                return table[name]
        return False


symbols = SimpleSymbolTable()

class ParserError(CompilerError):
    AT = 1
    GOT = 2
    AFTER = 3

    def __init__(self, message, index, tokens, message_type):
        
        self.amount_parsed = index

        if len(tokens) == 0:
            super().__init__(f"{message} at beginning of source")
            return

        # If the index is too big, we're always using the AFTER form
        if index >= len(tokens):
            index = len(tokens)
            message_type = self.AFTER
        # If the index is too small, we should not use the AFTER form
        elif index <= 0:
            index = 0
            if message_type == self.AFTER:
                message_type = self.GOT

        if message_type == self.AT:
            super().__init__(f"{message} at '{tokens[index]}'",
                             tokens[index].r)
        elif message_type == self.GOT:
            super().__init__(f"{message}, got '{tokens[index]}'",
                             tokens[index].r)
        elif message_type == self.AFTER:
            if tokens[index - 1].r:
                new_range = Range(tokens[index - 1].r.end + 1)
            else:
                new_range = None

            super().__init__(
                f"{message} after '{tokens[index - 1]}'", new_range)


def raise_error(err, index, error_type):
    global tokens
    raise ParserError(err, index, tokens, error_type)

best_error = None

@contextmanager
def log_error():

    global best_error, symbols

    # back up the global symbols table, so if parsing fails we can reset it
    symbols_bak = copy.deepcopy(symbols)
    try:
        yield
    except ParserError as e:
        if not best_error or e.amount_parsed >= best_error.amount_parsed:
            best_error = e
        symbols = symbols_bak


def token_is(index, kind):
    """Return true if the next token is of the given kind."""
    global tokens
    return len(tokens) > index and tokens[index].kind == kind


def token_in(index, kinds):
    """Return true if the next token is in the given list/set of kinds."""
    global tokens
    return len(tokens) > index and tokens[index].kind in kinds


def match_token(index, kind, message_type, message=None):

    global tokens
    if not message:
        message = f"expected '{kind.text_repr}'"

    if token_is(index, kind):
        return index + 1
    else:
        raise ParserError(message, index, tokens, message_type)


def token_range(start, end):
    global tokens

    start_index = min(start, len(tokens) - 1, end - 1)
    end_index = min(end - 1, len(tokens) - 1)
    return tokens[start_index].r + tokens[end_index].r


def add_range(parse_func):
    """Return a decorated function that tags the produced node with a range.

    Accepts a parse_* function, and returns a version of the function where
    the returned node has its range attribute set

    """
    global tokens

    def parse_with_range(index, *args):
        start_index = index
        node, end_index = parse_func(index, *args)
        node.r = token_range(start_index, end_index)

        return node, end_index

    return parse_with_range
