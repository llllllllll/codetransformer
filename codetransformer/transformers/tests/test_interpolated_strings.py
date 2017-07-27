import sys

import pytest

from ..interpolated_strings import interpolated_strings


pytestmark = pytest.mark.skipif(
    sys.version_info >= (3, 6),
    reason='interpolated_strings is deprecated, just use f-strings',
)


def test_interpolated_bytes():

    @interpolated_strings(transform_bytes=True)
    def enabled(a, b, c):
        return b"{a} {b!r} {c}"

    assert enabled(1, 2, 3) == "{a} {b!r} {c}".format(a=1, b=2, c=3)

    @interpolated_strings()
    def default(a, b, c):
        return b"{a} {b!r} {c}"

    assert default(1, 2, 3) == "{a} {b!r} {c}".format(a=1, b=2, c=3)

    @interpolated_strings(transform_bytes=False)
    def disabled(a, b, c):
        return b"{a} {b!r} {c}"

    assert disabled(1, 2, 3) == b"{a} {b!r} {c}"


def test_interpolated_str():

    @interpolated_strings(transform_str=True)
    def enabled(a, b, c):
        return "{a} {b!r} {c}"

    assert enabled(1, 2, 3) == "{a} {b!r} {c}".format(a=1, b=2, c=3)

    @interpolated_strings()
    def default(a, b, c):
        return "{a} {b!r} {c}"

    assert default(1, 2, 3) == "{a} {b!r} {c}"

    @interpolated_strings(transform_bytes=False)
    def disabled(a, b, c):
        return "{a} {b!r} {c}"

    assert disabled(1, 2, 3) == "{a} {b!r} {c}"


def test_no_cross_pollination():

    @interpolated_strings(transform_bytes=True)
    def ignore_str(a):
        u = "{a}"
        b = b"{a}"
        return u, b

    assert ignore_str(1) == ("{a}", "1")

    @interpolated_strings(transform_bytes=False, transform_str=True)
    def ignore_bytes(a):
        u = "{a}"
        b = b"{a}"
        return u, b

    assert ignore_bytes(1) == ("1", b"{a}")


def test_string_in_nested_const():

    @interpolated_strings(transform_str=True)
    def foo(a, b):
        return ("{a}", (("{b}",), "{a} {b}"), (1, 2))

    assert foo(1, 2) == ("1", (("2",), "1 2"), (1, 2))

    @interpolated_strings(transform_str=True)
    def bar(a):
        return "1" in {"{a}"}

    assert bar(1)
    assert not bar(2)
