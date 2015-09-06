from types import CodeType

from codetransformer.code import Code
from ..constants import asconstants


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
