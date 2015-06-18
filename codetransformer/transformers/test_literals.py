"""
Tests for literal transformers
"""
from .literals import overloaded_bytes


def test_overloaded_bytes():

    @overloaded_bytes(list)
    def bytes_to_list():
        return ["unicode", b"bytes", 1, 2, 3]

    assert bytes_to_list() == ["unicode", list(b"bytes"), 1, 2, 3]

    @overloaded_bytes(list)
    def bytes_to_list_tuple():
        return "unicode", b"bytes", 1, 2, 3

    assert bytes_to_list_tuple() == ("unicode", list(b"bytes"), 1, 2, 3)
