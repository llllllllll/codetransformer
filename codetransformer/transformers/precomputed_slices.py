from codetransformer.core import CodeTransformer
from codetransformer.instructions import LOAD_CONST, BUILD_SLICE
from codetransformer.patterns import pattern, plus


class precomputed_slices(CodeTransformer):
    """
    An optimizing transformer that precomputes and inlines slice literals.

    Example
    -------
    >>> from dis import dis
    >>> def first_five(l):
    ...     return l[:5]
    ...
    >>> dis(first_five)  # doctest: +SKIP
      2           0 LOAD_FAST                0 (l)
                  3 LOAD_CONST               0 (None)
                  6 LOAD_CONST               1 (5)
                  9 BUILD_SLICE              2
                 12 BINARY_SUBSCR
                 13 RETURN_VALUE
    >>> dis(precomputed_slices()(first_five))  # doctest: +SKIP
      2           0 LOAD_FAST                0 (l)
                  3 LOAD_CONST               0 (slice(None, 5, None))
                  6 BINARY_SUBSCR
                  7 RETURN_VALUE
    """
    @pattern(LOAD_CONST[plus], BUILD_SLICE)
    def make_constant_slice(self, *instrs):
        *loads, build = instrs
        if build.arg != len(loads):
            # There are non-constant loads before the consts:
            # e.g. x[<non-const expr>:1:2]
            yield from instrs

        slice_ = slice(*(instr.arg for instr in loads))
        yield LOAD_CONST(slice_).steal(loads[0])
