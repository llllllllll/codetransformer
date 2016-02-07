"""
A transformer implementing ruby-style interpolated strings.
"""
from codetransformer import pattern, CodeTransformer
from codetransformer.instructions import (
    LOAD_CONST,
    LOAD_ATTR,
    CALL_FUNCTION,
    CALL_FUNCTION_KW,
)


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
    """

    def __init__(self, *, transform_bytes=True, transform_str=False):
        super().__init__()
        self._transform_bytes = transform_bytes
        self._transform_str = transform_str

    @pattern(LOAD_CONST)
    def _load_const(self, instr):
        yield instr
        if isinstance(instr.arg, bytes) and self._transform_bytes:
            yield from self._interpolate_bytes()
        elif isinstance(instr.arg, str) and self._transform_str:
            yield from self._interpolate_str()

    def _interpolate_bytes(self):
        """
        Yield instructions to call TOS.decode('utf-8').format(**locals()).
        """
        yield LOAD_ATTR('decode')
        yield LOAD_CONST('utf-8')
        yield CALL_FUNCTION(1)
        yield from self._interpolate_str()

    def _interpolate_str(self):
        """
        Yield instructions to call TOS.format(**locals()).
        """
        yield LOAD_ATTR('format')
        yield LOAD_CONST(locals)
        yield CALL_FUNCTION(0)
        yield CALL_FUNCTION_KW()
