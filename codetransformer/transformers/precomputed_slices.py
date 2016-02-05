"""
An optimizing transformer that pre-computes slices.
"""
from codetransformer.core import CodeTransformer
from codetransformer.instructions import LOAD_CONST, BUILD_SLICE
from codetransformer.patterns import pattern, plus


class precomputed_slices(CodeTransformer):

    @pattern(LOAD_CONST[plus], BUILD_SLICE)
    def make_constant_slice(self, *instrs):
        *loads, build = instrs
        if build.arg != len(loads):
            # There are non-constant loads before the consts:
            # e.g. x[<non-const expr>:1:2]
            yield from instrs

        slice_ = slice(*(instr.arg for instr in loads))
        yield LOAD_CONST(slice_).steal(loads[0])
