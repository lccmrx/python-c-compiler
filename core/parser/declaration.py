import core.ctypes as ctypes
from core.errors import error_collector, CompilerError
import core.parser.utils as p
from core import tokens as tks
import core.tree.decl_nodes as decl_nodes
import core.tree.nodes as nodes
from core.parser.expression import parse_expression
from core.parser.utils import (add_range, ParserError, match_token, token_is,
                                 raise_error, log_error, token_in)


@add_range
def parse_func_definition(index):
    specs, index = parse_decl_specifiers(index)
    decl, index = parse_declarator(index)

    from core.parser.statement import parse_compound_statement
    body, index = parse_compound_statement(index)

    root = decl_nodes.Root(specs, [decl])
    return nodes.Declaration(root, body), index


@add_range
def parse_declaration(index):
    node, index = parse_decls_inits(index)
    return nodes.Declaration(node), index

@add_range
def parse_abstract_declarator(index):
    root, index = parse_declarator(index)
    node = root
    while not isinstance(node, decl_nodes.Identifier):
        node = node.child

    if node.identifier:
        err = "expected abstract declarator, but identifier name was provided"
        error_collector.add(CompilerError(err, node.identifier.r))

    return root, index
@add_range
def parse_decls_inits(index, parse_inits=True):

    if token_is(index, tks.semicolon):
        return decl_nodes.Root(specs, []), index + 1

    decls = []
    inits = []

    while True:
        # node, index = parse_declarator(index, is_typedef)
        # print(node)
        # decls.append(node)

        if token_is(index, tks.equals) and parse_inits:
            from core.parser.expression import parse_assignment
            expr, index = parse_assignment(index + 1)
            inits.append(expr)
        else:
            inits.append(None)

        print(inits)
        if token_is(index, tks.comma):
            index += 1
        else:
            break
    index = match_token(index, tks.semicolon, ParserError.AFTER)

    node = decl_nodes.Root(specs, decls, inits)
    return node, index

def parse_decl_specifiers(index, _spec_qual=False):
    type_specs = set(ctypes.simple_types.keys())

    type_quals = {}

    storage_specs = {}

    specs = []

    SIMPLE = 1
    STRUCT = 2
    TYPEDEF = 3
    type_spec_class = None

    while True:
        if (not type_spec_class
              and token_is(index, tks.identifier)
              and p.symbols.is_typedef(p.tokens[index])):
            specs.append(p.tokens[index])
            index += 1
            type_spec_class = TYPEDEF

        elif type_spec_class in {None, SIMPLE} and token_in(index, type_specs):
            specs.append(p.tokens[index])
            index += 1
            type_spec_class = SIMPLE

        elif token_in(index, type_quals):
            specs.append(p.tokens[index])
            index += 1

        elif token_in(index, storage_specs):
            if not _spec_qual:
                specs.append(p.tokens[index])
            else:
                err = "storage specifier not permitted here"
                error_collector.add(CompilerError(err, p.tokens[index].r))
            index += 1

        else:
            break

    if specs:
        return specs, index
    else:
        raise_error("expected declaration specifier", index, ParserError.AT)


def parse_spec_qual_list(index):
    return parse_decl_specifiers(index, True)
