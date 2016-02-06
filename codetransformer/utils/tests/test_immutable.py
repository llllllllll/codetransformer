from inspect import getfullargspec

import pytest

from codetransformer.utils.immutable import immutable


class a(immutable):
    __slots__ = 'a',

    def spec(__self, a):
        pass


class b(immutable):
    __slots__ = 'a', 'b'

    def spec(__self, a, b):
        pass


class c(immutable):
    __slots__ = 'a', 'b', '*c'

    def spec(__self, a, b, *c):
        pass


class d(immutable):
    __slots__ = 'a', 'b', '**c'

    def spec(__self, a, b, **c):
        pass


class e(immutable):
    __slots__ = 'a', 'b', '*', 'c'

    def spec(__self, a, b, *, c):
        pass


class f(immutable):
    __slots__ = 'a', 'b', '*c', 'd'

    def spec(__self, a, b, *c, d):
        pass


class g(immutable, defaults={'a': 1}):
    __slots__ = 'a',

    def spec(__self, a=1):
        pass


class h(immutable, defaults={'b': 2}):
    __slots__ = 'a', 'b'

    def spec(__self, a, b=2):
        pass


class i(immutable, defaults={'a': 1, 'b': 2}):
    __slots__ = 'a', 'b'

    def spec(__self, a=1, b=2):
        pass


class j(immutable, defaults={'c': 3}):
    __slots__ = 'a', 'b', '*', 'c'

    def spec(__self, a, b, *, c=3):
        pass


@pytest.mark.parametrize('cls', (a, b, c, d, e, f, g, h, i, j))
def test_created_signature_single(cls):
    assert getfullargspec(cls) == getfullargspec(cls.spec)


class k(immutable):
    __slots__ = 'a',

    def __init__(self, a):
        pass


class l(immutable):
    __slots__ = 'a',

    def __init__(self, *a):
        pass


class m(immutable):
    __slots__ = 'a',

    def __init__(self, **a):
        pass


class n(immutable):
    __slots__ = 'a',

    def __init__(self, *, a):
        pass


class o(immutable):
    __slots__ = 'a', 'b'

    def __init__(self, a, b=2):
        pass


class p(immutable):
    __slots__ = 'a', 'b'

    def __init__(self, a=1, b=2):
        pass


class q(immutable):
    __slots__ = 'a', 'b'

    def __init__(self, a, *b):
        pass


class r(immutable):
    __slots__ = 'a', 'b'

    def __init__(self, a=1, *b):
        pass


class s(immutable):
    __slots__ = 'a', 'b', 'c'

    def __init__(self, a=1, *b, c):
        pass


class t(immutable):
    __slots__ = 'a', 'b', 'c'

    def __init__(self, a, *b, c=3):
        pass


class u(immutable):
    __slots__ = 'a', 'b', 'c'

    def __init__(self, a=1, *b, c=3):
        pass


class v(immutable):
    __slots__ = 'a', 'b', 'c'

    def __init__(self, a, **b):
        pass


class w(immutable):
    __slots__ = 'a', 'b', 'c'

    def __init__(self, a, b, **c):
        pass


class x(immutable):
    __slots__ = 'a', 'b', 'c'

    def __init__(self, a, *b, **c):
        pass


class y(immutable):
    __slots__ = 'a', 'b', 'c', 'd'

    def __init__(self, a, *b, c, **d):
        pass


class z(immutable):
    __slots__ = 'a', 'b', 'c', 'd'

    def __init__(self, a, *b, c=1, **d):
        pass


@pytest.mark.parametrize('cls', (
    k, l, m, n, o, p, q, r, s, t, u, v, w, x, y, z,
))
def test_preserve_custom_init_signature(cls):
    assert getfullargspec(cls) == getfullargspec(cls.__init__)
