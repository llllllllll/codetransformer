from abc import ABCMeta, abstractmethod
from dis import opname, opmap, hasjabs, hasjrel, HAVE_ARGUMENT, stack_effect
from re import escape


from .patterns import matchable
from .utils.immutable import immutableattr


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
        dict_['opcode'] = immutableattr(opcode)
        absjmp = opcode in hasjabs
        reljmp = opcode in hasjrel
        dict_['absjmp'] = immutableattr(absjmp)
        dict_['reljmp'] = immutableattr(reljmp)
        dict_['is_jmp'] = immutableattr(absjmp or reljmp)
        dict_['opname'] = immutableattr(opname_)
        dict_['uses_name'] = immutableattr(opname_ in _uses_name)
        dict_['uses_varname'] = immutableattr(opname_ in _uses_varname)
        dict_['uses_free'] = immutableattr(opname_ in _uses_free)
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
    _no_arg = object()

    def __init__(self, arg=_no_arg):
        if self.have_arg and arg is self._no_arg:
            raise TypeError(
                "{} missing 1 required argument: 'arg'".format(self.opname),
            )
        self.arg = arg
        self._target_of = set()

    def __repr__(self):
        arg = self.arg
        return '{op}{arg}'.format(
            op=self.opname,
            arg='(' + str(arg) + ')' if self.arg is not self._no_arg else '',
        )

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


@classmethod
def from_argcounts(cls, positional=0, keyword=0):
    return cls(
        int.from_bytes(
            positional.to_bytes(1, 'little') + keyword.to_bytes(1, 'little'),
            'little',
        ),
    )


globals_ = globals()
for name, opcode in opmap.items():
    ns = {}
    # Catch all the different function call kinds.
    if name.startswith('CALL_FUNCTION'):
        ns['from_argcounts'] = from_argcounts
    globals_[name] = InstructionMeta(
        opname[opcode], (Instruction,), ns, opcode=opcode,
    )
del name
del globals_
