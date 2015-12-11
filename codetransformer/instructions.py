from abc import ABCMeta, abstractmethod
from dis import opname, opmap, hasjabs, hasjrel, HAVE_ARGUMENT, stack_effect
from enum import (
    IntEnum,
    unique,
)
from re import escape

from .patterns import matchable
from .utils.immutable import immutableattr, immutable
from .utils.no_default import no_default


__all__ = ['Instruction'] + list(opmap)

# The opcodes that use the co_names tuple.
_uses_name = frozenset({
    'DELETE_ATTR',
    'DELETE_GLOBAL',
    'DELETE_NAME',
    'IMPORT_FROM',
    'IMPORT_NAME',
    'LOAD_ATTR',
    'LOAD_GLOBAL',
    'LOAD_NAME',
    'STORE_ATTR',
    'STORE_GLOBAL',
    'STORE_NAME',
})
# The opcodes that use the co_varnames tuple.
_uses_varname = frozenset({
    'LOAD_FAST',
    'STORE_FAST',
    'DELETE_FAST',
})
# The opcodes that use the free vars.
_uses_free = frozenset({
    'DELETE_DEREF',
    'LOAD_CLASSDEREF',
    'LOAD_CLOSURE',
    'LOAD_DEREF',
    'STORE_DEREF',
})


def _notimplemented_property(name):
    @property
    @abstractmethod
    def _(self):
        raise NotImplementedError(name)

    return _


@property
def _vartype(self):
    try:
        return self._vartype
    except AttributeError:
        raise AttributeError(
            "vartype is not available on instructions "
            "constructed outside of a Code object."
        )


class InstructionMeta(ABCMeta, matchable):
    _marker = object()  # sentinel
    _type_cache = {}

    def __init__(self, *args, opcode=None):
        return super().__init__(*args)

    def __new__(mcls, name, bases, dict_, *, opcode=None):
        try:
            return mcls._type_cache[opcode]
        except KeyError:
            pass

        if len(bases) != 1:
            raise TypeError(
                '{} does not support multiple inheritance'.format(
                    mcls.__name__,
                ),
            )

        if bases[0] is mcls._marker:
            for name in ('opcode', 'absjmp', 'reljmp', 'opname', 'have_arg'):
                dict_[name] = _notimplemented_property(name)
            return super().__new__(mcls, name, (object,), dict_)

        if opcode not in opmap.values():
            raise TypeError('Invalid opcode: {}'.format(opcode))

        opname_ = opname[opcode]
        dict_['opname'] = immutableattr(opname_)
        dict_['opcode'] = immutableattr(opcode)

        absjmp = opcode in hasjabs
        reljmp = opcode in hasjrel
        dict_['absjmp'] = immutableattr(absjmp)
        dict_['reljmp'] = immutableattr(reljmp)
        dict_['is_jmp'] = immutableattr(absjmp or reljmp)

        dict_['uses_name'] = immutableattr(opname_ in _uses_name)
        dict_['uses_varname'] = immutableattr(opname_ in _uses_varname)
        dict_['uses_free'] = immutableattr(opname_ in _uses_free)
        if opname_ in _uses_free:
            dict_['vartype'] = _vartype

        dict_['have_arg'] = immutableattr(opcode >= HAVE_ARGUMENT)

        cls = mcls._type_cache[opcode] = super().__new__(
            mcls, opname[opcode], bases, dict_,
        )
        return cls

    def mcompile(self):
        return escape(bytes((self.opcode,)))

    def __repr__(self):
        return self.opname
    __str__ = __repr__


