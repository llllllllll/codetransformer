from sys import exc_info

from enum import (
    IntEnum,
    unique,
)


from ..core import CodeTransformer
from ..instructions import (
    CALL_FUNCTION,
    CALL_FUNCTION_VAR,
    COMPARE_OP,
    LOAD_CONST,
    POP_TOP,
    ROT_TWO,
)
from ..patterns import pattern


@unique
class Comparisons(IntEnum):
    LT = 0
    LE = 1
    EQ = 2
    NE = 3
    GT = 4
    GE = 5
    IN = 6
    NOT_IN = 7
    IS = 8
    IS_NOT = 9
    EXCEPTION_MATCH = 10


def match(match_expr, exc_type, exc_value, exc_traceback):
    """
    Called to determine whether or not an except block should be matched.

    True -> enter except block
    False -> don't enter except block
    """
    # Emulate standard behavior when match_expr is an exception subclass.
    if isinstance(match_expr, type) and issubclass(match_expr, BaseException):
        return issubclass(exc_type, match_expr)

    # Match on type and args when match_expr is an exception instance.
    return (
        issubclass(exc_type, type(match_expr))
        and
        match_expr.args == exc_value.args
    )


class pattern_matched_exceptions(CodeTransformer):
    """
    Allows usage of arbitrary expressions and matching functions in
    `except` blocks.

    When an exception is raised in an except block in a function decorated with
    `pattern_matched_exceptions`, a matching function will be called with the
    block's expression and the three values returned by sys.exc_info().  If the
    matching function returns `True`, we enter the corresponding except-block,
    otherwise we continue to the next block, or re-raise if there are no more
    blocks to check

    Parameters
    ----------
    matcher : function, optional, default is `transformers.exc_patterns.match`.
        A function accepting an expression and the values of sys.exc_info,
        returning True if the exception info "matches" the expression.

        The default behavior is to emulate standard python when the match
        expression is a *subtype* of Exception, and to compare exc.type and
        exc.args when the match expression is an *instance* of Exception.

    Example
    -------
    >>> @pattern_matched_exceptions()
    ... def foo():
    ...     try:
    ...         raise ValueError('bar')
    ...     except ValueError('buzz'):
    ...         return 'buzz'
    ...     except ValueError('bar'):
    ...         return 'bar'
    >>> foo()
    'bar'
    """
    def __init__(self, matcher=match):
        super().__init__()
        self._matcher = matcher

    @pattern(COMPARE_OP)
    def _compare_op(self, instr):
        if instr.arg == Comparisons.EXCEPTION_MATCH:
            yield ROT_TWO().steal(instr)
            yield POP_TOP()
            yield LOAD_CONST(self._matcher)
            yield ROT_TWO()
            yield LOAD_CONST(exc_info)
            yield CALL_FUNCTION(0)
            yield CALL_FUNCTION_VAR(1)
        else:
            yield instr
