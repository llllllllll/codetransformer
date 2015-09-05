from collections import OrderedDict
from contextlib import contextmanager
from ctypes import py_object, pythonapi
from operator import attrgetter
from types import CodeType, FunctionType

from .code import Code
from .instructions import LOAD_CONST, STORE_FAST, LOAD_FAST
from .patterns import (
    boundpattern,
    patterndispatcher,
    NoMatches,
    DEFAULT_STARTCODE,
)


_cell_new = pythonapi.PyCell_New
_cell_new.argtypes = (py_object,)
_cell_new.restype = py_object


def _a_if_not_none(a, b):
    return a if a is not None else b


class NoContext(Exception):
    """Exception raised to indicate that the ``code` or ``startcode``
    attribute was accessed outside of a code context.
    """
    def __init__(self):
        return super().__init__('no context')


class CodeTransformerMeta(type):
    """Meta class for CodeTransformer to collect all of the patterns
    and ensure the class dict is ordered.

    Patterns are created when a method is decorated with
    ``codetransformer.pattern.pattern``
    """
    def __new__(mcls, name, bases, dict_):
        dict_['_patterndispatcher'] = patterndispatcher(
            *(v for v in dict_.values() if isinstance(v, boundpattern))
        )
        return super().__new__(mcls, name, bases, dict_)

    def __prepare__(self, bases):
        return OrderedDict()


class CodeTransformer(metaclass=CodeTransformerMeta):
    """A code object transformer, simmilar to the NodeTransformer
    from the ast module.

    Attributes
    ----------
    code
    """
    __slots__ = '_code_stack', '_startcode_stack'

    def __init__(self):
        self._code_stack = []
        self._startcode_stack = []

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

    def transform(self, code, *, name=None, filename=None, lnotab=None):
        """Transform a codetransformer.Code object applying the transforms.

        Parameters
        ----------
        code : Code
            The code object to transform.
        name : str, optional
            The new name for this code object.
        filename : str, optional
            The new filename for this code object.
        lnotab : bytes, optional
            The new lnotab for this code object.

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
            opcodes = bytes(map(attrgetter('opcode'), code))
            idx = 0  # The current index into the pre-transformed instrs.
            post_transform = []  # The instrs that have been transformed.
            dispatcher = self._patterndispatcher
            while idx < len(code):
                try:
                    processed, nconsumed = dispatcher(
                        opcodes[idx:],
                        code[idx:],
                        self.startcode
                    )
                except NoMatches:
                    post_transform.append(code[idx])
                    idx += 1
                else:
                    post_transform.extend(processed)
                    idx += nconsumed

            return Code(
                post_transform,
                code.argnames,
                cellvars=self.transform_cellvars(code.cellvars),
                freevars=self.transform_freevars(code.freevars),
                name=name if name is not None else code.name,
                filename=filename if filename is not None else code.filename,
                lnotab=lnotab if lnotab is not None else code.lnotab,
                nested=code.is_nested,
                generator=code.is_generator,
                coroutine=code.is_coroutine,
                iterable_coroutine=code.is_iterable_coroutine,
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

    @contextmanager
    def _new_context(self, code):
        self._code_stack.append(code)
        self._startcode_stack.append(DEFAULT_STARTCODE)
        try:
            yield
        finally:
            self._code_stack.pop()
            self._startcode_stack.pop()

    @property
    def code(self):
        """The code object we are currently manipulating.
        """
        try:
            return self._code_stack[-1]
        except IndexError:
            raise NoContext()

    @property
    def startcode(self):
        """The startcode we are currently in.
        """
        try:
            return self._startcode_stack[-1]
        except IndexError:
            raise NoContext()

    def begin(self, startcode):
        """Begin a new startcode.

        Parameters
        ----------
        startcode : any
            The startcode to begin.
        """
        try:
            # "beginning" a new startcode changes the current startcode.
            # Here we are mutating the current context's startcode.
            self._startcode_stack[-1] = startcode
        except IndexError:
            raise NoContext()
