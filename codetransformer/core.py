from collections import OrderedDict
from contextlib import contextmanager
from ctypes import py_object, pythonapi
from itertools import chain
from types import CodeType, FunctionType
from weakref import WeakKeyDictionary

try:
    import threading
except ImportError:
    import dummy_threading as threading

from .code import Code
from .instructions import LOAD_CONST, STORE_FAST, LOAD_FAST
from .patterns import (
    boundpattern,
    patterndispatcher,
    DEFAULT_STARTCODE,
)
from .utils.instance import instance


_cell_new = pythonapi.PyCell_New
_cell_new.argtypes = (py_object,)
_cell_new.restype = py_object


def _a_if_not_none(a, b):
    return a if a is not None else b


def _new_lnotab(instrs, lnotab):
    """The updated lnotab after the instructions have been transformed.

    Parameters
    ----------
    instrs : iterable[Instruction]
        The new instructions.
    lnotab : dict[Instruction -> int]
        The lnotab for the old code object.

    Returns
    -------
    new_lnotab : dict[Instruction -> int]
        The post transform lnotab.
    """
    return {
        lno: _a_if_not_none(instr._stolen_by, instr)
        for lno, instr in lnotab.items()
    }


class NoContext(Exception):
    """Exception raised to indicate that the ``code` or ``startcode``
    attribute was accessed outside of a code context.
    """
    def __init__(self):
        return super().__init__('no active transformation context')


class Context:
    """Empty object for holding the transformation context.
    """
    def __init__(self, code):
        self.code = code
        self.startcode = DEFAULT_STARTCODE

    def __repr__(self):  # pragma: no cover
        return '<%s: %r>' % (type(self).__name__, self.__dict__)


class CodeTransformerMeta(type):
    """Meta class for CodeTransformer to collect all of the patterns
    and ensure the class dict is ordered.

    Patterns are created when a method is decorated with
    ``codetransformer.pattern.pattern``
    """
    def __new__(mcls, name, bases, dict_):
        dict_['patterndispatcher'] = patterndispatcher(*chain(
            (v for v in dict_.values() if isinstance(v, boundpattern)),
            *(
                d and d.patterns for d in (
                    getattr(b, 'patterndispatcher', ()) for b in bases
                )
            )
        ))
        return super().__new__(mcls, name, bases, dict_)

    def __prepare__(self, bases):
        return OrderedDict()


class CodeTransformer(metaclass=CodeTransformerMeta):
    """A code object transformer, similar to the NodeTransformer
    from the ast module.

    Attributes
    ----------
    code
    """
    __slots__ = '__weakref__',

    def transform_consts(self, consts):
        """transformer for the co_consts field.

        Override this method to transform the `co_consts` of the code object.

        Parameters
        ----------
        consts : tuple
            The co_consts

        Returns
        -------
        new_consts : tuple
            The new constants.
        """
        return tuple(
            self.transform(Code.from_pycode(const)).to_pycode()
            if isinstance(const, CodeType) else
            const
            for const in consts
        )

    def _id(self, obj):
        """Identity function.

        Parameters
        ----------
        obj : any
            The object to return

        Returns
        -------
        obj : any
            The input unchanged
        """
        return obj

    transform_name = _id
    transform_names = _id
    transform_varnames = _id
    transform_freevars = _id
    transform_cellvars = _id
    transform_defaults = _id

    del _id

    def transform(self, code, *, name=None, filename=None):
        """Transform a codetransformer.Code object applying the transforms.

        Parameters
        ----------
        code : Code
            The code object to transform.
        name : str, optional
            The new name for this code object.
        filename : str, optional
            The new filename for this code object.

        Returns
        -------
        new_code : Code
            The transformed code object.
        """
        # reverse lookups from for constants and names.
        reversed_consts = {}
        reversed_names = {}
        reversed_varnames = {}
        for instr in code:
            if isinstance(instr, LOAD_CONST):
                reversed_consts[instr] = instr.arg
            if instr.uses_name:
                reversed_names[instr] = instr.arg
            if isinstance(instr, (STORE_FAST, LOAD_FAST)):
                reversed_varnames[instr] = instr.arg

        instrs, consts = tuple(zip(*reversed_consts.items())) or ((), ())
        for instr, const in zip(instrs, self.transform_consts(consts)):
            instr.arg = const

        instrs, names = tuple(zip(*reversed_names.items())) or ((), ())
        for instr, name_ in zip(instrs, self.transform_names(names)):
            instr.arg = name_

        instrs, varnames = tuple(zip(*reversed_varnames.items())) or ((), ())
        for instr, varname in zip(instrs, self.transform_varnames(varnames)):
            instr.arg = varname

        with self._new_context(code):
            post_transform = self.patterndispatcher(code)

            return Code(
                post_transform,
                code.argnames,
                cellvars=self.transform_cellvars(code.cellvars),
                freevars=self.transform_freevars(code.freevars),
                name=name if name is not None else code.name,
                filename=filename if filename is not None else code.filename,
                firstlineno=code.firstlineno,
                lnotab=_new_lnotab(post_transform, code.lnotab),
                flags=code.flags,
            )

    def __call__(self, f, *,
                 globals_=None, name=None, defaults=None, closure=None):
        # Callable so that we can use CodeTransformers as decorators.
        if closure is not None:
            closure = tuple(map(_cell_new, closure))
        else:
            closure = f.__closure__

        return FunctionType(
            self.transform(Code.from_pycode(f.__code__)).to_pycode(),
            _a_if_not_none(globals_, f.__globals__),
            _a_if_not_none(name, f.__name__),
            _a_if_not_none(defaults, f.__defaults__),
            closure,
        )

    @instance
    class _context_stack(threading.local):
        """Thread safe transformation context stack.

        Each thread will get it's own ``WeakKeyDictionary`` that maps
        instances to a stack of ``Context`` objects. When this descriptor
        is looked up we first try to get the weakkeydict off of the thread
        local storage. If it doesn't exist we make a new map. Then we lookup
        our instance in this map. If it doesn't exist yet create a new stack
        (as an empty list).

        This allows a single instance of ``CodeTransformer`` to be used
        recursively to transform code objects in a thread safe way while
        still being able to use a stateful context.
        """
        def __get__(self, instance, owner):
            try:
                stacks = self._context_stacks
            except AttributeError:
                stacks = self._context_stacks = WeakKeyDictionary()

            if instance is None:
                # when looked up off the class return the current threads
                # context stacks map
                return stacks

            return stacks.setdefault(instance, [])

    @contextmanager
    def _new_context(self, code):
        self._context_stack.append(Context(code))
        try:
            yield
        finally:
            self._context_stack.pop()

    @property
    def context(self):
        """Lookup the current transformation context.

        Raises
        ------
        NoContext
            Raised when there is no active transformation context.
        """
        try:
            return self._context_stack[-1]
        except IndexError:
            raise NoContext()

    @property
    def code(self):
        """The code object we are currently manipulating.
        """
        return self.context.code

    @property
    def startcode(self):
        """The startcode we are currently in.
        """
        return self.context.startcode

    def begin(self, startcode):
        """Begin a new startcode.

        Parameters
        ----------
        startcode : any
            The startcode to begin.
        """
        self.context.startcode = startcode
