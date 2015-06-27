"""
Tests for literal transformers
"""
from decimal import Decimal
from itertools import islice

from ..literals import (
    islice_literals,
    overloaded_bytes,
    overloaded_floats,
    overloaded_lists,
    overloaded_sets,
    overloaded_slices,
    overloaded_strs,
    overloaded_tuples,
)


def test_overloaded_bytes():

    @overloaded_bytes(list)
    def bytes_to_list():
        return ["unicode", b"bytes", 1, 2, 3]

    assert bytes_to_list() == ["unicode", list(b"bytes"), 1, 2, 3]

    @overloaded_bytes(list)
    def bytes_to_list_tuple():
        return "unicode", b"bytes", 1, 2, 3

    assert bytes_to_list_tuple() == ("unicode", list(b"bytes"), 1, 2, 3)

    @overloaded_bytes(int)
    def bytes_in_set(x):
        return x in {b'3'}

    assert not bytes_in_set(b'3')
    assert bytes_in_set(3)

    @overloaded_bytes(bytearray)
    def mutable_bytes():
        return b'123'

    assert isinstance(mutable_bytes(), bytearray)


def test_overloaded_floats():

    @overloaded_floats(Decimal)
    def float_to_decimal():
        return [2, 2.0, 3.5]

    assert float_to_decimal() == [2, Decimal(2.0), Decimal(3.5)]

    @overloaded_floats(Decimal)
    def float_to_decimal_tuple():
        return (2, 2.0, 3.5)

    assert float_to_decimal_tuple() == (2, Decimal(2.0), Decimal(3.5))

    @overloaded_floats(Decimal)
    def float_in_set(x):
        return x in {3.0}

    xformed_const = float_in_set.__code__.co_consts[2]
    assert isinstance(xformed_const, frozenset)
    assert len(xformed_const) == 1
    assert isinstance(tuple(xformed_const)[0], Decimal)
    assert tuple(xformed_const)[0] == Decimal(3.0)


def test_overloaded_lists():

    @overloaded_lists(tuple)
    def frozen_list():
        return [1, 2, 3]

    assert frozen_list() == (1, 2, 3)


    @overloaded_lists(tuple)
    def frozen_in_tuple():
        return [1, 2, 3], [4, 5, 6]

    assert frozen_in_tuple() == ((1, 2, 3), (4, 5, 6))

    @overloaded_lists(tuple)
    def frozen_in_set():
        # lists are not hashable but tuple are.
        return [1, 2, 3] in {[1, 2, 3]}

    assert frozen_in_set()


def test_overloaded_strs():

    @overloaded_strs(tuple)
    def haskell_strs():
        return 'abc'

    assert haskell_strs() == ('a', 'b', 'c')

    @overloaded_strs(tuple)
    def cs_in_tuple():
        return 'abc', 'def'

    assert cs_in_tuple() == (('a', 'b', 'c'), ('d', 'e', 'f'))


def test_overloaded_sets():

    @overloaded_sets(frozenset)
    def f():
        return {'a', 'b', 'c'}

    assert isinstance(f(), frozenset)
    assert f() == frozenset({'a', 'b', 'c'})

    class invertedset(set):
        def __contains__(self, e):
            return not super().__contains__(e)

    @overloaded_sets(invertedset)
    def containment_with_consts():
        # This will create a frozenset FIRST and then we should pull it
        # into an invertedset
        return 'd' in {'e'}

    assert containment_with_consts()


def test_overloaded_tuples():

    @overloaded_tuples(list)
    def nonconst():
        a = 1
        b = 2
        c = 3
        return (a, b, c)

    assert nonconst() == [1, 2, 3]

    @overloaded_tuples(list)
    def const():
        return (1, 2, 3)

    assert const() == [1, 2, 3]


def test_overloaded_slices():

    def concrete_slice(slice_):
        return tuple(range(slice_.start, slice_.stop))[::slice_.step]

    class C(object):
        _idx = None

        def __getitem__(self, idx):
            self._idx = idx
            return idx

    c = C()

    @overloaded_slices(concrete_slice)
    def f():
        return c[1:10:2]

    f()
    assert c._idx == (1, 3, 5, 7, 9)


def test_islice_literals():

    @islice_literals
    def f():
        return map(str, (1, 2, 3, 4))[:2]

    assert isinstance(f(), islice)
    assert tuple(f()) == ('1', '2')
