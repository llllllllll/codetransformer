from collections import OrderedDict

from codetransformer import CodeTransformer, ops, Instruction


class ordereddict_literals(CodeTransformer):
    def visit_BUILD_MAP(self, instr):
        yield self.LOAD_CONST(OrderedDict).steal(instr)
        # TOS  = OrderedDict

        yield Instruction(ops.CALL_FUNCTION, 0)
        # TOS  = m = OrderedDict()

        yield from (Instruction(ops.DUP_TOP),) * instr.arg
        # TOS  = m
        # ...
        # TOS[instr.arg] = m

    def visit_STORE_MAP(self, instr):
        # TOS  = k
        # TOS1 = v
        # TOS2 = m
        # TOS3 = m

        yield Instruction(ops.ROT_THREE).steal(instr)
        # TOS  = v
        # TOS1 = m
        # TOS2 = k
        # TOS3 = m

        yield Instruction(ops.ROT_THREE)
        # TOS  = m
        # TOS1 = k
        # TOS2 = v
        # TOS3 = m

        yield Instruction(ops.ROT_TWO)
        # TOS  = k
        # TOS1 = m
        # TOS2 = v
        # TOS3 = m

        yield Instruction(ops.STORE_SUBSCR)
        # TOS  = m


class OverloadedLiteralTransformer(CodeTransformer):

    def __init__(self, f):
        self.f = f
        super().__init__()

    def visit_consts(self, consts):
        return super().visit_consts(
            tuple(
                # This is all one expression.
                frozenset(self.visit_consts(tuple(const)))
                if isinstance(const, frozenset)
                else self.visit_consts(const)
                if isinstance(const, tuple)
                else self.f(const)
                if isinstance(const, self._type)
                else const
                ###
                for const in consts
            )
        )


class overloaded_bytes(OverloadedLiteralTransformer):
    """
    Decorator that applies a callable to each bytes literal in the decorated
    function.

    Parameters
    ----------
    f : callable
        A callable to be applied to each bytes literal in the decorated
        function.
    """
    _type = bytes


class overloaded_floats(OverloadedLiteralTransformer):
    """
    Decorator that applies a callable to each float literal in the decorated
    function.

    Parameters
    ----------
    f : callable
        A callable to be applied to each float literal in the decorated
        function.
    """
    _type = float
