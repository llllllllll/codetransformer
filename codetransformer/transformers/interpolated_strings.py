"""
A transformer implementing ruby-style interpolated strings.
"""
import sys

from codetransformer import pattern, CodeTransformer
from codetransformer.instructions import (
    BUILD_TUPLE,
    LOAD_CONST,
    LOAD_ATTR,
    CALL_FUNCTION,
    CALL_FUNCTION_KW,
    ROT_TWO,
)
from codetransformer.utils.functional import flatten, is_a


class interpolated_strings(CodeTransformer):
    """
    A transformer that interpolates local variables into string literals.

    Parameters
    ----------
    transform_bytes : bool, optional
        Whether to transform bytes literals to interpolated unicode strings.
        Default is True.
    transform_str : bool, optional
        Whether to interpolate values into unicode strings.
        Default is False.

    Example
    -------
    >>> @interpolated_strings()  # doctest: +SKIP
    ... def foo(a, b):
    ...     c = a + b
    ...     return b"{a} + {b} = {c}"
    ...
    >>> foo(1, 2)  # doctest: +SKIP
    '1 + 2 = 3'
    """

    if sys.version_info >= (3, 6):
        def __init__(self, *, transform_bytes=True, transform_str=False):
            raise NotImplementedError(
                '%s is not supported on 3.6 or newer, just use f-strings' %
                type(self).__name__,
            )
    else:
        def __init__(self, *, transform_bytes=True, transform_str=False):
            super().__init__()
            self._transform_bytes = transform_bytes
            self._transform_str = transform_str

    @property
    def types(self):
        """
        Tuple containing types transformed by this transformer.
        """
        out = []
        if self._transform_bytes:
            out.append(bytes)
        if self._transform_str:
            out.append(str)
        return tuple(out)

    @pattern(LOAD_CONST)
    def _load_const(self, instr):
        const = instr.arg

        if isinstance(const, (tuple, frozenset)):
            yield from self._transform_constant_sequence(const)
            return

        if isinstance(const, bytes) and self._transform_bytes:
            yield from self.transform_stringlike(const)
        elif isinstance(const, str) and self._transform_str:
            yield from self.transform_stringlike(const)
        else:
            yield instr

    def _transform_constant_sequence(self, seq):
        """
        Transform a frozenset or tuple.
        """
        should_transform = is_a(self.types)

        if not any(filter(should_transform, flatten(seq))):
            # Tuple doesn't contain any transformable strings. Ignore.
            yield LOAD_CONST(seq)
            return

        for const in seq:
            if should_transform(const):
                yield from self.transform_stringlike(const)
            elif isinstance(const, (tuple, frozenset)):
                yield from self._transform_constant_sequence(const)
            else:
                yield LOAD_CONST(const)

        if isinstance(seq, tuple):
            yield BUILD_TUPLE(len(seq))
        else:
            assert isinstance(seq, frozenset)
            yield BUILD_TUPLE(len(seq))
            yield LOAD_CONST(frozenset)
            yield ROT_TWO()
            yield CALL_FUNCTION(1)

    def transform_stringlike(self, const):
        """
        Yield instructions to process a str or bytes constant.
        """
        yield LOAD_CONST(const)
        if isinstance(const, bytes):
            yield from self.bytes_instrs
        elif isinstance(const, str):
            yield from self.str_instrs

    @property
    def bytes_instrs(self):
        """
        Yield instructions to call TOS.decode('utf-8').format(**locals()).
        """
        yield LOAD_ATTR('decode')
        yield LOAD_CONST('utf-8')
        yield CALL_FUNCTION(1)
        yield from self.str_instrs

    @property
    def str_instrs(self):
        """
        Yield instructions to call TOS.format(**locals()).
        """
        yield LOAD_ATTR('format')
        yield LOAD_CONST(locals)
        yield CALL_FUNCTION(0)
        yield CALL_FUNCTION_KW()
