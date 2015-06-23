from collections import OrderedDict
from decimal import Decimal
from textwrap import dedent

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


def _format_constant_docstring(type_):
    return dedent(
        """
        Transformer that applies a callable to each {type_} constant in the
        transformed code object

        Parameters
        ----------
        astype : callable
            A callable to be applied to {type_} literals.
        """
    ).format(type_=type_.__name__)


class _ConstantTransformerBase(CodeTransformer):

    def __init__(self, f, *, optimize=True):
        self.f = f
        super().__init__(optimize=optimize)

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


def overloaded_constants(type_):
    """
    Factory for constant transformers that apply to a particular type.
    """
    typename = type.__name__
    if not typename.endswith('s'):
        typename += 's'

    return type(
        "overloaded_" + typename,
        (_ConstantTransformerBase,),
        {'_type': type_, '__doc__': _format_constant_docstring(type_)},
    )


overloaded_bytes = overloaded_constants(bytes)
overloaded_floats = overloaded_constants(float)
decimal_literals = overloaded_floats(Decimal)
