from dis import dis
from io import StringIO
from itertools import product, chain
import random
import sys

import pytest

from codetransformer.code import Code, Flag, pycode
from codetransformer.instructions import LOAD_CONST, LOAD_FAST, uses_free


@pytest.fixture(scope='module')
def sample_flags(request):
    random.seed(8025816322119661921)  # ayy lmao
    nflags = len(Flag.__members__)
    return tuple(
        dict(zip(Flag.__members__.keys(), case)) for case in chain(
            random.sample(list(product((True, False), repeat=nflags)), 1000),
            [[True] * nflags],
            [[False] * nflags],
        )
    )


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


def test_lnotab_really_dumb_whitespace():
    ns = {}
    exec('def f():\n    lol = True' + '\n' * 1024 + '    wut = True', ns)
    f = ns['f']
    code = Code.from_pycode(f.__code__)
    lines = [2, 1026]
    lnotab = code.lnotab
    assert lnotab.keys() == set(lines)
    assert isinstance(lnotab[lines[0]], LOAD_CONST)
    assert lnotab[lines[0]].arg
    assert isinstance(lnotab[lines[1]], LOAD_CONST)
    assert lnotab[lines[1]].arg
    assert f.__code__.co_lnotab == code.py_lnotab == code.to_pycode().co_lnotab


def test_flag_packing(sample_flags):
    for flags in sample_flags:
        assert Flag.unpack(Flag.pack(**flags)) == flags


def test_flag_unpack_too_big():
    assert all(Flag.unpack(Flag.max).values())
    with pytest.raises(ValueError):
        Flag.unpack(Flag.max + 1)


def test_flag_max():
    assert Flag.pack(
        CO_OPTIMIZED=True,
        CO_NEWLOCALS=True,
        CO_VARARGS=True,
        CO_VARKEYWORDS=True,
        CO_NESTED=True,
        CO_GENERATOR=True,
        CO_NOFREE=True,
        CO_COROUTINE=True,
        CO_ITERABLE_COROUTINE=True,
        CO_FUTURE_DIVISION=True,
        CO_FUTURE_ABSOLUTE_IMPORT=True,
        CO_FUTURE_WITH_STATEMENT=True,
        CO_FUTURE_PRINT_FUNCTION=True,
        CO_FUTURE_UNICODE_LITERALS=True,
        CO_FUTURE_BARRY_AS_BDFL=True,
        CO_FUTURE_GENERATOR_STOP=True,
    ) == Flag.max


def test_flag_max_immutable():
    with pytest.raises(AttributeError):
        Flag.CO_OPTIMIZED.max = None


def test_code_multiple_varargs():
    with pytest.raises(ValueError) as e:
        Code(
            (), (
                '*args',
                '*other',
            ),
        )

    assert str(e.value) == 'cannot specify *args more than once'


def test_code_multiple_kwargs():
    with pytest.raises(ValueError) as e:
        Code(
            (), (
                '**kwargs',
                '**kwargs',
            ),
        )

    assert str(e.value) == 'cannot specify **kwargs more than once'


@pytest.mark.parametrize('cls', uses_free)
def test_dangling_var(cls):
    instr = cls('dangling')
    with pytest.raises(ValueError) as e:
        Code((instr,))

    assert (
        str(e.value) ==
        "Argument to %r is not in cellvars or freevars." % instr
    )


def test_code_flags(sample_flags):
    attr_map = {
        'CO_NESTED': 'is_nested',
        'CO_GENERATOR': 'is_generator',
        'CO_COROUTINE': 'is_coroutine',
        'CO_ITERABLE_COROUTINE': 'is_iterable_coroutine',
        'CO_NEWLOCALS': 'constructs_new_locals',
    }
    for flags in sample_flags:
        if sys.version_info < (3, 6):
            codestring = b'd\x00\x00S'  # return None
        else:
            codestring = b'd\x00S'  # return None

        code = Code.from_pycode(pycode(
            argcount=0,
            kwonlyargcount=0,
            nlocals=2,
            stacksize=0,
            flags=Flag.pack(**flags),
            codestring=codestring,
            constants=(None,),
            names=(),
            varnames=('a', 'b'),
            filename='',
            name='',
            firstlineno=0,
            lnotab=b'',
        ))
        assert code.flags == flags
        for flag, attr in attr_map.items():
            if flags[flag]:
                assert getattr(code, attr)


@pytest.fixture
def abc_code():
    a = LOAD_CONST('a')
    b = LOAD_CONST('b')
    c = LOAD_CONST('c')  # not in instrs
    code = Code((a, b), argnames=())

    return (a, b, c), code


def test_instr_index(abc_code):
    (a, b, c), code = abc_code

    assert code.index(a) == 0
    assert code.index(b) == 1

    with pytest.raises(ValueError):
        code.index(c)


def test_code_contains(abc_code):
    (a, b, c), code = abc_code

    assert a in code
    assert b in code
    assert c not in code


def test_code_dis(capsys):
    @Code.from_pyfunc
    def code():  # pragma: no cover
        a = 1
        b = 2
        return a, b

    buf = StringIO()
    dis(code.to_pycode(), file=buf)
    expected = buf.getvalue()

    code.dis()
    out, err = capsys.readouterr()
    assert not err
    assert out == expected

    buf = StringIO()
    code.dis(file=buf)
    assert buf.getvalue() == expected
