``codetransformer 0.1.0``
==============

Bytecode transformers for CPython inspired by the ``ast`` module's
``NodeTransformer``.

``CodeTransformer`` API
-----------------------

``visit_{OP}``
^^^^^^^^^^^^^^

Just like the ``NodeTransformer``, we write ``visit_*`` methods that define how
we act on an instruction.

For example (taken from my lazy_ library):

.. code:: python

    def visit_UNARY_NOT(self, instr):
        """
        Replace the `not` operator to act on the values that the thunks
        represent.
        This makes `not` lazy.
        """
        yield self.LOAD_CONST(_lazy_not).steal(instr)
        # TOS = _lazy_not
        # TOS1 = arg

        yield Instruction(ops.ROT_TWO)
        # TOS = arg
        # TOS1 = _lazy_not

        yield Instruction(ops.CALL_FUNCTION, 1)
        # TOS = _lazy_not(arg)

This visitor is applied to a unary not instruction (``not a``) and replaces it
with code that is like: ``_lazy_not(a)``

These methods will act on any opcode_.

These methods are passed an ``Instruction`` object as the argument.

``visit_{OTHER}``
^^^^^^^^^^^^^^^^^

Code objects also have some data other than their bytecode. We can act on these
things as well.

These methods are passed the type that occupied the given field.

1. ``visit_name``: A transformer for the ``co_names`` field.
2. ``visit_varname``: A transformer for the ``co_varnames`` field.
3. ``visit_freevar``: A transformer for the ``co_freevars`` field.
4. ``visit_cellvar``: A transformer for the ``co_cellvars`` field.
5. ``visit_default``: A transformer for the ``co_defaults`` field.
6. ``visit_const``: A transformer for the ``co_consts`` field.

A note about ``visit_const``: One should be sure to call
``super().visit_const(const)`` inside of their definiton to recursivly apply
your transformer to nested code objects.


``const_index``
^^^^^^^^^^^^^^^

One of the best uses of a bytecode transform is to make something available at
runtime without putting a name in the namespace. We can do this by putting a
new entry in the ``co_consts``.

The ``const_index`` function accepts the value you want to put into the consts
and returns the index as an ``int``. This will create a new entry if needed.

The ``LOAD_CONST`` method of a ``CodeTransformer`` is a shortcut that returns a
``LOAD_CONST`` instruction object with the argument as the index of the object
passed.

``stack_modifier``
^^^^^^^^^^^^^^^^^^

Python code objects need to know the maximum amount of objects that will be on
the stack at one time. ``stack_modifier`` is a property that is added to the
``co_stacksize`` of the input code to return the new maximum stacksize.

Currently there is work being done to generate this from arbitrary code
sequences.

``steal``
^^^^^^^^^

``steal`` is a method of the ``Instruction`` object that steals the jump target
of another instruction. For example, if an instruction ``a`` is jumping to
instruction ``b`` and instruction ``c`` steals ``b``, then ``a`` will jump to
``b``. This is useful when you are replacing an instruction with a transformer
but want to preserve jumps.


.. _lazy: https://github.com/llllllllll/lazy_python
.. _opcode: https://docs.python.org/3.5/library/dis.html#opcode-NOP
