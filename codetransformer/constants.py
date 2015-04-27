import builtins

from codetransformer.base import CodeTransformer
from codetransformer.utils import with_code_transformation


class constnames(CodeTransformer):
    def __init__(self, *args, **kwargs):
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

    def visit_names(self, names):
        for name in names:
            if name not in self._constnames:
                yield name
            else:
                yield ''  # We need to keep the other indicies correct.

    def visit_LOAD_NAME(self, instr):
        name = self._clean_co.co_names[instr.arg]
        if name not in self._constnames:
            yield instr
            return

        yield self.LOAD_CONST(self._constnames[name]).steal(instr)

    visit_LOAD_GLOBAL = visit_LOAD_NAME


def asconstants(*args, **kwargs):
    """
    Binds the given names as constants.
    """
    return with_code_transformation(constnames(*args, **kwargs))
