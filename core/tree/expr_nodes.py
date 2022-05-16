import core.tree.nodes as nodes

from core.errors import CompilerError
from core.tree.utils import (IndirectLValue, DirectLValue, RelativeLValue,
                               check_cast, set_type, arith_convert,
                               get_size, report_err, shift_into_range)

class _ExprNode(nodes.Node):
    
    def __init__(self):
        super().__init__()

    def make_il(self, il_code, symbol_table, c):
        
        raise NotImplementedError

    def make_il_raw(self, il_code, symbol_table, c):
        raise NotImplementedError

    def lvalue(self, il_code, symbol_table, c):
        raise NotImplementedError


class _RExprNode(nodes.Node):
    def __init__(self):  # noqa D102
        nodes.Node.__init__(self)
        self._cache_raw_ilvalue = None

    def make_il(self, il_code, symbol_table, c):  # noqa D102
        raise NotImplementedError

    def make_il_raw(self, il_code, symbol_table, c):  # noqa D102
        return self.make_il(il_code, symbol_table, c)

    def lvalue(self, il_code, symbol_table, c):  # noqa D102
        return None


class _LExprNode(nodes.Node):
    def __init__(self):
        super().__init__()
        self._cache_lvalue = None

    def make_il(self, il_code, symbol_table, c):  # noqa D102
        lvalue = self.lvalue(il_code, symbol_table, c)

        if lvalue.ctype().is_array():
            addr = lvalue.addr(il_code)
            return set_type(addr, PointerCType(lvalue.ctype().el), il_code)

        elif lvalue.ctype().is_function():
            return lvalue.addr(il_code)

        else:
            return lvalue.val(il_code)

    def make_il_raw(self, il_code, symbol_table, c):  # noqa D102
        return self.lvalue(il_code, symbol_table, c).val(il_code)

    def lvalue(self, il_code, symbol_table, c):
        if not self._cache_lvalue:
            self._cache_lvalue = self._lvalue(il_code, symbol_table, c)
        return self._cache_lvalue

    def _lvalue(self, il_code, symbol_table, c):
        raise NotImplementedError


class MultiExpr(_RExprNode):
    def __init__(self, left, right, op):
        self.left = left
        self.right = right
        self.op = op

    def make_il(self, il_code, symbol_table, c):
        self.left.make_il(il_code, symbol_table, c)
        return self.right.make_il(il_code, symbol_table, c)

class Number(_RExprNode):
    def __init__(self, number):
        super().__init__()
        self.number = number

    def make_il(self, il_code, symbol_table, c):
        v = int(str(self.number))

        if ctypes.int_min <= v <= ctypes.int_max:
            il_value = ILValue(ctypes.integer)
        elif ctypes.long_min <= v <= ctypes.long_max:
            il_value = ILValue(ctypes.longint)
        else:
            err = "integer literal too large to be represented by any " \
                  "integer type"
            raise CompilerError(err, self.number.r)

        il_code.register_literal_var(il_value, v)
        return il_value


class String(_LExprNode):
    def __init__(self, chars):
        super().__init__()
        self.chars = chars

    def _lvalue(self, il_code, symbol_table, c):
        il_value = ILValue(ArrayCType(ctypes.char, len(self.chars)))
        il_code.register_string_literal(il_value, self.chars)
        return DirectLValue(il_value)


class Identifier(_LExprNode):
    def __init__(self, identifier):
        super().__init__()
        self.identifier = identifier

    def _lvalue(self, il_code, symbol_table, c):
        var = symbol_table.lookup_variable(self.identifier)
        return DirectLValue(var)


class ParenExpr(nodes.Node):
    def __init__(self, expr):
        super().__init__()
        self.expr = expr

    def lvalue(self, il_code, symbol_table, c):
        return self.expr.lvalue(il_code, symbol_table, c)

    def make_il(self, il_code, symbol_table, c):
        return self.expr.make_il(il_code, symbol_table, c)

    def make_il_raw(self, il_code, symbol_table, c):
        return self.expr.make_il_raw(il_code, symbol_table, c)

class _ArithBinOp(_RExprNode):
    def __init__(self, left, right, op):
        super().__init__()
        self.left = left
        self.right = right
        self.op = op

    def make_il(self, il_code, symbol_table, c):
        left = self.left.make_il(il_code, symbol_table, c)
        right = self.right.make_il(il_code, symbol_table, c)

        if self._check_type(left, right):
            left, right = arith_convert(left, right, il_code)

            if left.literal and right.literal:
                try:
                    val = self._arith_const(
                        shift_into_range(left.literal.val, left.ctype),
                        shift_into_range(right.literal.val, right.ctype),
                        left.ctype)
                    out = ILValue(left.ctype)
                    il_code.register_literal_var(out, val)
                    return out

                except NotImplementedError:
                    pass

            return self._arith(left, right, il_code)

        else:
            return self._nonarith(left, right, il_code)

    def _check_type(self, left, right):
        return left.ctype.is_arith() and right.ctype.is_arith()

    def _arith(self, left, right, il_code):
        out = ILValue(left.ctype)
        # il_code.add(self.default_il_cmd(out, left, right))
        return out

    def _arith_const(self, left, right, ctype):
        raise NotImplementedError

    def _nonarith(self, left, right, il_code):
        raise NotImplementedError

