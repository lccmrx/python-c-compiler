"""Parser logic that parses expression nodes."""

from core import tokens as tks
import parser.utils as p
import core.tree.expr_nodes as expr_nodes
import core.tree.decl_nodes as decl_nodes
from core.parser.utils import (add_range, match_token, token_is, ParserError,
                                 raise_error, log_error, token_in)

@add_range
def parse_expression(index):
    """Parse expression."""
    return parse_series(
        index, parse_assignment,
        {tks.comma: expr_nodes.MultiExpr})


@add_range
def parse_assignment(index):

    left, index = parse_conditional(index)

    if index < len(p.tokens):
        op = p.tokens[index]
        kind = op.kind
    else:
        op = None
        kind = None

    node_types = {tks.equals: expr_nodes.Equals,
                  tks.plusequals: expr_nodes.PlusEquals,
                  tks.minusequals: expr_nodes.MinusEquals,
                  tks.starequals: expr_nodes.StarEquals,
                  tks.divequals: expr_nodes.DivEquals,
                  tks.modequals: expr_nodes.ModEquals}

    if kind in node_types:
        right, index = parse_assignment(index + 1)
        return node_types[kind](left, right, op), index
    else:
        return left, index


@add_range
def parse_conditional(index):
    """Parse a conditional expression."""
    # TODO: Parse ternary operator
    return parse_logical_or(index)


@add_range
def parse_logical_or(index):
    """Parse logical or expression."""
    return parse_series(
        index, parse_logical_and,
        {token_kinds.bool_or: expr_nodes.BoolOr})


@add_range
def parse_logical_and(index):
    """Parse logical and expression."""
    # TODO: Implement bitwise operators here.
    return parse_series(
        index, parse_equality,
        {tks.bool_and: expr_nodes.BoolAnd})


@add_range
def parse_equality(index):
    """Parse equality expression."""
    # TODO: Implement relational and shift expressions here.
    return parse_series(
        index, parse_relational,
        {tks.twoequals: expr_nodes.Equality,
         tks.notequal: expr_nodes.Inequality})


@add_range
def parse_relational(index):
    """Parse relational expression."""
    return parse_series(
        index, parse_bitwise,
        {tks.lt: expr_nodes.LessThan,
         tks.gt: expr_nodes.GreaterThan,
         tks.ltoe: expr_nodes.LessThanOrEq,
         tks.gtoe: expr_nodes.GreaterThanOrEq})


@add_range
def parse_bitwise(index):
    return parse_series(
        index, parse_additive,
        {tks.lbitshift: expr_nodes.LBitShift,
         tks.rbitshift: expr_nodes.RBitShift})


@add_range
def parse_additive(index):
    """Parse additive expression."""
    return parse_series(
        index, parse_multiplicative,
        {tks.plus: expr_nodes.Plus,
         tks.minus: expr_nodes.Minus})


@add_range
def parse_multiplicative(index):
    """Parse multiplicative expression."""
    return parse_series(
        index, parse_cast,
        {tks.star: expr_nodes.Mult,
         tks.slash: expr_nodes.Div,
         tks.mod: expr_nodes.Mod})


@add_range
def parse_cast(index):
    """Parse cast expression."""

    from shivyc.parser.declaration import (
        parse_abstract_declarator, parse_spec_qual_list)

    with log_error():
        match_token(index, tks.open_paren, ParserError.AT)
        specs, index = parse_spec_qual_list(index + 1)
        node, index = parse_abstract_declarator(index)
        match_token(index, tks.close_paren, ParserError.AT)

        decl_node = decl_nodes.Root(specs, [node])
        expr_node, index = parse_cast(index + 1)
        return expr_nodes.Cast(decl_node, expr_node), index

    return parse_unary(index)


