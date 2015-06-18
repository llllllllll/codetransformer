"""
Tests for literal transformers
"""
from .literals import (
    overloaded_bytes,
    overloaded_floats,
)
from decimal import Decimal


def test_overloaded_bytes():

    @overloaded_bytes(list)
    def bytes_to_list():
        return ["unicode", b"bytes", 1, 2, 3]

    assert bytes_to_list() == ["unicode", list(b"bytes"), 1, 2, 3]

    @overloaded_bytes(list)
    def bytes_to_list_tuple():
        return "unicode", b"bytes", 1, 2, 3

    assert bytes_to_list_tuple() == ("unicode", list(b"bytes"), 1, 2, 3)


def test_overloaded_floats():

    @overloaded_floats(Decimal)
    def float_to_decimal():
        return [2, 2.0, 3.5]

    assert float_to_decimal() == [2, Decimal(2.0), Decimal(3.5)]

    @overloaded_floats(Decimal)
    def float_to_decimal_tuple():
        return (2, 2.0, 3.5)

    assert float_to_decimal_tuple() == (2, Decimal(2.0), Decimal(3.5))
