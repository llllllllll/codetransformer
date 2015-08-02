import builtins

from ..core import CodeTransformer
from ..instructions import (
    LOAD_CONST,
    LOAD_NAME,
    LOAD_GLOBAL,
)
from ..patterns import pattern


class asconstants(CodeTransformer):
    """
    A code transformer that inlines names as constants.

    >>> from codetransformer.transformers import asconstants
    >>> @asconstants(a=1)
    >>> def f():
    ...     return a
    ...
    >>> f()
    1
    >>> a = 5
    >>> f()
    1
    """
    def __init__(self, *args, **kwargs):
        super().__init__()
        bltins = vars(builtins)
        if not (args or kwargs):
            self._constnames = bltins.copy()
        else:
            self._constnames = constnames = {}
            for arg in args:
                constnames[arg] = bltins[arg]
            overlap = constnames.keys() & kwargs.keys()
            if overlap:
                raise TypeError('Duplicate keys: {!r}'.format(overlap))
            constnames.update(kwargs)

    @pattern(LOAD_NAME | LOAD_GLOBAL)
    def _load_name(self, instr):
        name = instr.arg
        if name not in self._constnames:
            yield instr
            return

        yield LOAD_CONST(self._constnames[name]).steal(instr)
