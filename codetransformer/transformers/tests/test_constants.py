import os
from sys import _getframe
from types import CodeType

import pytest

from codetransformer.code import Code
from ..constants import asconstants


basename = os.path.basename(__file__)


def test_global():

    @asconstants(a=1)
    def f():
        return a  # noqa

    assert f() == 1


def test_name():
    for const in compile(
            'class C:\n    b = a', '<string>', 'exec').co_consts:

        if isinstance(const, CodeType):
            pre_transform = Code.from_pycode(const)
            code = asconstants(a=1).transform(pre_transform)
            break
    else:
        raise AssertionError('There should be a code object in there!')

    ns = {}
    exec(code.to_pycode(), ns)
    assert ns['b'] == 1


def test_closure():
    def f():
        a = 2

        @asconstants(a=1)
        def g():
            return a

        return g

    assert f()() == 1


def test_store():
    with pytest.raises(SyntaxError) as e:
        @asconstants(a=1)
        def f():
            a = 1  # noqa

    line = _getframe().f_lineno - 2
    assert (
        str(e.value) ==
        "can't assign to constant name 'a' (%s, line %d)" % (basename, line)
    )


def test_delete():
    with pytest.raises(SyntaxError) as e:
        @asconstants(a=1)
        def f():
            del a  # noqa

    line = _getframe().f_lineno - 2
    assert (
        str(e.value) ==
        "can't delete constant name 'a' (%s, line %d)" % (basename, line)
    )


def test_argname_overlap():
    with pytest.raises(SyntaxError) as e:
        @asconstants(a=1)
        def f(a):
            pass

    assert str(e.value) == "argument names overlap with constant names: {'a'}"
