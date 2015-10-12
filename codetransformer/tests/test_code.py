from codetransformer.code import Code


def test_lnotab_roundtrip():
    def f():  # pragma: no cover
        a = 1
        b = 2
        c = 3
        d = 4
        a, b, c, d

    code = Code.from_pycode(f.__code__)
    assert f.__code__.co_lnotab == code.py_lnotab == code.to_pycode().co_lnotab
