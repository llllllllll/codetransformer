from ..add2mul import add2mul


def test_add2mul():

    @add2mul()
    def foo(a, b):
        return (a + b + 2) - 1

    assert foo(1, 2) == 3
    assert foo(2, 2) == 7
