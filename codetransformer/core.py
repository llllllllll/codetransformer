from abc import ABCMeta
from collections import ChainMap
from contextlib import contextmanager
from ctypes import py_object, pythonapi
from dis import Bytecode, opmap, HAVE_ARGUMENT
import operator
from types import CodeType, FunctionType

from .instructions import Instruction, LOAD_CONST

# Opcodes with attribute access.
ops = type(
    'Ops', (dict,), {'__getattr__': lambda self, name: self[name]},
)(opmap)


def _sparse_args(instrs):
    """
    Makes the arguments sparse so that instructions live at the correct
    index for the jump resolution step.
    The `None` instructions will be filtered out.
    """
    for instr in instrs:
        yield instr
        if instr.opcode >= HAVE_ARGUMENT:
            yield None
            yield None


_optimize = pythonapi.PyCode_Optimize
_optimize.argtypes = (py_object,) * 4
_optimize.restype = py_object

_cell_new = pythonapi.PyCell_New
_cell_new.argtypes = (py_object,)
_cell_new.restype = py_object


def _scanl(f, n, ns):
    yield n
    for m in ns:
        n = f(n, m)
        yield n


def _a_if_not_none(a, b):
    return a if a is not None else b


def _calculate_stack_effect(code):
    return max(
        _scanl(
            operator.add,
            0,
            map(
                operator.attrgetter('stack_effect'),
                Instruction.from_bytes(code),
            ),
        ),
    )


class context_free(object):
    """Mark that a method or attribute should not be looked up in the
    code context.

    Parameters
    ----------
    a : any
        The object to put into the dict.
    """
    def __init__(self, a):
        self._a = a

    def __call__(self):
        return self._a


class CodeTransformerMeta(ABCMeta):
    _context_free_types = context_free, FunctionType, staticmethod, classmethod

    def __new__(mcls, name, bases, dict_):
        _context_free = (
            set() | getattr(bases and bases[0], '_context_free', set())
        )
        for k, v in dict_.items():
            if not isinstance(v, mcls._context_free_types):
                continue
            if isinstance(v, context_free):
                dict_[k] = v()
            _context_free.add(k)

        dict_['_context_free'] = _context_free
        return super().__new__(mcls, name, bases, dict_)


getattribute = object.__getattribute__
setattribute = object.__setattr__


class CodeTransformer(object, metaclass=CodeTransformerMeta):
    """
    A code object transformer, simmilar to the AstTransformer from the ast
    module.
    """
    _contexts = context_free(ChainMap())

    def __init__(self, *, optimize=True):
        self._instrs = None
        self._const_indices = None  # Maps id(obj) -> [index in consts tuple]
        self._const_values = None   # Maps id(obj) -> obj
        self._optimize = optimize

    def __getattribute__(self, name):
        if name in type(self)._context_free:
            return getattribute(self, name)

        try:
            return self._contexts[name]
        except KeyError:
            raise AttributeError(name)

    def __setattr__(self, name, value):
        if name in type(self)._context_free:
            setattribute(self, name, value)

        self._contexts[name] = value

    @contextmanager
    def _context(self):
        old_contexts = getattribute(self, '_contexts')
        setattribute(self, '_contexts', old_contexts.new_child())
        try:
            yield
        finally:
            setattribute(self, '_contexts', old_contexts)

    def __getitem__(self, idx):
        return self._instrs[idx]

    def index(self, instr):
        """
        Returns the index of an `Instruction`.
        """
        return self._instrs.index(instr)

    def __iter__(self):
        return iter(self._instrs)

    def const_index(self, obj):
        """
        The index of a constant in our code object's co_consts.
        If `obj` is not already a constant, it will be added to the consts
        and given a new const index.
        """
        obj_id = id(obj)
        try:
            return self._const_indices[obj_id][0]
        except KeyError:
            self._const_indices[obj_id] = ret = [self._const_idx]
            self._const_values[obj_id] = obj
            self._const_idx += 1
            return ret[0]

    def visit_generic(self, instr):
        if instr is None:
            yield None
            return

        yield from getattr(self, 'visit_' + instr.opname, lambda *a: a)(instr)

    def visit_consts(self, consts):
        """
        Override this method to transform the `co_consts` of the code object.
        """
        return tuple(
            self.visit(const) if isinstance(const, CodeType) else const
            for const in consts
        )

    def _id(self, obj):
        """
        Identity function.
        """
        return obj

    visit_name = _id
    visit_names = _id
    visit_varnames = _id
    visit_freevars = _id
    visit_cellvars = _id
    visit_defaults = _id

    del _id

    def visit(self, co, *, name=None):
        """
        Visit a code object, applying the transforms.
        """
        with self._context():
            return self._visit(co, name=name)

    def _visit(self, co, *, name=None):
        # WARNING:
        # This is setup in this double assignment way because jump args
        # must backreference their original jump target before any transforms.
        # Don't refactor this into a single pass.
        self._instrs = tuple(_sparse_args([
            Instruction.from_opcode(b.opcode, b.arg) for b in Bytecode(co)
        ]))
        self._instrs = tuple(filter(bool, (
            instr and instr._with_jmp_arg(self) for instr in self._instrs
        )))

        self._const_indices = const_indices = {}
        self._const_values = const_values = {}
        for n, const in enumerate(self.visit_consts(co.co_consts)):
            const_indices.setdefault(id(const), []).append(n)
            const_values[id(const)] = const

        self._const_idx = len(co.co_consts)  # used for adding new consts.
        self._clean_co = co

        # Apply the transforms.
        self._instrs = tuple(_sparse_args(sum(
            (tuple(self.visit_generic(_instr)) for _instr in self),
            (),
        )))

        code = b''.join(
            (instr or b'') and instr.to_bytecode(self) for instr in self
        )

        consts = [None] * self._const_idx
        for const_id, idxs in self._const_indices.items():
            for idx in idxs:
                consts[idx] = const_values[const_id]

        names = tuple(self.visit_names(co.co_names))

        if self._optimize:
            # Run the optimizer over the new code.
            code = _optimize(
                code,
                consts,
                names,
                co.co_lnotab,
            )

        return CodeType(
            co.co_argcount,
            co.co_kwonlyargcount,
            co.co_nlocals,
            _calculate_stack_effect(code),
            co.co_flags,
            code,
            tuple(consts),
            names,
            tuple(self.visit_varnames(co.co_varnames)),
            co.co_filename,
            self.visit_name(name if name is not None else co.co_name),
            co.co_firstlineno,
            co.co_lnotab,
            tuple(self.visit_freevars(co.co_freevars)),
            tuple(self.visit_cellvars(co.co_cellvars)),
        )

    def __call__(self, f, *,
                 globals_=None, name=None, defaults=None, closure=None):
        # Callable so that we can use CodeTransformers as decorators.
        if closure is not None:
            closure = tuple(map(_cell_new, closure))
        else:
            closure = f.__closure__

        return FunctionType(
            self.visit(f.__code__),
            _a_if_not_none(globals_, f.__globals__),
            _a_if_not_none(name, f.__name__),
            _a_if_not_none(defaults, f.__defaults__),
            closure,
        )

    def LOAD_CONST(self, const):
        """
        Shortcut for loading a constant value.
        Returns an instruction object.
        """
        return LOAD_CONST(self.const_index(const))
