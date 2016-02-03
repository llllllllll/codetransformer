import sys

from ..code import Flag


def paramnames(co):
    """
    Get the parameter names from a pycode object.

    Returns a 4-tuple of (args, kwonlyargs, varargs, varkwargs).
    varargs and varkwargs will be None if the function doesn't take *args or
    **kwargs, respectively.
    """
    flags = co.co_flags
    varnames = co.co_varnames

    argcount, kwonlyargcount = co.co_argcount, co.co_kwonlyargcount
    total = argcount + kwonlyargcount

    args = varnames[:argcount]
    kwonlyargs = varnames[argcount:total]
    varargs, varkwargs = None, None
    if flags & Flag.CO_VARARGS:
        varargs = varnames[total]
        total += 1
    if flags & Flag.CO_VARKEYWORDS:
        varkwargs = varnames[total]

    return args, kwonlyargs, varargs, varkwargs


if sys.version_info[:3] == (3, 4, 3):
    from ._343 import *  # noqa
