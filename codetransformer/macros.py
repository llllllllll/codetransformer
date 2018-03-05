"""Macros for building high-level operations in bytecode.
"""
from . import instructions as instrs
from .assembler import assemble_instructions

Label = instrs.Label


class Macro:
    """TODO
    """
    def assemble(self):
        raise NotImplementedError('assemble')

    def __iter__(self):
        return self.assemble()


class ForLoop(Macro):
    """Macro for assembling for-loops.
    """

    def __init__(self, init, unpack, body, else_body=()):
        self.init = init
        self.unpack = unpack
        self.body = body
        self.else_body = else_body

    def assemble(self):
        top_of_loop = Label('top')
        cleanup = Label('cleanup')
        end = Label('end')

        # Loop setup.
        yield instrs.SETUP_LOOP(end)
        yield from assemble_instructions(self.init)
        yield instrs.GET_ITER()

        # Loop iteration setup.
        yield top_of_loop
        yield instrs.FOR_ITER(cleanup)
        yield from assemble_instructions(self.unpack)

        # Loop body.
        yield from assemble_instructions(self.body)
        yield instrs.JUMP_ABSOLUTE(top_of_loop)

        # Cleanup.
        yield cleanup
        yield instrs.POP_BLOCK()
        yield from self.else_body

        # End of Loop.
        yield end


class IfStatement(Macro):
    """Macro for assembling an if block.
    """
    def __init__(self, test, body, else_body=()):
        self.test = test
        self.body = body
        self.else_body = else_body

    def assemble(self):
        done = Label('done')

        # Setup Test.
        yield from self.test

        if self.else_body:
            # Test.
            start_of_else = Label('start_of_else')
            yield instrs.POP_JUMP_IF_FALSE(start_of_else)

            # Main Branch.
            yield from self.body
            yield instrs.JUMP_FORWARD(done)

            # Else Branch.
            yield start_of_else
            yield from self.else_body
        else:
            # Test.
            yield instrs.POP_JUMP_IF_FALSE(done)

            # Body.
            yield from self.body

        yield done


class PrintVariable(Macro):
    """Macro for printing a local variable by name.

    This is mostly useful for debugging.
    """
    def __init__(self, name):
        self.name = name

    def assemble(self):
        yield instrs.LOAD_FAST(self.name)
        yield instrs.PRINT_EXPR()

    def __repr__(self):
        return "{}({!r})".format(type(self).__name__, self.name)


class PrintStack(Macro):
    """Macro for printing the toptop N values on the stack.
    """
    def __init__(self, n=1):
        self.n = n

    def assemble(self):
        # Pop the top N values off the stack into a tuple.
        yield instrs.BUILD_TUPLE(self.n)
        # Make a copy of the tuple.
        yield instrs.DUP_TOP()
        # Print it. This pops the copy.
        yield instrs.PRINT_EXPR()
        # Unpack the tuple back onto the stack. We call reversed here because
        # UNPACK_SEQUENCE unpacks in reverse.
        yield instrs.LOAD_CONST(reversed)
        yield instrs.ROT_TWO()
        yield instrs.CALL_FUNCTION(1)
        yield instrs.UNPACK_SEQUENCE(self.n)

    def __repr__(self):
        return "{}({!r})".format(type(self).__name__, self.n)


class AssertFail(Macro):
    def __init__(self, message):
        self.message = message

    def assemble(self):
        yield instrs.LOAD_CONST(AssertionError)
        yield instrs.LOAD_CONST(self.message)
        yield instrs.CALL_FUNCTION(1)
        yield instrs.RAISE_VARARGS(1)
