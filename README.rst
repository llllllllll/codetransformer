``codetransformer 0.4``
=========================

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

The following methods act in the form of ``visit_*`` -> ``co_*``, for example,
``visit_name`` acts on the ``co_name`` field.

1. ``visit_name``
2. ``visit_names``
3. ``visit_varnames``
4. ``visit_freevars``
5. ``visit_cellvars``
6. ``visit_defaults``
7. ``visit_consts``

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

``steal``
^^^^^^^^^

``steal`` is a method of the ``Instruction`` object that steals the jump target
of another instruction. For example, if an instruction ``a`` is jumping to
instruction ``b`` and instruction ``c`` steals ``b``, then ``a`` will jump to
``b``. This is useful when you are replacing an instruction with a transformer
but want to preserve jumps.


Applying a Transformer to a Function
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

An instance of ``CodeTransformer`` is callable, accepting a function and
returning a new function with the bytecode modified based on the rules of the
transformer. This allows a ``CodeTransformer`` to be used as a decorator, for
example:

.. code-block:: python

   >>> @mytransformer()
   ... def f(*args):
   ...     ...
   ...     return None


Included Transformers
~~~~~~~~~~~~~~~~~~~~~

``asconstants``
^^^^^^^^^^^^^^^

This decorator will inline objects into a piece of code so that the names do
not need to be looked up at runtime.

Example:

.. code-block:: python

   >>> from codetransformer.transformers import asconstants
   >>> @asconstants(a=1)
   >>> def f():
   ...     return a
   ...
   >>> f()
   1
   >>> a = 5
   >>> f()
   1


This will work in a fresh session where ``a`` is not defined because the name
``a`` will be inlined with the constant value: ``1``. If ``a`` is defined, it
will still be overridden with the new value.

This decorator can also take a variable amount of of builtin names:

.. code-block:: python

   >>> tuple = None
   >>> @asconstants('tuple', 'list')
   ... def f(a):
   ...     if a:
   ...         return tuple
   ...     return list
   ...
   >>> f(True) is tuple
   False


These strings are take as the original builtin values, even if they have been
overridden. These will still be faster than doing a global lookup to find the
object. If no arguments are passed, it means: assume all the builtin names are
constants.

``optimize``
^^^^^^^^^^^^

The CPython peephole optimizer is only run once over the bytecode; however,
sometimes some optimizations do not present themselves until a second pass has
been made. One example of this is De Morgan's Laws. Using the following code as
an example:

.. code-block:: python

   >>> from dis import dis
   >>> def f(a, b):
   ...     if not a and not b: return None
   ...
   >>> dis(f)
   2           0 LOAD_FAST                0 (a)
               3 UNARY_NOT
               4 POP_JUMP_IF_FALSE       18
               7 LOAD_FAST                1 (b)
              10 UNARY_NOT
              11 POP_JUMP_IF_FALSE       18
              14 LOAD_CONST               0 (None)
              17 RETURN_VALUE
         >>   18 LOAD_CONST               0 (None)
              21 RETURN_VALUE
   >>> from codetransformer.transformers import optimize
   >>> @optimize()
   ... def g(a, b):
   ...     if not a and not b: return None
   ...
   >>> dis(g)
   3           0 LOAD_FAST                0 (a)
               3 POP_JUMP_IF_TRUE        16
               6 LOAD_FAST                1 (b)
               9 POP_JUMP_IF_TRUE        16
              12 LOAD_CONST               0 (None)
              15 RETURN_VALUE
         >>   16 LOAD_CONST               0 (None)
              19 RETURN_VALUE


This shows that we can get a pretty decent win for no effort at all.
The ``optimize`` transformer takes a keyword argument: ``passes``, that denotes
the number of passes of the peephole optimizer to run. Just like this
optimization is ironed out on the second pass, there may exist some that
require 2 or 3 passes to work.


.. _lazy: https://github.com/llllllllll/lazy_python
.. _opcode: https://docs.python.org/3.5/library/dis.html#opcode-NOP
