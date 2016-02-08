from pytest import raises
from ..pattern_matched_exceptions import pattern_matched_exceptions


def test_patterns():

    @pattern_matched_exceptions()
    def foo():
        try:
            raise ValueError("bar")
        except TypeError:
            raise
        except ValueError("foo"):
            raise
        except ValueError("bar"):
            return "bar"
        except ValueError("buzz"):
            raise

    assert foo() == "bar"


def test_patterns_bind_name():

    @pattern_matched_exceptions()
    def foo():
        try:
            raise ValueError("bar")
        except ValueError("foo") as e:
            return e.args[0]
        except ValueError("bar") as e:
            return e.args[0]
        except ValueError("buzz") as e:
            return e.args[0]

    assert foo() == "bar"


def test_patterns_reraise():

    @pattern_matched_exceptions()
    def foo():
        try:
            raise ValueError("bar")
        except ValueError("bar"):
            raise

    with raises(ValueError) as err:
        foo()

    assert err.type == ValueError
    assert err.value.args == ('bar',)


def test_normal_exc_match():

    @pattern_matched_exceptions()
    def foo():
        try:
            raise ValueError("bar")
        except ValueError:
            return "matched"
        except ValueError("bar"):
            raise

    assert foo() == "matched"


def test_exc_match_custom_func():

    def match_greater(expr, exc_type, exc_value, exc_traceback):
        return expr > exc_value.args[0]

    @pattern_matched_exceptions(match_greater)
    def foo():
        try:
            raise ValueError(5)
        except 4:
            return 4
        except 5:
            return 5
        except 6:
            return 6

    assert foo() == 6
