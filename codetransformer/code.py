from dis import Bytecode
from enum import IntEnum, unique
from functools import reduce
import operator
from types import CodeType

from .instructions import Instruction, LOAD_CONST
from .utils.functional import scanl


@unique
class Flags(IntEnum):
    CO_OPTIMIZED = 0x0001
    CO_NEWLOCALS = 0x0002
    CO_VARARGS = 0x0004
    CO_VARKEYWORDS = 0x0008
    CO_NESTED = 0x0010
    CO_GENERATOR = 0x0020

    # The CO_NOFREE flag is set if there are no free or cell variables.
    # This information is redundant, but it allows a single flag test
    # to determine whether there is any extra work to be done when the
    # call frame it setup.
    CO_NOFREE = 0x0040

    # The CO_COROUTINE flag is set for coroutine functions
    # (defined with ``async def`` keywords)
    CO_COROUTINE = 0x0080
    CO_ITERABLE_COROUTINE = 0x0100

    # Old values:
    CO_FUTURE_DIVISION = 0x2000
    CO_FUTURE_ABSOLUTE_IMPORT = 0x4000  # Do absolute imports by default.
    CO_FUTURE_WITH_STATEMENT = 0x8000
    CO_FUTURE_PRINT_FUNCTION = 0x10000
    CO_FUTURE_UNICODE_LITERALS = 0x20000

    CO_FUTURE_BARRY_AS_BDFL = 0x40000
    CO_FUTURE_GENERATOR_STOP = 0x80000


def _sparse_args(instrs):
    """Makes the arguments sparse so that instructions live at the correct
    index for the jump resolution step.

    This pads the instruction set with None to mark the bytes occupied by
    arguments.

    Parameters
    ----------
    instrs : iterable of Instruction
        The dense instruction set.

    Yields
    ------
    sparse : Instruction or None
        Yields the instructions, with objects marking the bytes that are used
        for arguments.
    """
    for instr in instrs:
        yield instr
        if instr.have_arg:
            yield None
            yield None


