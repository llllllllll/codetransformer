"""
Tests for literal transformers
"""
from collections import OrderedDict
from decimal import Decimal
from itertools import islice

from ..literals import (
    islice_literals,
    overloaded_dicts,
    overloaded_bytes,
    overloaded_floats,
    overloaded_lists,
    overloaded_sets,
    overloaded_slices,
    overloaded_strs,
    overloaded_tuples,
)


def test_overload_thing_with_thing_is_noop():
    test_vals = [('a', 1), ('b', 2), ('c', 3)]
    for t in dict, set, list, tuple:
        expected = t(test_vals)
        f = eval("lambda: %s" % expected)
        overloaded = eval(t.__name__.join(['overloaded_', 's']))(t)(f)
        assert f() == overloaded() == expected


def test_overloaded_dicts():

    @overloaded_dicts(OrderedDict)
    def literal():
        return {'a': 1, 'b': 2, 'c': 3}

    assert literal() == OrderedDict((('a', 1), ('b', 2), ('c', 3)))

    @overloaded_dicts(OrderedDict)
    def comprehension():
        return {k: n for n, k in enumerate('abc', 1)}

    assert comprehension() == OrderedDict((('a', 1), ('b', 2), ('c', 3)))


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

    xformed_const = float_in_set.__code__.co_consts[0]
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

    @overloaded_lists(tuple)
    def frozen_comprehension():
        return [a for a in (1, 2, 3)]

    assert frozen_comprehension() == (1, 2, 3)


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

    def frozen_comprehension():
        return {a for a in 'abc'}

    assert frozen_comprehension() == frozenset('abc')


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

    class C:
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
    def islice_test():
        return map(str, (1, 2, 3, 4))[:2]

    assert isinstance(islice_test(), islice)
    assert tuple(islice_test()) == ('1', '2')