class Plus(_ArithBinOp):
    def __init__(self, left, right, op):
        super().__init__(left, right, op)

    def _arith_const(self, left, right, ctype):
        return shift_into_range(left + right, ctype)

    def _nonarith(self, left, right, il_code):

        if left.ctype.is_pointer() and right.ctype.is_integral():
            arith, pointer = right, left
        elif right.ctype.is_pointer() and left.ctype.is_integral():
            arith, pointer = left, right
        else:
            err = "invalid operand types for addition"
            raise CompilerError(err, self.op.r)

        if not pointer.ctype.arg.is_complete():
            err = "invalid arithmetic on pointer to incomplete type"
            raise CompilerError(err, self.op.r)

        out = ILValue(pointer.ctype)
        shift = get_size(pointer.ctype.arg, arith, il_code)
        il_code.add(math_cmds.Add(out, pointer, shift))
        return out

class Minus(_ArithBinOp):
    def __init__(self, left, right, op):
        super().__init__(left, right, op)

    def _arith_const(self, left, right, ctype):
        return shift_into_range(left - right, ctype)

    def _nonarith(self, left, right, il_code):
        if (left.ctype.is_pointer() and right.ctype.is_pointer()
             and left.ctype.compatible(right.ctype)):

            if (not left.ctype.arg.is_complete() or
                  not right.ctype.arg.is_complete()):
                err = "invalid arithmetic on pointers to incomplete types"
                raise CompilerError(err, self.op.r)

            raw = ILValue(ctypes.longint)
            il_code.add(math_cmds.Subtr(raw, left, right))

            out = ILValue(ctypes.longint)
            size = ILValue(ctypes.longint)
            il_code.register_literal_var(size, str(left.ctype.arg.size))
            il_code.add(math_cmds.Div(out, raw, size))

            return out

        elif left.ctype.is_pointer() and right.ctype.is_integral():
            if not left.ctype.arg.is_complete():
                err = "invalid arithmetic on pointer to incomplete type"
                raise CompilerError(err, self.op.r)

            out = ILValue(left.ctype)
            shift = get_size(left.ctype.arg, right, il_code)
            il_code.add(math_cmds.Subtr(out, left, shift))
            return out

        else:
            descrip = "invalid operand types for subtraction"
            raise CompilerError(descrip, self.op.r)

class Mult(_ArithBinOp):
    def __init__(self, left, right, op):
        super().__init__(left, right, op)

    def _arith_const(self, left, right, ctype):
        return shift_into_range(left * right, ctype)

    def _nonarith(self, left, right, il_code):
        err = "invalid operand types for multiplication"
        raise CompilerError(err, self.op.r)

class _IntBinOp(_ArithBinOp):
    def _check_type(self, left, right):
        return left.ctype.is_integral() and right.ctype.is_integral()


class Div(_ArithBinOp):
    def __init__(self, left, right, op):
        super().__init__(left, right, op)

    def _arith_const(self, left, right, ctype):
        return shift_into_range(int(left / right), ctype)

    def _nonarith(self, left, right, il_code):
        err = "invalid operand types for division"
        raise CompilerError(err, self.op.r)

class Mod(_IntBinOp):
    def __init__(self, left, right, op):
        super().__init__(left, right, op)

    def _nonarith(self, left, right, il_code):
        err = "invalid operand types for modulus"
        raise CompilerError(err, self.op.r)

class _Equality(_ArithBinOp):
    eq_il_cmd = None

    def __init__(self, left, right, op):
        super().__init__(left, right, op)

    def _arith(self, left, right, il_code):
        out = ILValue(ctypes.integer)
        il_code.add(self.eq_il_cmd(out, left, right))
        return out

    def _nonarith(self, left, right, il_code):
        if (left.ctype.is_pointer()
             and getattr(right.literal, "val", None) == 0):
            right = set_type(right, left.ctype, il_code)
        elif (right.ctype.is_pointer()
              and getattr(left.literal, "val", None) == 0):
            left = set_type(left, right.ctype, il_code)

        # If both operands are not pointer types, quit now
        if not left.ctype.is_pointer() or not right.ctype.is_pointer():
            with report_err():
                err = "comparison between incomparable types"
                raise CompilerError(err, self.op.r)

        # If one side is pointer to void, cast the other to same.
        elif left.ctype.arg.is_void():
            check_cast(right, left.ctype, self.op.r)
            right = set_type(right, left.ctype, il_code)
        elif right.ctype.arg.is_void():
            check_cast(left, right.ctype, self.op.r)
            left = set_type(left, right.ctype, il_code)

        # If both types are still incompatible, warn!
        elif not left.ctype.compatible(right.ctype):
            with report_err():
                err = "comparison between distinct pointer types"
                raise CompilerError(err, self.op.r)

        # Now, we can do comparison
        out = ILValue(ctypes.integer)
        il_code.add(self.eq_il_cmd(out, left, right))
        return out

