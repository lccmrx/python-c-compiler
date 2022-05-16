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
def parse_declarator(index, is_typedef=False):
    end = _find_decl_end(index)
    return _parse_declarator(index, end, is_typedef), end


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
    specs, index = parse_decl_specifiers(index)

    if token_is(index, tks.semicolon):
        return decl_nodes.Root(specs, []), index + 1

    is_typedef = False

    decls = []
    inits = []

    while True:
        node, index = parse_declarator(index, is_typedef)
        decls.append(node)

        if token_is(index, tks.equals) and parse_inits:
            from core.parser.expression import parse_assignment
            expr, index = parse_assignment(index + 1)
            inits.append(expr)
        else:
            inits.append(None)

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


def parse_parameter_list(index):
    params = []

    if token_is(index, tks.r_paren):
        return params, index

    while True:
        specs, index = parse_decl_specifiers(index)
        decl, index = parse_declarator(index)
        params.append(decl_nodes.Root(specs, [decl]))

        if token_is(index, tks.comma):
            index += 1
        else:
            break

    return params, index

def parse_struct_union_members(index):
    members = []

    while True:
        if token_is(index, tks.close_brack):
            return members, index + 1

        node, index = parse_decls_inits(index, False)
        members.append(node)


def _find_pair_forward(index,
                       open=tks.l_paren,
                       close=tks.r_paren,
                       mess="mismatched parentheses in declaration"):
    depth = 0
    for i in range(index, len(p.tokens)):
        if p.tokens[i].kind == open:
            depth += 1
        elif p.tokens[i].kind == close:
            depth -= 1

        if depth == 0:
            break
    else:
        raise_error(mess, index, ParserError.AT)
    return i


def _find_pair_backward(index,
                        open=tks.l_paren,
                        close=tks.r_paren,
                        mess="mismatched parentheses in declaration"):
    depth = 0
    for i in range(index, -1, -1):
        if p.tokens[i].kind == close:
            depth += 1
        elif p.tokens[i].kind == open:
            depth -= 1

        if depth == 0:
            break
    else:
        raise_error(mess, index, ParserError.AT)
    return i


def _find_decl_end(index):
    if (token_is(index, tks.star) or
         token_is(index, tks.identifier)):
        return _find_decl_end(index + 1)
    elif token_is(index, tks.l_paren):
        close = _find_pair_forward(index)
        return _find_decl_end(close + 1)
    elif token_is(index, tks.l_sq_brack):
        mess = "mismatched square brackets in declaration"
        close = _find_pair_forward(index, tks.l_sq_brack,
                                   tks.close_sq_brack, mess)
        return _find_decl_end(close + 1)
    else:
        return index


def _parse_declarator(start, end, is_typedef):
    decl = _parse_declarator_raw(start, end, is_typedef)
    decl.r = p.tokens[start].r + p.tokens[end - 1].r
    return decl


def _parse_declarator_raw(start, end, is_typedef):
    if start == end:
        return decl_nodes.Identifier(None)

    elif (start + 1 == end and
           p.tokens[start].kind == tks.identifier):
        p.symbols.add_symbol(p.tokens[start], is_typedef)
        return decl_nodes.Identifier(p.tokens[start])

    elif p.tokens[start].kind == tks.star:
        const, index = _find_const(start + 1)
        return decl_nodes.Pointer(
            _parse_declarator(index, end, is_typedef), const)

    func_decl = _try_parse_func_decl(start, end, is_typedef)
    if func_decl: return func_decl

    elif (p.tokens[start].kind == tks.l_paren and
          _find_pair_forward(start) == end - 1):
        return _parse_declarator(start + 1, end - 1, is_typedef)

    elif p.tokens[end - 1].kind == tks.close_sq_brack:
        open_sq = _find_pair_backward(
            end - 1, tks.l_sq_brack, tks.close_sq_brack,
            "mismatched square brackets in declaration")

        if open_sq == end - 2:
            num_el = None
        else:
            num_el, index = parse_expression(open_sq + 1)
            if index != end - 1:
                err = "unexpected token in array size"
                raise_error(err, index, ParserError.AFTER)

        return decl_nodes.Array(
            num_el, _parse_declarator(start, open_sq, is_typedef))

    raise_error("faulty declaration syntax", start, ParserError.AT)
