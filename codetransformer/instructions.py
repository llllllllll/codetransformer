from abc import ABCMeta, abstractmethod
from dis import opname, opmap, hasjabs, hasjrel, HAVE_ARGUMENT, stack_effect


__all__ = ['Instruction'] + list(opmap)


class _immutableattr(object):
    def __init__(self, op):
        self._op = op

    def __get__(self, instance, owner):
        return self._op


class InstructionMeta(ABCMeta):
    _marker = object()  # sentinel
    _type_cache = {}

    def __init__(self, *args, opcode=None):
        return super().__init__(*args)

    def __new__(mcls, name, bases, dict_, *, opcode=None):
        if len(bases) != 1:
            raise TypeError(
                '{} does not support multiple inheritence'.format(
                    mcls.__name__,
                ),
            )
        if bases[0] is mcls._marker:
            return super().__new__(mcls, name, (object,), dict_)

        if opcode not in opmap.values():
            raise TypeError('Invalid opcode: {}'.format(opcode))

        dict_['opcode'] = _immutableattr(opcode)
        dict_['absjmp'] = _immutableattr(opcode in hasjabs)
        dict_['reljmp'] = _immutableattr(opcode in hasjrel)
        dict_['opname'] = _immutableattr(opname[opcode])

        have_arg = opcode >= HAVE_ARGUMENT
        dict_['have_arg'] = _immutableattr(have_arg)
        mcls._type_cache[opcode] = cls = super().__new__(
            mcls, opname[opcode], bases, dict_,
        )
        return cls


class Instruction(InstructionMeta._marker, metaclass=InstructionMeta):
    """
    An abstraction of an instruction.
    """
    def __init__(self, arg=None):
        if self.have_arg and arg is None:
            raise TypeError(
                "{} missing 1 required argument: 'arg'".format(self.opname),
            )
        self.arg = arg
        self._stolen_by = None

    @property
    @abstractmethod
    def opcode(self):
        raise NotImplementedError('opcode')

    def _with_jmp_arg(self, transformer):
        """
        If this is a jump opcode, then convert the arg to the instruction
        to jump to.
        """
        if self.reljmp:
            self.arg = transformer[self.index(transformer) + self.arg - 1]
        elif self.absjmp:
            self.arg = transformer[self.arg]
        return self

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
        return '{op}{arg}'.format(
            op=self.opname,
            arg='(' + str(arg) + ')' if self.arg is not None else '',
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
                instr = cls.from_opcode(b)
            except TypeError:
                raise ValueError('Invalid opcode: {0!d}'.format(b))

            arg = None
            if instr.have_arg:
                arg = int.from_bytes(
                    next(it).to_bytes(1, 'little') +
                    next(it).to_bytes(1, 'little'),
                    'little',
                )

            yield cls(arg)

    @classmethod
    def from_opcode(cls, opcode):
        return InstructionMeta(
            opname[opcode], (Instruction,), {}, opcode=opcode
        )

    @property
    def stack_effect(self):
        return stack_effect(
            self.opcode, *((self.arg,) if self.have_arg else ())
        )


globals_ = globals()
for name, opcode in opmap.items():
    globals_[name] = Instruction.from_opcode(opcode)
del name
del globals_
