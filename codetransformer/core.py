from contextlib import contextmanager
from ctypes import py_object, pythonapi
from itertools import chain
from types import CodeType, FunctionType

from .code import Code
from .instructions import LOAD_CONST


_cell_new = pythonapi.PyCell_New
_cell_new.argtypes = (py_object,)
_cell_new.restype = py_object


def _a_if_not_none(a, b):
    return a if a is not None else b


class NoCodeContext(Exception):
    """Exection raised to indicate that the ``code`` attribute was accessed
    outside of a code context.
    """
    def __init__(self):
        return super().__init__('no code context')


class CodeTransformer(object):
    """A code object transformer, simmilar to the NodeTransformer
    from the ast module.

    Attributes
    ----------
    code
    """
    __slots__ = '_code_stack',

    def __init__(self):
        self._code_stack = []

    def visit_generic(self, instr):
        """Generic visitor, calls the correct visit function for the given
        instruction.

        Parameters
        ----------
        instr : Instruction
            The instruction to visit.

        Yields
        ------
        new_instr : Instruction
            The new instructions to replace this one with.
        """
        if instr is None:
            yield None
            return

        yield from getattr(self, 'visit_' + instr.opname, lambda *a: a)(instr)

    def visit_consts(self, consts):
        """visitor for the co_consts field.

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
            self.visit(const) if isinstance(const, CodeType) else const
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

    visit_name = _id
    visit_names = _id
    visit_varnames = _id
    visit_freevars = _id
    visit_cellvars = _id
    visit_defaults = _id

    del _id

    def visit(self, code, *, name=None, filename=None, lnotab=None):
        """Visit a python object, applying the transforms.

        Parameters
        ----------
        co : Code
            The code object to visit.
        name : str, optional
            The new name for this code object.
        filename : str, optional
            The new filename for this code object.
        lnotab : bytes, optional
            The new lnotab for this code object.

        Returns
        -------
        new_code : Code
            The visited code object.
        """
        # reverse lookups from for constants and names.
        reversed_consts = {}
        reversed_names = {}
        for instr in code:
            if isinstance(instr, LOAD_CONST):
                reversed_consts[instr] = instr.arg
            if instr.uses_name:
                reversed_names[instr] = instr.arg

        instrs, consts = tuple(zip(*reversed_consts.items())) or ((), ())
        for instr, const in zip(instrs, self.visit_consts(consts)):
            instr.arg = const

        instrs, names = tuple(zip(*reversed_names.items())) or ((), ())
        for instr, name in zip(instrs, self.visit_names(names)):
            instr.arg = name

        with self._new_code_context(code):
            return Code(
                chain.from_iterable(map(self.visit_generic, code)),
                code.argnames,
                cellvars=self.visit_cellvars(code.cellvars),
                freevars=self.visit_freevars(code.freevars),
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
            self.visit(Code.from_pycode(f.__code__)).to_pycode(),
            _a_if_not_none(globals_, f.__globals__),
            _a_if_not_none(name, f.__name__),
            _a_if_not_none(defaults, f.__defaults__),
            closure,
        )

    @contextmanager
    def _new_code_context(self, code):
        self._code_stack.append(code)
        try:
            yield
        finally:
            self._code_stack.pop()

    @property
    def code(self):
        """The code object we are currently manipulating.
        """
        try:
            return self._code_stack[-1]
        except IndexError:
            raise NoCodeContext()