class Equality(_Equality):
    pass

class Inequality(_Equality):
    pass

class Equals(_RExprNode):

    def __init__(self, left, right, op):
        super().__init__()
        self.left = left
        self.right = right
        self.op = op

    def make_il(self, il_code, symbol_table, c):
        right = self.right.make_il(il_code, symbol_table, c)
        lvalue = self.left.lvalue(il_code, symbol_table, c)

        if lvalue and lvalue.modable():
            return lvalue.set_to(right, il_code, self.op.r)
        else:
            err = "expression on left of '=' is not assignable"
            raise CompilerError(err, self.left.r)

class _CompoundPlusMinus(_RExprNode):
    command = None
    accept_pointer = False

    def __init__(self, left, right, op):
        super().__init__()
        self.left = left
        self.right = right
        self.op = op

    def make_il(self, il_code, symbol_table, c):
        right = self.right.make_il(il_code, symbol_table, c)
        lvalue = self.left.lvalue(il_code, symbol_table, c)
        if not lvalue or not lvalue.modable():
            err = f"expression on left of '{str(self.op)}' is not assignable"
            raise CompilerError(err, self.left.r)

        if (lvalue.ctype().is_pointer()
            and right.ctype.is_integral()
             and self.accept_pointer):

            if not lvalue.ctype().arg.is_complete():
                err = "invalid arithmetic on pointer to incomplete type"
                raise CompilerError(err, self.op.r)

            left = self.left.make_il(il_code, symbol_table, c)

            out = ILValue(left.ctype)
            shift = get_size(left.ctype.arg, right, il_code)

            il_code.add(self.command(out, left, shift))
            lvalue.set_to(out, il_code, self.op.r)
            return out

        elif lvalue.ctype().is_arith() and right.ctype.is_arith():
            left = self.left.make_il(il_code, symbol_table, c)
            out = ILValue(left.ctype)

            left, right = arith_convert(left, right, il_code)
            il_code.add(self.command(out, left, right))
            lvalue.set_to(out, il_code, self.op.r)
            return out

        else:
            err = f"invalid types for '{str(self.op)}' operator"
            raise CompilerError(err, self.op.r)

class _ArithUnOp(_RExprNode):
    descrip = None
    opnd_descrip = "arithmetic"
    cmd = None

    def __init__(self, expr):
        super().__init__()
        self.expr = expr

    def make_il(self, il_code, symbol_table, c):
        expr = self.expr.make_il(il_code, symbol_table, c)
        if not self._check_type(expr):
            err = f"{self.descrip} requires {self.opnd_descrip} type operand"
            raise CompilerError(err, self.expr.r)
        if expr.ctype.size < 4:
            expr = set_type(expr, ctypes.integer, il_code)
        if self.cmd:
            out = ILValue(expr.ctype)
            if expr.literal:
                val = self._arith_const(expr.literal.val, expr.ctype)
                val = shift_into_range(val, expr.ctype)
                il_code.register_literal_var(out, val)
            else:
                il_code.add(self.cmd(out, expr))
            return out
        return expr

    def _check_type(self, expr):
        return expr.ctype.is_arith()

    def _arith_const(self, expr, ctype):
        raise NotImplementedError


class UnaryPlus(_ArithUnOp):
    descrip = "unary plus"


class UnaryMinus(_ArithUnOp):
    descrip = "unary minus"

    def _arith_const(self, expr, ctype):
        return -shift_into_range(expr, ctype)

class Compl(_ArithUnOp):
    descrip = "bit-complement"
    opnd_descrip = "integral"

    def _check_type(self, expr):
        return expr.ctype.is_integral()

    def _arith_const(self, expr, ctype):
        return ~shift_into_range(expr, ctype)

class _SizeofNode(_RExprNode):
    def __init__(self):
        super().__init__()

    def sizeof_ctype(self, ctype, range, il_code):
        if ctype.is_function():
            err = "sizeof argument cannot have function type"
            raise CompilerError(err, range)

        if ctype.is_incomplete():
            err = "sizeof argument cannot have incomplete type"
            raise CompilerError(err, range)

        out = ILValue(ctypes.unsig_longint)
        il_code.register_literal_var(out, ctype.size)
        return out