class Code(object):
    """A higher abstraction over python's CodeType.

    See Include/code.h for more information.

    Parameters
    ----------
    instrs : iterable of Instruction
        A sequence of codetransformer Instruction objects.
    argnames : iterable of str, optional
        The names of the arguments to the code object.
    name : str, optional
        The name of this code object.
    filename : str, optional
        The file that this code object came from.
    firstlineno : int, optional
        The first line number of the code in this code object.
    lnotab : bytes, optional
        Bytes (encoding addr<->lineno mapping).
        See Objects/lnotab_notes.txt for details.
    nested : bool, optional
        Is this code object nested in another code object?
    generator : bool, optional
        Is this code object a generator?
    coroutine : bool, optional
        Is this code object a coroutine (async def)?
    iterable_coroutine : bool, optional
        Is this code object a coroutine iterator?

    Attributes
    ----------
    argcount
    argnames
    cellvars
    consts
    filename
    flags
    freevars
    instrs
    is_coroutine
    is_generator
    is_iterable_coroutine
    is_nested
    kwonlyargcount
    lnotab
    name
    names
    sparse_instrs
    stacksize
    varnames
    """
    __slots__ = (
        '_instrs',
        '_argnames',
        '_argcount',
        '_kwonlyargcount',
        '_cellvars',
        '_freevars',
        '_name',
        '_filename',
        '_firstlineno',
        '_lnotab',
        '_flags',
    )

    def __init__(self,
                 instrs,
                 argnames=(),
                 *,
                 cellvars=(),
                 freevars=(),
                 name='<code>',
                 filename='<code>',
                 firstlineno=1,
                 lnotab=b'',
                 nested=False,
                 generator=False,
                 coroutine=False,
                 iterable_coroutine=False):

        instrs = tuple(instrs)  # strictly evaluate any generators.

        # Create the base flags for the function.
        flags = reduce(
            operator.or_, (
                (nested and Flags.CO_NESTED),
                (generator and Flags.CO_GENERATOR),
                (coroutine and Flags.CO_COROUTINE),
                (iterable_coroutine and Flags.CO_ITERABLE_COROUTINE),
            ),
            Flags.CO_NEWLOCALS,
        )

        # The starting varnames (the names of the arguments to the function)
        argcount = [0]
        kwonlyargcount = [0]
        argcounter = argcount  # Which set of args are we currently counting.
        _argnames = []
        append_argname = _argnames.append
        varg = kwarg = None
        for argname in argnames:
            if argname.startswith('**'):
                if kwarg is not None:
                    raise ValueError('cannot specify **kwargs more than once')
                kwarg = argname[2:]
                continue
            elif argname.startswith('*'):
                if varg is not None:
                    raise ValueError('cannot specify *args more than once')
                varg = argname[1:]
                argcounter = kwonlyargcount  # all following args are kwonly.
                continue
            argcounter[0] += 1
            append_argname(argname)

        if varg is not None:
            flags |= Flags.CO_VARARGS
            append_argname(varg)
        if kwarg is not None:
            flags |= Flags.CO_VARKEYWORDS
            append_argname(kwarg)

        if not any(map(operator.attrgetter('uses_free'), instrs)):
            flags |= Flags.CO_NOFREE

        self._instrs = instrs
        self._argnames = tuple(_argnames)
        self._argcount = argcount[0]
        self._kwonlyargcount = kwonlyargcount[0]
        self._cellvars = cellvars
        self._freevars = freevars
        self._name = name
        self._filename = filename
        self._firstlineno = firstlineno
        self._lnotab = lnotab
        self._flags = flags

    @classmethod
    def from_pycode(cls, co):
        """Create a Code object from a python code object.

        Parameters
        ----------
        co : CodeType
            The python code object.

        Returns
        -------
        code : Code
            The codetransformer Code object.
        """
        # Make it sparse to instrs[n] is the instruction at bytecode[n]
        instrs = tuple(
            _sparse_args(
                Instruction.from_opcode(
                    b.opcode,
                    Instruction._no_arg if b.arg is None else b.arg,
                ) for b in Bytecode(co)
            ),
        )
        for idx, instr in enumerate(instrs):
            if instr is None:
                # The sparse value
                continue
            if instr.absjmp:
                instr.arg = instrs[instr.arg]
            elif instr.reljmp:
                instr.arg = instrs[instr.arg + idx + 3]
            elif isinstance(instr, LOAD_CONST):
                instr.arg = co.co_consts[instr.arg]
            elif instr.uses_name:
                instr.arg = co.co_names[instr.arg]
            elif instr.uses_varname:
                instr.arg = co.co_varnames[instr.arg]

        flags = co.co_flags
        has_vargs = bool(flags & Flags.CO_VARARGS)
        has_kwargs = bool(flags & Flags.CO_VARKEYWORDS)

        # Here we convert the varnames format into our argnames format.
        paramnames = co.co_varnames[
            :(co.co_argcount +
              co.co_kwonlyargcount +
              has_vargs +
              has_kwargs)
        ]
        # We start with the positional arguments.
        new_paramnames = list(paramnames[:co.co_argcount])
        # Add *args next.
        if has_vargs:
            new_paramnames.append('*' + paramnames[-1 - has_kwargs])
        # Add positional only arguments next.
        new_paramnames.extend(paramnames[
            co.co_argcount:co.co_argcount + co.co_kwonlyargcount
        ])
        # Add **kwargs last.
        if has_kwargs:
            new_paramnames.append('**' + paramnames[-1])

        return cls(
            filter(bool, instrs),
            argnames=new_paramnames,
            cellvars=co.co_cellvars,
            freevars=co.co_freevars,
            name=co.co_name,
            filename=co.co_filename,
            firstlineno=co.co_firstlineno,
            lnotab=co.co_lnotab,
            nested=flags & Flags.CO_NESTED,
            generator=flags & Flags.CO_GENERATOR,
            coroutine=flags & Flags.CO_COROUTINE,
            iterable_coroutine=flags & Flags.CO_ITERABLE_COROUTINE
        )

    def to_pycode(self):
        """Create a python code object from the more abstract
        codetransfomer.Code object.

        Returns
        -------
        co : CodeType
            The python code object.
        """
        consts = self.consts
        names = self.names
        varnames = self.varnames
        freevars = self.freevars
        cellvars = self.cellvars
        bc = bytearray()
        for instr in self.instrs:
            bc.append(instr.opcode)  # Write the opcode byte.
            if isinstance(instr, LOAD_CONST):
                # Resolve the constant index.
                bc.extend(consts.index(instr.arg).to_bytes(2, 'little'))
            elif instr.uses_name:
                # Resolve the name index.
                bc.extend(names.index(instr.arg).to_bytes(2, 'little'))
            elif instr.uses_varname:
                # Resolve the local variable index.
                bc.extend(varnames.index(instr.arg).to_bytes(2, 'little'))
            elif instr.absjmp:
                # Resolve the absolute jump target.
                bc.extend(
                    self.bytecode_offset(instr.arg).to_bytes(2, 'little'),
                )
            elif instr.reljmp:
                # Resolve the relative jump target.
                # We do this by subtracting the curren't instructions's
                # sparse index from the sparse index of the argument.
                # We then subtract 3 to account for the 3 bytes the
                # current instruction takes up.
                bytecode_offset = self.bytecode_offset
                bc.extend((
                    bytecode_offset(instr.arg) - bytecode_offset(instr) - 3
                ).to_bytes(2, 'little',))
            elif instr.have_arg:
                # Write any other arg here.
                bc.extend(instr.arg.to_bytes(2, 'little'))

        return CodeType(
            self.argcount,
            self.kwonlyargcount,
            len(varnames),
            self.stacksize,
            self.flags,
            bytes(bc),
            consts,
            names,
            varnames,
            self.filename,
            self.name,
            self.firstlineno,
            self.lnotab,
            freevars,
            cellvars,
        )

    @property
    def instrs(self):
        """The instructions in this code object.
        """
        return self._instrs

    @property
    def sparse_instrs(self):
        """The instructions where the index of an instruction
        is the bytecode offset of that instruction.

        None indicates that no instruction is at that offset.
        """
        return tuple(_sparse_args(self.instrs))

    @property
    def argcount(self):
        """The number of arguments this code object accepts.

        This does not include varargs (*args).
        """
        return self._argcount

    @property
    def kwonlyargcount(self):
        """The number of keyword only arguments this code object accepts.

        This does not include varkwargs (**kwargs).
        """
        return self._kwonlyargcount

    @property
    def consts(self):
        """The constants referenced in this code object.
        """
        # We cannot use a set comprehension because consts do not need
        # to be hashable.
        consts = []
        append_const = consts.append
        for instr in self.instrs:
            if isinstance(instr, LOAD_CONST) and instr.arg not in consts:
                append_const(instr.arg)
        return tuple(consts)

    @property
    def names(self):
        """The names referenced in this code object.

        Names come from instructions like LOAD_GLOBAL or STORE_ATTR
        where the name of the global or attribute is needed at runtime.
        """
        # We must sort to preserve the order between calls.
        # The set comprehension is to drop the duplicates.
        return tuple(sorted({
            instr.arg for instr in self.instrs if instr.uses_name
        }))

    @property
    def argnames(self):
        """The names of the arguments to this code object.

        The format is: [args] [vararg] [kwonlyargs] [varkwarg]
        where each group is optional.
        """
        return self._argnames

    @property
    def varnames(self):
        """The names of all of the local variables in this code object.
        """
        # We must sort to preserve the order between calls.
        # The set comprehension is to drop the duplicates.
        return self._argnames + tuple(sorted({
            instr.arg for instr in self.instrs if instr.uses_varname
        }))

    @property
    def cellvars(self):
        """The names of the variables closed over by inner code objects.
        """
        return self._cellvars

    @property
    def freevars(self):
        """The names of the variables this code object has closed over.
        """
        return self._freevars

    @property
    def flags(self):
        """The flags of this code object. This is the bitwise or of
        the enum values defined in the Flag class.
        """
        return self._flags

    @property
    def is_nested(self):
        """Is this a nested code object?
        """
        return bool(self._flags & Flags.CO_NESTED)

    @property
    def is_generator(self):
        """Is this a generator?
        """
        return bool(self._flags & Flags.CO_GENERATOR)

    @property
    def is_coroutine(self):
        """Is this a coroutine defined with async def?

        This is 3.5 and greater.
        """
        return bool(self._flags & Flags.CO_COROUTINE)

    @property
    def is_iterable_coroutine(self):
        """Is this an async iterator defined with __anext__?

        This is 3.5 and greater.
        """
        return bool(self._flags & Flags.CO_ITERABLE_COROUTINE)

    @property
    def filename(self):
        """The filename of this code object.
        """
        return self._filename

    @property
    def name(self):
        """The name of this code object.
        """
        return self._name

    @property
    def firstlineno(self):
        """The first source line from self.filename
        that this code object represents.
        """
        return self._firstlineno

    @property
    def lnotab(self):
        """The encoding of address to lineno mapping.

        See Objects/lnotab_notes.txt for details.
        """
        return self._lnotab

    @property
    def stacksize(self):
        """The maximum amount of stack space used by this code object.
        """
        return max(scanl(
            operator.add,
            0,
            map(operator.attrgetter('stack_effect'), self.instrs),
        ))

    def __getitem__(self, key):
        return self.instrs[key]

    def index(self, instr):
        """Returns the index of instr.

        Parameters
        ----------
        instr : Instruction
            The instruction the check the index of.

        Returns
        -------
        idx : int
            The index of instr in this code object.
        """
        return self._instrs.index(instr)

    def bytecode_offset(self, instr):
        """Returns the offset of instr in the bytecode representation.

        Parameters
        ----------
        instr : Instruction
            The instruction the check the index of.

        Returns
        -------
        idx : int
            The index of instr in this code object in the sparse instructions.
        """
        return self.sparse_instrs.index(instr)

    def __iter__(self):
        return iter(self.instrs)
