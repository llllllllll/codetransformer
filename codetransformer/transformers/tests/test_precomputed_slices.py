from codetransformer.code import Code
from codetransformer.instructions import BUILD_SLICE, LOAD_CONST

from ..precomputed_slices import precomputed_slices


def test_precomputed_slices():

    @precomputed_slices()
    def foo(a):
        return a[1:5]

    l = list(range(10))
    assert foo(l) == l[1:5]
    assert slice(1, 5) in foo.__code__.co_consts

    instrs = Code.from_pyfunc(foo).instrs
    assert LOAD_CONST(slice(1, 5)).equiv(instrs[1])
    assert BUILD_SLICE not in set(map(type, instrs))


def test_precomputed_slices_non_const():

    transformer = precomputed_slices()

    def f(a, b):
        with_non_const = a[b]
        with_mixed = a[1, b]
        return with_non_const, with_mixed

    transformed = transformer(f)

    f_instrs = Code.from_pyfunc(f).instrs
    transformed_instrs = Code.from_pyfunc(transformed).instrs

    for orig, xformed in zip(f_instrs, transformed_instrs):
        assert orig.equiv(xformed)
