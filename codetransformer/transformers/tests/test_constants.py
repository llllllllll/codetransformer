from codetransformer.code import Code
from codetransformer.instructions import LOAD_CONST, LOAD_NAME
from ..constants import asconstants


def test_global():

    @asconstants(a=1)
    def f():
        return a  # noqa

    assert f() == 1


def test_name():
    new_code = asconstants(a=1).transform(
        Code.from_pycode(
            compile('class C: a', '<string>', 'exec').co_consts[0]),
    )
    assert LOAD_CONST(1) in new_code
    assert LOAD_NAME('a') not in new_code
