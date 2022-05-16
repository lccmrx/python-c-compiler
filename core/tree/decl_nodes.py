class DeclNode:
    pass

class Root(DeclNode):
    def __init__(self, specs, decls, inits=None):
        self.specs = specs
        self.decls = decls

        if inits:
            self.inits = inits
        else:
            self.inits = [None] * len(self.decls)

        super().__init__()

class Pointer(DeclNode):
    def __init__(self, child, const):
        self.child = child
        self.const = const
        super().__init__()

class Array(DeclNode):
    def __init__(self, n, child):
        self.n = n
        self.child = child
        super().__init__()

class Identifier(DeclNode):
    def __init__(self, identifier):
        self.identifier = identifier
        super().__init__()