@add_range
def parse_unary(index):
    """Parse unary expression."""

    unary_args = {tks.incr: (parse_unary, expr_nodes.PreIncr),
                  tks.decr: (parse_unary, expr_nodes.PreDecr),
                  tks.amp: (parse_cast, expr_nodes.AddrOf),
                  tks.star: (parse_cast, expr_nodes.Deref),
                  tks.bool_not: (parse_cast, expr_nodes.BoolNot),
                  tks.plus: (parse_cast, expr_nodes.UnaryPlus),
                  tks.minus: (parse_cast, expr_nodes.UnaryMinus),
                  tks.compl: (parse_cast, expr_nodes.Compl)}

    if token_in(index, unary_args):
        parse_func, NodeClass = unary_args[p.tokens[index].kind]
        subnode, index = parse_func(index + 1)
        return NodeClass(subnode), index
    elif token_is(index, tks.sizeof_kw):
        with log_error():
            node, index = parse_unary(index + 1)
            return expr_nodes.SizeofExpr(node), index


        match_token(index + 1, tks.open_paren, ParserError.AFTER)
        specs, index = parse_spec_qual_list(index + 2)
        node, index = parse_abstract_declarator(index)
        match_token(index, tks.close_paren, ParserError.AT)
        decl_node = decl_nodes.Root(specs, [node])

        return expr_nodes.SizeofType(decl_node), index + 1
    else:
        return parse_postfix(index)


@add_range
def parse_postfix(index):
    """Parse postfix expression."""
    cur, index = parse_primary(index)

    while True:
        old_range = cur.r

        if token_is(index, tks.open_sq_brack):
            index += 1
            arg, index = parse_expression(index)
            cur = expr_nodes.ArraySubsc(cur, arg)
            match_token(index, tks.close_sq_brack, ParserError.GOT)
            index += 1

        elif (token_is(index, tks.dot) or
              token_is(index, tks.arrow)):
            index += 1
            match_token(index, tks.identifier, ParserError.AFTER)
            member = p.tokens[index]

            if token_is(index - 1, tks.dot):
                cur = expr_nodes.ObjMember(cur, member)
            else:
                cur = expr_nodes.ObjPtrMember(cur, member)

            index += 1

        elif token_is(index, tks.open_paren):
            args = []
            index += 1

            if token_is(index, tks.close_paren):
                return expr_nodes.FuncCall(cur, args), index + 1

            while True:
                arg, index = parse_assignment(index)
                args.append(arg)

                if token_is(index, tks.comma):
                    index += 1
                else:
                    break

            index = match_token(
                index, tks.close_paren, ParserError.GOT)

            return expr_nodes.FuncCall(cur, args), index

        elif token_is(index, tks.incr):
            index += 1
            cur = expr_nodes.PostIncr(cur)
        elif token_is(index, tks.decr):
            index += 1
            cur = expr_nodes.PostDecr(cur)
        else:
            return cur, index

        cur.r = old_range + p.tokens[index - 1].r


@add_range
def parse_primary(index):
    """Parse primary expression."""
    if token_is(index, tks.open_paren):
        node, index = parse_expression(index + 1)
        index = match_token(index, tks.close_paren, ParserError.GOT)
        return expr_nodes.ParenExpr(node), index
    elif token_is(index, tks.number):
        return expr_nodes.Number(p.tokens[index]), index + 1
    elif (token_is(index, tks.identifier)
          and not p.symbols.is_typedef(p.tokens[index])):
        return expr_nodes.Identifier(p.tokens[index]), index + 1
    elif token_is(index, tks.string):
        return expr_nodes.String(p.tokens[index].content), index + 1
    elif token_is(index, tks.char_string):
        chars = p.tokens[index].content
        return expr_nodes.Number(chars[0]), index + 1
    else:
        raise_error("expected expression", index, ParserError.GOT)


def parse_series(index, parse_base, separators):

    cur, index = parse_base(index)
    while True:
        for s in separators:
            if token_is(index, s):
                break
        else:
            return cur, index

        tok = p.tokens[index]
        new, index = parse_base(index + 1)
        cur = separators[s](cur, new, tok)
