"""
Mutable Locals transformer.
"""
import ctypes
from functools import reduce
from operator import or_
import sys

from ..instructions import (
    CALL_FUNCTION,
    DELETE_FAST,
    DELETE_NAME,
    LOAD_CLASSDEREF,
    LOAD_CLOSURE,
    LOAD_CONST,
    LOAD_DEREF,
    LOAD_FAST,
    LOAD_GLOBAL,
    LOAD_NAME,
    STORE_DEREF,
    STORE_FAST,
    STORE_NAME,
)
from ..core import CodeTransformer
from ..patterns import pattern
from ..utils.instance import instance

from ._mutable_locals import set_locals_dict

c_zero = ctypes.c_int(0)


PyFrame_LocalsToFast = ctypes.pythonapi.PyFrame_LocalsToFast
PyFrame_LocalsToFast.argtypes = [ctypes.py_object]


class LocalsProxy(dict):
    """
    A dict subclass that synchronizes with a `frame` object when mutated

    Parameters
    ---------
    frame : frame
        The stack frame whose locals the dict should proxy.
    **kwargs
        Initial dictionary values.
    """
    __slots__ = ('_frame',)

    def __init__(self, frame, **kwargs):
        dict.__init__(self, **kwargs)
        self._frame = frame

    def __setitem__(self, key, value):
        dict.__setitem__(self, key, value)
        PyFrame_LocalsToFast(self._frame, c_zero)

    def __delitem__(self, key):
        dict.__delitem__(self, key)
        PyFrame_LocalsToFast(self._frame, c_zero)

    def update(self, other):
        dict.update(self, other)
        PyFrame_LocalsToFast(self._frame, c_zero)


def _override_locals():
    """
    Override f_locals of the calling frame with a LocalsProxy to that frame.
    """
    prev_frame = sys._getframe(1)
    set_locals_dict(prev_frame, LocalsProxy(prev_frame))


LOADS = reduce(
    or_,
    (
        LOAD_FAST,
        LOAD_GLOBAL,
        LOAD_DEREF,
    )
)


@instance
class mutable_locals(CodeTransformer):
    """
    Make assignments into the dictionary returned by `locals()` persist in a
    function's locals.

    Example
    -------
    >>> @mutable_locals
    ... def foo():
            x = 1
    ...     print(x)
    ...     locals()['x'] = 2
    ...     print(x)
    ...     locals().update({'x': 3, 'y': 4})
    ...     print(x, y)
    ...
    >>> foo()
    1
    2
    3, 4
    """

    @pattern(..., startcodes={0})
    def _first(self, instr):
        yield LOAD_CONST(_override_locals)
        yield CALL_FUNCTION(0)
        yield instr
        self.begin("tail")

    @pattern(LOADS, startcodes={0})
    def _load_first(self, instr):
        *init, last = self._first(instr)
        yield from init
        yield from self._load(last)

    @pattern(LOAD_CLOSURE)
    def _load_closure(self, instr):
        import pdb; pdb.set_trace()
        yield instr

    @pattern(LOADS, startcodes={"tail"})
    def _load(self, instr):
        if isinstance(instr, LOAD_DEREF):
            yield LOAD_CLASSDEREF(instr.arg).steal(instr)
        else:
            yield LOAD_NAME(instr.arg).steal(instr)

    @pattern(STORE_DEREF, startcodes={"tail"})
    def _store_deref(self, instr):
        yield STORE_NAME(instr.arg).steal(instr)

    @pattern(STORE_FAST, startcodes={"tail"})
    def _store_fast(self, instr):
        yield STORE_NAME(instr.arg).steal(instr)

    @pattern(DELETE_FAST, startcodes={"tail"})
    def _delete_fast(self, instr):
        yield DELETE_NAME(instr.arg).steal(instr)
