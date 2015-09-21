"""
Tests for the mutable_locals transformer.
"""
from pytest import raises
from ..mutable_locals import mutable_locals


def test_overwrite():

    @mutable_locals
    def f():
        out = []
        x = 1
        out.append(x)
        locals()['x'] = 2
        out.append(x)
        return out

    assert f() == [1, 2]


def test_create_new():

    @mutable_locals
    def f():
        with raises(NameError):
            y  # noqa
        locals()['y'] = 1
        return y  # noqa. Joke's on you pyflakes, this works!

    assert f() == 1


def test_assign_after_local_write():

    @mutable_locals
    def f():
        out = []
        locals()['x'] = 1
        out.append(1)
        x = 2
        out.append(x)
        return out

    assert f() == [1, 2]


def test_update():

    @mutable_locals
    def f():
        out = []
        x = 1
        out.append(x)
        locals().update({'x': 2, 'y': 3})
        out.append(x)
        out.append(y)  # noqa
        return out

    assert f() == [1, 2, 3]


GLOBAL = 1


def test_global_interactions():

    # No assignments to GLOBAL in the function, which means it should be
    # compiled as a global.
    @mutable_locals
    def f():
        out = []
        out.append(GLOBAL)
        locals().update({'GLOBAL': 2})
        out.append(GLOBAL)  # noqa
        return out

    assert f() == [1, 2]

    # Assignments and dels trigger the Python compiler to treat `GLOBAL` as a
    # local, but we should still be able to use it interchangeably.
    @mutable_locals
    def g():
        out = []
        out.append(GLOBAL)
        locals().update({'GLOBAL': 2})
        out.append(GLOBAL)  # noqa
        GLOBAL = 3
        out.append(GLOBAL)
        del GLOBAL
        out.append(GLOBAL)
        return out

    assert g() == [1, 2, 3, 1]


def test_nonlocal_interactions():
    NONLOCAL = 1

    @mutable_locals
    def f():
        out = []
        out.append(NONLOCAL)
        locals().update({'NONLOCAL': 2})
        out.append(NONLOCAL)  # noqa
        return out

    assert f() == [1, 2]

    @mutable_locals
    def g():
        out = []
        # Python compiles the function in a way that doesn't capture the
        # nonlocal.  We can't, in general, detect that we need to capture, so
        # loading a nonlocal in a function that would normally get compiled
        # with STORE_FASTs or DELETE_FASTs will fail in this case.
        with raises(NameError):
            out.append(NONLOCAL)

        locals().update({'NONLOCAL': 2})
        out.append(NONLOCAL)  # noqa
        NONLOCAL = 3
        out.append(NONLOCAL)
        del NONLOCAL
        with raises(NameError):
            out.append(NONLOCAL)
        return out

    assert g() == [2, 3]


def test_closure_interactions():

    @mutable_locals
    def f():
        out = []
        x = 1

        def g():
            nonlocal x
            out.append(x)
            x += 1
            out.append(x)

        g()  # (1, 2)

        locals()['x'] = 3

        g()  # (3, 4)
        return out

    assert f() == [1, 2, 3, 4]
