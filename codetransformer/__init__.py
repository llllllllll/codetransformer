from .code import Code, Flag
from .core import CodeTransformer
from . patterns import (
    matchany,
    not_,
    option,
    or_,
    pattern,
    plus,
    seq,
    var,
)
from . import instructions
from . import transformers
from .utils.pretty import a, d, display, pprint_ast, pformat_ast
from ._version import get_versions


__version__ = get_versions()['version']
del get_versions


def load_ipython_extension(ipython):  # pragma: no cover

    def dis_magic(line, cell=None):
        if cell is None:
            return d(line)
        return d(cell)
    ipython.register_magic_function(dis_magic, 'line_cell', 'dis')

    def ast_magic(line, cell=None):
        if cell is None:
            return a(line)
        return a(cell)
    ipython.register_magic_function(ast_magic, 'line_cell', 'ast')


__all__ = [
    'a',
    'd',
    'display',
    'Code',
    'CodeTransformer',
    'Flag',
    'instructions',
    'matchany',
    'not_',
    'option',
    'or_',
    'pattern',
    'pattern',
    'plus',
    'pformat_ast',
    'pprint_ast',
    'seq',
    'var',
    'transformers',
]