class Instruction(InstructionMeta._marker, metaclass=InstructionMeta):
    """An abstraction of an instruction.

    Parameters
    ----------
    arg : any, optional
        The argument for the instruction. This should be the actual value of
        the argument, for example, if this is a ``LOAD_CONST``, use the
        constant value, not the index that would appear in the bytecode.
    """
    _no_arg = no_default

    def __init__(self, arg=_no_arg):
        if self.have_arg and arg is self._no_arg:
            raise TypeError(
                "{} missing 1 required argument: 'arg'".format(self.opname),
            )
        self.arg = self._normalize_arg(arg)
        self._target_of = set()

    def __repr__(self):
        arg = self.arg
        return '{op}{arg}'.format(
            op=self.opname,
            arg='(' + repr(arg) + ')' if self.arg is not self._no_arg else '',
        )

    @staticmethod
    def _normalize_arg(arg):
        return arg

    def steal(self, instr):
        """Steal the jump index off of `instr`.

        This makes anything that would have jumped to `instr` jump to
        this Instruction instead.
        This mutates self and ``instr`` inplace.

        Parameters
        ----------
        instr : Instruction
            The instruction to steal the jump sources from.

        Returns
        -------
        self : Instruction
            The instruction that owns this method.
        """
        for jmp in instr._target_of:
            jmp.arg = self
        self._target_of = instr._target_of
        instr._target_of = set()
        return self

    @classmethod
    def from_bytes(cls, bs):
        """Create a sequence of ``Instruction`` objects from bytes.

        Parameters
        ----------
        bs : bytes
            The bytecode to consume.

        Yields
        ------
        instr : Instruction
            The bytecode converted into instructions.
        """
        it = iter(bs)
        for b in it:
            arg = None
            if b >= HAVE_ARGUMENT:
                arg = int.from_bytes(
                    next(it).to_bytes(1, 'little') +
                    next(it).to_bytes(1, 'little'),
                    'little',
                )

            try:
                yield cls.from_opcode(b, arg)
            except TypeError:
                raise ValueError('Invalid opcode: {}'.format(b))

    @classmethod
    def from_opcode(cls, opcode, arg=_no_arg):
        return type(cls)(opname[opcode], (cls,), {}, opcode=opcode)(arg)

    @property
    def stack_effect(self):
        return stack_effect(
            self.opcode,
            *((self.arg if isinstance(self.arg, int) else 0,)
              if self.have_arg else ())
        )

    def equiv(self, instr):
        """Check equivalence of instructions. This checks against the types
        and the arguments of the instructions

        Parameters
        ----------
        instr : Instruction
            The instruction to check against.

        Returns
        -------
        is_equiv : bool
            If the instructions are equivalent.

        Notes
        -----
        This is a seperate concept from instruction identity. Two seperate
        instructions can be equivalent without being the same exact instance.
        This means that two equivalent instructions can be at different points
        in the bytecode or be targeted by different jumps.
        """
        return type(self) == type(instr) and self.arg == instr.arg


class _RawArg(immutable):
    """A class to hold arguments that are not yet initialized so that they
    don't break subclass's type checking code.

    This is used in the first pass of instruction creating in Code.from_pycode.
    """
    __slots__ = 'value',


def _mk_call_init(class_):
    """Create an __init__ function for a call type instruction.

    Parameters
    ----------
    class_ : type
        The type to bind the function to.

    Returns
    -------
    __init__ : callable
        The __init__ method for the class.
    """
    def __init__(self, packed=no_default, *, positional=0, keyword=0):
        if isinstance(packed, _RawArg):
            packed = packed.value
        if packed is no_default:
            arg = int.from_bytes(bytes((positional, keyword)), 'little')
        elif not positional and not keyword:
            arg = packed
        else:
            raise TypeError('cannot specify packed and unpacked arguments')
        self.positional, self.keyword = arg.to_bytes(2, 'little')
        super(class_, self).__init__(arg)

    return __init__


def _call_repr(self):
    return '%s(positional=%d, keyword=%d)' % (
        type(self).__name__,
        self.positional,
        self.keyword,
    )


def _check_jmp_arg(self, arg):
    if not isinstance(arg, (Instruction, _RawArg)):
        raise TypeError(
            '%s argument must be an instruction' % type(self).__name__,
        )
    if isinstance(arg, Instruction):
        arg._target_of.add(self)
    return arg


class CompareOpMeta(InstructionMeta):
    @unique
    class comparators(IntEnum):
        LT = 0
        LE = 1
        EQ = 2
        NE = 3
        GT = 4
        GE = 5
        IN = 6
        NOT_IN = 7
        IS = 8
        IS_NOT = 9
        EXCEPTION_MATCH = 10

        @classmethod
        def _resolve(cls, value):
            if isinstance(value, cls):
                return value
            if isinstance(value, _RawArg):
                value = value.value
            for _, enum in cls.__members__.items():
                if value == enum:
                    return enum
            raise ValueError('%r is not a valid Comparator' % value)

        def __repr__(self):
            return '<COMPARE_OP.%s.%s: %r>' % (
                self.__class__.__name__, self._name_, self._value_,
            )

    class ComparatorDescr:
        def __init__(self, comparator):
            self._comparator = comparator

        def __get__(self, instance, owner):
            if instance is None:
                return self
            return instance(self._comparator)

    for comparator in comparators:
        locals()[comparator._name_] = ComparatorDescr(comparator)
    del comparator
    del ComparatorDescr


metamap = {
    'COMPARE_OP': CompareOpMeta,
}


globals_ = globals()
for name, opcode in opmap.items():
    globals_[name] = class_ = metamap.get(name, InstructionMeta)(
        opname[opcode],
        (Instruction,), {
            '__module__': __name__,
            '__qualname__': '.'.join((__name__, name)),
        },
        opcode=opcode,
    )
    if name.startswith('CALL_FUNCTION'):
        class_.__init__ = _mk_call_init(class_)
        class_.__repr__ = _call_repr

    if name == 'COMPARE_OP':
        class_._normalize_arg = staticmethod(class_.comparators._resolve)

    if class_.is_jmp:
        class_._normalize_arg = _check_jmp_arg

    del class_


# Clean up the namespace
del name
del globals_
del metamap
del _check_jmp_arg
del _call_repr
del _mk_call_init
