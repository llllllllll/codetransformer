import builtins

from ..core import CodeTransformer
from ..instructions import (
    DELETE_DEREF,
    DELETE_FAST,
    DELETE_GLOBAL,
    DELETE_NAME,
    LOAD_CLASSDEREF,
    LOAD_CONST,
    LOAD_DEREF,
    LOAD_GLOBAL,
    LOAD_NAME,
    STORE_DEREF,
    STORE_FAST,
    STORE_GLOBAL,
    STORE_NAME,
)
from ..patterns import pattern


def _assign_or_del(type_):
    assert type_ in ('assign to', 'delete')

    def handler(self, instr):
        name = instr.arg
        if name not in self._constnames:
            yield instr
            return

        code = self.code
        filename = code.filename
        lno = code.lno_of_instr[instr]
        try:
            with open(filename) as f:
                line = f.readlines()[lno - 1]
        except IOError:
            line = '???'

        raise SyntaxError(
            "can't %s constant name %r" % (type_, name),
            (filename, lno, len(line), line),
        )

    return handler


class asconstants(CodeTransformer):
    """
    A code transformer that inlines names as constants.

    - Positional arguments are interpreted as names of builtins (e.g. ``len``,
      ``print``) to freeze as constants in the decorated function's namespace.

    - Keyword arguments provide additional custom names to freeze as constants.

    - If invoked with no positional or keyword arguments, ``asconstants``
      inlines all names in ``builtins``.

    Parameters
    ----------
    \*builtin_names
        Names of builtins to freeze as constants.
    \*\*kwargs
        Additional key-value pairs to bind as constants.

    Examples
    --------
    Freezing Builtins:

    >>> from codetransformer.transformers import asconstants
    >>>
    >>> @asconstants('len')
    ... def with_asconstants(x):
    ...     return len(x) * 2
    ...
    >>> def without_asconstants(x):
    ...     return len(x) * 2
    ...
    >>> len = lambda x: 0
    >>> with_asconstants([1, 2, 3])
    6
    >>> without_asconstants([1, 2, 3])
    0

    Adding Custom Constants:

    >>> @asconstants(a=1)
    ... def f():
    ...     return a
    ...
    >>> f()
    1
    >>> a = 5
    >>> f()
    1
    """
    def __init__(self, *builtin_names, **kwargs):
        super().__init__()
        bltins = vars(builtins)
        if not (builtin_names or kwargs):
            self._constnames = bltins.copy()
        else:
            self._constnames = constnames = {}
            for arg in builtin_names:
                constnames[arg] = bltins[arg]
            overlap = constnames.keys() & kwargs.keys()
            if overlap:
                raise TypeError('Duplicate keys: {!r}'.format(overlap))
            constnames.update(kwargs)

    def transform(self, code, **kwargs):
        overlap = self._constnames.keys() & set(code.argnames)
        if overlap:
            raise SyntaxError(
                'argument names overlap with constant names: %r' % overlap,
            )
        return super().transform(code, **kwargs)

    @pattern(LOAD_NAME | LOAD_GLOBAL | LOAD_DEREF | LOAD_CLASSDEREF)
    def _load_name(self, instr):
        name = instr.arg
        if name not in self._constnames:
            yield instr
            return

        yield LOAD_CONST(self._constnames[name]).steal(instr)

    _store = pattern(
        STORE_NAME | STORE_GLOBAL | STORE_DEREF | STORE_FAST,
    )(_assign_or_del('assign to'))
    _delete = pattern(
        DELETE_NAME | DELETE_GLOBAL | DELETE_DEREF | DELETE_FAST,
    )(_assign_or_del('delete'))
