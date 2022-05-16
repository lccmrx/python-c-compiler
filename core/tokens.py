
class TokenKind:

    def __init__(self, text_repr="", kinds=[]):

        self.text_repr = text_repr
        kinds.append(self)
        kinds.sort(key=lambda kind: -len(kind.text_repr))

    def __str__(self):
        return self.text_repr


class Token:
    def __init__(self, kind, content="", rep="", r=None):
        self.kind = kind

        self.content = content if content else str(self.kind)
        self.rep = rep
        self.r = r

    def __repr__(self):
        return self.content

    def __str__(self):
        return self.rep if self.rep else self.content

keyword_kinds = []
symbol_kinds = []

bool_kw = TokenKind("bool", keyword_kinds)
char_kw = TokenKind("string", keyword_kinds)
int_kw = TokenKind("int", keyword_kinds)

plus = TokenKind("+", symbol_kinds)
minus = TokenKind("-", symbol_kinds)
star = TokenKind("*", symbol_kinds)
slash = TokenKind("/", symbol_kinds)
equals = TokenKind("=", symbol_kinds)
mod = TokenKind("%", symbol_kinds)
amp = TokenKind("&", symbol_kinds)

dquote = TokenKind('"', symbol_kinds)
squote = TokenKind("'", symbol_kinds)

l_paren = TokenKind("(", symbol_kinds)
r_paren = TokenKind(")", symbol_kinds)
l_brack = TokenKind("{", symbol_kinds)
r_brack = TokenKind("}", symbol_kinds)
l_sq_brack = TokenKind("[", symbol_kinds)
r_sq_brack = TokenKind("]", symbol_kinds)

comma = TokenKind(",", symbol_kinds)
semicolon = TokenKind(";", symbol_kinds)
dot = TokenKind(".", symbol_kinds)

identifier = TokenKind()
number = TokenKind()
string = TokenKind()
