from codetransformer.code import Code
from codetransformer.instructions import LOAD_CONST, LOAD_FAST


def test_lnotab_roundtrip():
    # DO NOT ADD EXTRA LINES HERE
    def f():  # pragma: no cover
        a = 1
        b = 2
        c = 3
        d = 4
        a, b, c, d

    start_line = test_lnotab_roundtrip.__code__.co_firstlineno + 3
    lines = [start_line + n for n in range(5)]
    code = Code.from_pycode(f.__code__)
    lnotab = code.lnotab
    assert lnotab.keys() == set(lines)
    assert isinstance(lnotab[lines[0]], LOAD_CONST)
    assert lnotab[lines[0]].arg == 1
    assert isinstance(lnotab[lines[1]], LOAD_CONST)
    assert lnotab[lines[1]].arg == 2
    assert isinstance(lnotab[lines[2]], LOAD_CONST)
    assert lnotab[lines[2]].arg == 3
    assert isinstance(lnotab[lines[3]], LOAD_CONST)
    assert lnotab[lines[3]].arg == 4
    assert isinstance(lnotab[lines[4]], LOAD_FAST)
    assert lnotab[lines[4]].arg == 'a'
    assert f.__code__.co_lnotab == code.py_lnotab == code.to_pycode().co_lnotab
