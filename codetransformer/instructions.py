from abc import ABCMeta, abstractmethod
from dis import opname, opmap, hasjabs, hasjrel, HAVE_ARGUMENT, stack_effect
from enum import (
    IntEnum,
    unique,
)
from operator import attrgetter
from re import escape

from .patterns import matchable
from .utils.immutable import immutableattr
from .utils.no_default import no_default


__all__ = ['Instruction'] + sorted(list(opmap))

# The instructions that use the co_names tuple.
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
# The instructions that use the co_varnames tuple.
_uses_varname = frozenset({
    'LOAD_FAST',
    'STORE_FAST',
    'DELETE_FAST',
})
# The instructions that use the co_freevars tuple.
_uses_free = frozenset({
    'DELETE_DEREF',
    'LOAD_CLASSDEREF',
    'LOAD_CLOSURE',
    'LOAD_DEREF',
    'STORE_DEREF',
})


def _notimplemented(name):
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
            dict_['_reprname'] = immutableattr(name)
            for attr in ('absjmp', 'have_arg', 'opcode', 'opname', 'reljmp'):
                dict_[attr] = _notimplemented(attr)
            return super().__new__(mcls, name, (object,), dict_)

        if opcode not in opmap.values():
            raise TypeError('Invalid opcode: {}'.format(opcode))

        opname_ = opname[opcode]
        dict_['opname'] = dict_['_reprname'] = immutableattr(opname_)
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
        return self._reprname
    __str__ = __repr__


class Instruction(InstructionMeta._marker, metaclass=InstructionMeta):
    """
    Base class for all instruction types.

    Parameters
    ----------
    arg : any, optional

        The argument for the instruction. This should be the actual value of
        the argument, for example, if this is a
        :class:`~codetransformer.instructions.LOAD_CONST`, use the constant
        value, not the index that would appear in the bytecode.
    """
    _no_arg = no_default

    def __init__(self, arg=_no_arg):
        if self.have_arg and arg is self._no_arg:
            raise TypeError(
                "{} missing 1 required argument: 'arg'".format(self.opname),
            )
        self.arg = self._normalize_arg(arg)
        self._target_of = set()
        self._stolen_by = None  # used for lnotab recalculation

    def __repr__(self):
        arg = self.arg
        return '{op}{arg}'.format(
            op=self.opname,
            arg='(%r)' % arg if self.arg is not self._no_arg else '',
        )

    @staticmethod
    def _normalize_arg(arg):
        return arg

    def steal(self, instr):
        """Steal the jump index off of `instr`.

        This makes anything that would have jumped to `instr` jump to
        this Instruction instead.

        Parameters
        ----------
        instr : Instruction
            The instruction to steal the jump sources from.

        Returns
        -------
        self : Instruction
            The instruction that owns this method.

        Notes
        -----
        This mutates self and ``instr`` inplace.
        """
        instr._stolen_by = self
        for jmp in instr._target_of:
            jmp.arg = self
        self._target_of = instr._target_of
        instr._target_of = set()
        return self

    @classmethod
    def from_opcode(cls, opcode, arg=_no_arg):
        """
        Create an instruction from an opcode and raw argument.

        Parameters
        ----------
        opcode : int
            Opcode for the instruction to create.
        arg : int, optional
            The argument for the instruction.

        Returns
        -------
        intsr : Instruction
            An instance of the instruction named by ``opcode``.
        """
        return type(cls)(opname[opcode], (cls,), {}, opcode=opcode)(arg)

    @property
    def stack_effect(self):
        """
        The net effect of executing this instruction on the interpreter stack.

        Instructions that pop values off the stack have negative stack effect
        equal to the number of popped values.

        Instructions that push values onto the stack have positive stack effect
        equal to the number of popped values.

        Examples
        --------
        - LOAD_{FAST,NAME,GLOBAL,DEREF} push one value onto the stack.
          They have a stack_effect of 1.
        - POP_JUMP_IF_{TRUE,FALSE} always pop one value off the stack.
          They have a stack effect of -1.
        - BINARY_* instructions pop two instructions off the stack, apply a
          binary operator, and push the resulting value onto the stack.
          They have a stack effect of -1 (-2 values consumed + 1 value pushed).
        """
        if self.opcode == NOP.opcode:  # noqa
            # dis.stack_effect is broken here
            return 0

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
        This is a separate concept from instruction identity. Two separate
        instructions can be equivalent without being the same exact instance.
        This means that two equivalent instructions can be at different points
        in the bytecode or be targeted by different jumps.
        """
        return type(self) == type(instr) and self.arg == instr.arg


class _RawArg(int):
    """A class to hold arguments that are not yet initialized so that they
    don't break subclass's type checking code.

    This is used in the first pass of instruction creating in Code.from_pycode.
    """


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
            'argument to %s must be an instruction, got: %r' % (
                type(self).__name__, arg,
            ),
        )
    if isinstance(arg, Instruction):
        arg._target_of.add(self)
    return arg


class CompareOpMeta(InstructionMeta):
    """
    Special-case metaclass for the COMPARE_OP instruction type that provides
    default constructors for the various kinds of comparisons.

    These default constructors are implemented as descriptors so that we can
    write::

        new_compare = COMPARE_OP.LT

    and have it be equivalent to::

        new_compare = COMPARE_OP(COMPARE_OP.comparator.LT)
    """

    @unique
    class comparator(IntEnum):
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

        def __repr__(self):
            return '<COMPARE_OP.%s.%s: %r>' % (
                self.__class__.__name__, self._name_, self._value_,
            )

    class ComparatorDescr:
        """
        A descriptor on the **metaclass** of COMPARE_OP that constructs new
        instances of COMPARE_OP on attribute access.

        Parameters
        ----------
        op : comparator
            The element of the `comparator` enum that this descriptor will
            forward to the COMPARE_OP constructor.
        """
        def __init__(self, op):
            self._op = op

        def __get__(self, instance, owner):
            # Since this descriptor is added to the current metaclass,
            # ``instance`` here is the COMPARE_OP **class**.

            if instance is None:
                # If someone does `CompareOpMeta.LT`, give them back the
                # descriptor object itself.
                return self

            # If someone does `COMPARE_OP.LT`, return a **new instance** of
            # COMPARE_OP.
            # We create new instances so that consumers can take ownership
            # without worrying about other jumps targeting the new instruction.
            return instance(self._op)

    # Dynamically add an instance of ComparatorDescr for each comparator
    # opcode.
    # This is equivalent to doing:
    # LT = ComparatorDescr(comparator.LT)
    # GT = ComparatorDescr(comparator.GT)
    # ...
    for c in comparator:
        locals()[c._name_] = ComparatorDescr(c)
    del c
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
        class_._normalize_arg = staticmethod(class_.comparator)

    if class_.is_jmp:
        class_._normalize_arg = _check_jmp_arg

    class_.__doc__ = (
        """
        See Also
        --------
        dis.{name}
        """.format(name=name),
    )

    del class_


# Clean up the namespace
del name
del globals_
del metamap
del _check_jmp_arg
del _call_repr
del _mk_call_init

# The instructions that use the co_names tuple.
uses_name = frozenset(
    filter(attrgetter('uses_name'), Instruction.__subclasses__()),
)
# The instructions that use the co_varnames tuple.
uses_varname = frozenset(
    filter(attrgetter('uses_varname'), Instruction.__subclasses__()),
)
# The instructions that use the co_freevars tuple.
uses_free = frozenset(
    filter(attrgetter('uses_free'), Instruction.__subclasses__()),
)
