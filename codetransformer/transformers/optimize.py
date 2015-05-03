from types import CodeType

from codetransformer.core import (
    CodeTransformer,
    _optimize,
    _calculate_stack_effect,
)


class optimize(CodeTransformer):
    """
    A simple transformer that runs more passes of the
    peephole optimizer on your code.
    """
    def __init__(self, *, passes=1):
        if passes < 0:
            raise ValueError('Passes must be a positive value')
        self._passes = passes - 1  # We run a pass in CodeTransformer.visit
        super().__init__()

    def visit(self, co, *, name=None):
        code = co.co_code
        consts = list(co.co_consts)
        names = co.co_names
        lnotab = co.co_lnotab
        for n in range(self._passes):
            code = _optimize(code, consts, names, lnotab)

        return super().visit(
            CodeType(
                co.co_argcount,
                co.co_kwonlyargcount,
                co.co_nlocals,
                _calculate_stack_effect(code),
                co.co_flags,
                code,
                tuple(consts),
                names,
                tuple(self.visit_varnames(co.co_varnames)),
                co.co_filename,
                self.visit_name(name if name is not None else co.co_name),
                co.co_firstlineno,
                co.co_lnotab,
                tuple(self.visit_freevars(co.co_freevars)),
                tuple(self.visit_cellvars(co.co_cellvars)),
            ),
            name=name,
        )
