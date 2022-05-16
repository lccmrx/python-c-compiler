"""This module defines all of the C types recognized by the compiler."""

import copy

from core import tokens as token_kinds


class CType:
    def __init__(self, size, const=False):
        self.size = size
        self.const = const
        self._bool = False
        self._orig = self

    def weak_compat(self, other):
        raise NotImplementedError

    def is_complete(self):
        return False

    def is_incomplete(self):
        """Check whether this is an incomplete type.

        An object type must be either complete or incomplete.
        """
        return False

    def is_object(self):
        """Check whether this is an object type."""
        return False

    def is_arith(self):
        """Check whether this is an arithmetic type."""
        return False

    def is_integral(self):
        """Check whether this is an integral type."""
        return False

    def is_pointer(self):
        """Check whether this is a pointer type."""
        return False

    def is_function(self):
        """Check whether this is a function type."""
        return False

    def is_void(self):
        """Check whether this is a void type."""
        return False

    def is_bool(self):
        """Check whether this is a boolean type."""
        return self._bool

    def is_array(self):
        """Check whether this is an array type."""
        return False

    def is_struct_union(self):
        """Check whether this has struct or union type."""
        return False

    def make_unsigned(self):
        """Return an unsigned version of this type."""
        raise NotImplementedError

    def compatible(self, other):
        """Check whether given `other` C type is compatible with self."""
        return self.weak_compat(other) and self.const == other.const

    def is_scalar(self):
        """Check whether this has scalar type."""
        return self.is_arith() or self.is_pointer()

    def is_const(self):
        """Check whether this is a const type."""
        return self.const

    def make_const(self):
        """Return a const version of this type."""
        const_self = copy.copy(self)
        const_self.const = True
        return const_self

    def make_unqual(self):
        """Return an unqualified version of this type."""
        unqual_self = copy.copy(self)
        unqual_self.const = False
        return unqual_self


class IntegerCType(CType):
    def __init__(self, size, signed):
        """Initialize type."""
        self.signed = signed
        super().__init__(size)

    def weak_compat(self, other):
        """Check whether two types are compatible."""

        # TODO: _orig stuff is hacky...
        # Find a more reliable way to talk about types being equal.
        return (other._orig == self._orig and self.signed == other.signed and
                self.is_bool() == other.is_bool())

    def is_complete(self):
        """Check if this is a complete type."""
        return True

    def is_object(self):
        """Check if this is an object type."""
        return True

    def is_arith(self):
        """Check whether this is an arithmetic type."""
        return True

    def is_integral(self):
        """Check whether this is an integral type."""
        return True

    def make_unsigned(self):
        """Return an unsigned version of this type."""
        unsig_self = copy.copy(self)
        unsig_self.signed = False
        return unsig_self

class PointerCType(CType):
    def __init__(self, arg, const=False):
        """Initialize type."""
        self.arg = arg
        super().__init__(8, const)

    def weak_compat(self, other):
        """Return True iff other is a compatible type to self."""
        return other.is_pointer() and self.arg.compatible(other.arg)

    def is_complete(self):
        """Check if this is a complete type."""
        return True

    def is_pointer(self):
        """Check whether this is a pointer type."""
        return True

    def is_object(self):
        """Check if this is an object type."""
        return True

class VoidCType(CType):

    def __init__(self):
        super().__init__(1)

    def weak_compat(self, other):
        return other.is_void()

    def is_incomplete(self):
        """Check if this is a complete type."""
        return True

    def is_void(self):
        """Check whether this is a void type."""
        return True

    def is_object(self):
        return True

class ArrayCType(CType):
    def __init__(self, el, n):
        """Initialize type."""
        self.el = el
        self.n = n
        super().__init__((n or 1) * self.el.size)

    def compatible(self, other):
        """Return True iff other is a compatible type to self."""
        return (other.is_array() and self.el.compatible(other.el) and
                (self.n is None or other.n is None or self.n == other.n))

    def is_complete(self):
        """Check if this is a complete type."""
        return self.n is not None

    def is_incomplete(self):
        return not self.is_complete()

    def is_object(self):
        """Check if this is an object type."""
        return True

    def is_array(self):
        """Check whether this is an array type."""
        return True

class FunctionCType(CType):
    def __init__(self, args, ret, no_info):
        """Initialize type."""
        self.args = args
        self.ret = ret
        self.no_info = no_info
        super().__init__(1)

    def weak_compat(self, other):
        if not other.is_function():
            return False
        elif not self.ret.compatible(other.ret):
            return False
        elif not self.no_info and not other.no_info:
            if len(self.args) != len(other.args):
                return False
            elif any(not a1.compatible(a2) for a1, a2 in
                     zip(self.args, other.args)):
                return False

        return True

    def is_function(self):
        """Check if this is a function type."""
        return True

bool_t = IntegerCType(1, False)
bool_t._bool = True

char = IntegerCType(1, True)
unsig_char = IntegerCType(1, False)
unsig_char_max = 255

integer = IntegerCType(4, True)
unsig_int = IntegerCType(4, False)
int_max = 2147483647
int_min = -2147483648


simple_types = {token_kinds.bool_kw: bool_t,
                token_kinds.char_kw: char,
                token_kinds.int_kw: integer}
