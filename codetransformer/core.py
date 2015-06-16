from abc import ABCMeta
from ctypes import py_object, pythonapi, c_int
from dis import Bytecode, opname, opmap, hasjabs, hasjrel, HAVE_ARGUMENT
import operator
from types import CodeType, FunctionType

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

_stack_effect = pythonapi.PyCompile_OpcodeStackEffect
_stack_effect.argtypes = c_int, c_int
_stack_effect.restype = c_int

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
            (_stack_effect(instr.opcode, instr.arg or 0)
             for instr in Instruction.from_bytes(code))),
    )


class CodeTransformer(object, metaclass=ABCMeta):
    """
    A code object transformer, simmilar to the AstTransformer from the ast
    module.
    """
    def __init__(self, optimize=True):
        self._instrs = None
        self._consts = None
        self._optimize = optimize

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
        The index of a constant.
        If `obj` is not already a constant, it will be added to the consts
        and given a new const index.
        """
        try:
            return self._consts[obj][0]
        except KeyError:
            self._consts[obj] = ret = [self._const_idx]
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
            type(self).visit(const) if isinstance(const, CodeType) else const
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
        # WARNING:
        # This is setup in this double assignment way because jump args
        # must backreference their original jump target before any transforms.
        # Don't refactor this into a single pass.
        self._instrs = tuple(_sparse_args([
            Instruction(b.opcode, b.arg) for b in Bytecode(co)
        ]))
        self._instrs = tuple(filter(bool, (
            instr and instr._with_jmp_arg(self) for instr in self._instrs
        )))

        self._consts = consts = {}
        for n, const in enumerate(self.visit_consts(co.co_consts)):
            consts.setdefault(const, []).append(n)

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
        for const, idxs in self._consts.items():
            for idx in idxs:
                consts[idx] = const

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

    def __repr__(self):
        return '<{cls}: {instrs!r}>'.format(
            cls=type(self).__name__,
            instrs=self._instrs,
        )

    def LOAD_CONST(self, const):
        """
        Shortcut for loading a constant value.
        Returns an instruction object.
        """
        return Instruction(ops.LOAD_CONST, self.const_index(const))


class Instruction(object):
    """
    An abstraction of an instruction.
    """
    def __init__(self, opcode, arg=None):
        if opcode >= HAVE_ARGUMENT and arg is None:
            raise TypeError(
                'Instruction {name} expects an argument'.format(
                    name=opname[opcode],
                ),
            )
        self.opcode = opcode
        self.arg = arg
        self.reljmp = False
        self.absjmp = False
        self._stolen_by = None

    def _with_jmp_arg(self, transformer):
        """
        If this is a jump opcode, then convert the arg to the instruction
        to jump to.
        """
        opcode = self.opcode
        if opcode in hasjrel:
            self.arg = transformer[self.index(transformer) + self.arg - 1]
            self.reljmp = True
        elif opcode in hasjabs:
            self.arg = transformer[self.arg]
            self.absjmp = True
        return self

    @property
    def opname(self):
        return opname[self.opcode]

    def to_bytecode(self, transformer):
        """
        Convert an instruction to the bytecode form inside of a transformer.
        This needs a transformer as context because it must know how to
        resolve jumps.
        """
        bs = bytes((self.opcode,))
        arg = self.arg
        if isinstance(arg, Instruction):
            if self.absjmp:
                bs += arg.jmp_index(transformer).to_bytes(2, 'little')
            elif self.reljmp:
                bs += (
                    arg.jmp_index(transformer) - self.index(transformer) + 1
                ).to_bytes(2, 'little')
            else:
                raise ValueError('must be relative or absolute jump')
        elif arg is not None:
            bs += arg.to_bytes(2, 'little')
        return bs

    def index(self, transformer):
        """
        This instruction's index within a transformer.
        """
        return transformer.index(self)

    def jmp_index(self, transformer):
        """
        This instruction's jump index within a transformer.
        This checks to see if it was stolen.
        """
        return (self._stolen_by or self).index(transformer)

    def __repr__(self):
        arg = self.arg
        return '<{cls}: {opname}({arg})>'.format(
            cls=type(self).__name__,
            opname=self.opname,
            arg=': ' + str(arg) if self.arg is not None else '',
        )

    def steal(self, instr):
        """
        Steal the jump index off of `instr`.
        This makes anything that would have jumped to `instr` jump to
        this Instruction instead.
        """
        instr._stolen_by = self
        return self

    @classmethod
    def from_bytes(cls, bs):
        it = iter(bs)
        for b in it:
            try:
                opname[b]
            except KeyError:
                raise ValueError('Invalid opcode: {0!d}'.format(b))

            arg = None
            if b >= HAVE_ARGUMENT:
                arg = int.from_bytes(
                    next(it).to_bytes(1, 'little') +
                    next(it).to_bytes(1, 'little'),
                    'little',
                )

            yield cls(b, arg)