class AddrOf(_RExprNode):
    def __init__(self, expr):
        super().__init__()
        self.expr = expr

    def make_il(self, il_code, symbol_table, c):
        lvalue = self.expr.lvalue(il_code, symbol_table, c)
        if lvalue:
            return lvalue.addr(il_code)
        else:
            err = "operand of unary '&' must be lvalue"
            raise CompilerError(err, self.expr.r)

class Deref(_LExprNode):
    def __init__(self, expr):
        super().__init__()
        self.expr = expr

    def _lvalue(self, il_code, symbol_table, c):
        addr = self.expr.make_il(il_code, symbol_table, c)

        if not addr.ctype.is_pointer():
            err = "operand of unary '*' must have pointer type"
            raise CompilerError(err, self.expr.r)

        return IndirectLValue(addr)

class ArraySubsc(_LExprNode):
    def __init__(self, head, arg):
        super().__init__()
        self.head = head
        self.arg = arg

    def _lvalue(self, il_code, symbol_table, c):
        head_lv = self.head.lvalue(il_code, symbol_table, c)
        arg_lv = self.arg.lvalue(il_code, symbol_table, c)

        matched = False
        if isinstance(head_lv, DirectLValue) and head_lv.ctype().is_array():
            array, arith = self.head, self.arg
            matched = True
        elif isinstance(arg_lv, DirectLValue) and arg_lv.ctype().is_array():
            array, arith = self.arg, self.head
            matched = True

        if matched:
            array_val = array.make_il_raw(il_code, symbol_table, c)
            arith_val = arith.make_il(il_code, symbol_table, c)

            if arith_val.ctype.is_integral():
                return self.array_subsc(array_val, arith_val)

        else:
            head_val = self.head.make_il(il_code, symbol_table, c)
            arg_val = self.arg.make_il(il_code, symbol_table, c)

            if head_val.ctype.is_pointer() and arg_val.ctype.is_integral():
                return self.pointer_subsc(head_val, arg_val, il_code)
            elif arg_val.ctype.is_pointer() and head_val.ctype.is_integral():
                return self.pointer_subsc(head_val, arg_val, il_code)

        descrip = "invalid operand types for array subscriping"
        raise CompilerError(descrip, self.r)

    def pointer_subsc(self, point, arith, il_code):
        if not point.ctype.arg.is_complete():
            err = "cannot subscript pointer to incomplete type"
            raise CompilerError(err, self.r)

        shift = get_size(point.ctype.arg, arith, il_code)
        out = ILValue(point.ctype)
        il_code.add(math_cmds.Add(out, point, shift))
        return IndirectLValue(out)

    def array_subsc(self, array, arith):
        el = array.ctype.el
        return RelativeLValue(el, array, el.size, arith)

class FuncCall(_RExprNode):
    def __init__(self, func, args):
        super().__init__()
        self.func = func
        self.args = args

    def make_il(self, il_code, symbol_table, c):
        func = self.func.make_il(il_code, symbol_table, c)

        if not func.ctype.is_pointer() or not func.ctype.arg.is_function():
            descrip = "called object is not a function pointer"
            raise CompilerError(descrip, self.func.r)
        elif (func.ctype.arg.ret.is_incomplete()
              and not func.ctype.arg.ret.is_void()):
            descrip = "function returns non-void incomplete type"
            raise CompilerError(descrip, self.func.r)

        if func.ctype.arg.no_info:
            final_args = self._get_args_without_prototype(
                il_code, symbol_table, c)
        else:
            final_args = self._get_args_with_prototype(
                func.ctype.arg, il_code, symbol_table, c)

        ret = ILValue(func.ctype.arg.ret)
        il_code.add(control_cmds.Call(func, final_args, ret))
        return ret

    def _get_args_without_prototype(self, il_code, symbol_table, c):
        final_args = []
        for arg_given in self.args:
            arg = arg_given.make_il(il_code, symbol_table, c)

            if arg.ctype.is_arith() and arg.ctype.size < 4:
                arg = set_type(arg, ctypes.integer, il_code)

            final_args.append(arg)
        return final_args

    def _get_args_with_prototype(self, func_ctype, il_code, symbol_table, c):
        arg_types = func_ctype.args

        if len(arg_types) != len(self.args):
            err = ("incorrect number of arguments for function call"
                   f" (expected {len(arg_types)}, have {len(self.args)})")

            if self.args:
                raise CompilerError(err, self.args[-1].r)
            else:
                raise CompilerError(err, self.r)

        final_args = []
        for arg_given, arg_type in zip(self.args, arg_types):
            arg = arg_given.make_il(il_code, symbol_table, c)
            check_cast(arg, arg_type, arg_given.r)
            final_args.append(
                set_type(arg, arg_type.make_unqual(), il_code))
        return final_args
