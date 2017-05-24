``codetransformer``
===================

|build status| |documentation|

Bytecode transformers for CPython inspired by the ``ast`` module's
``NodeTransformer``.

What is ``codetransformer``?
----------------------------

``codetransformer`` is a library that allows us to work with CPython's bytecode
representation at runtime. ``codetransformer`` provides a level of abstraction
between the programmer and the raw bytes read by the eval loop so that we can
more easily inspect and modify bytecode.

``codetransformer`` is motivated by the need to override parts of the python
language that are not already hooked into through data model methods. For example:

* Override the ``is`` and ``not`` operators.
* Custom data structure literals.
* Syntax features that cannot be represented with valid python AST or source.
* Run without a modified CPython interpreter.

``codetransformer`` was originally developed as part of lazy_ to implement
the transformations needed to override the code objects at runtime.

Example Uses
------------

Overloading Literals
~~~~~~~~~~~~~~~~~~~~

While this can be done as an AST transformation, we will often need to execute
the constructor for the literal multiple times. Also, we need to be sure that
any additional names required to run our code are provided when we run. With
``codetransformer``, we can pre compute our new literals and emit code that is
as fast as loading our unmodified literals without requiring any additional
names be available implicitly.

In the following block we demonstrate overloading dictionary syntax to result in
``collections.OrderedDict`` objects. ``OrderedDict`` is like a ``dict``;
however, the order of the keys is preserved.

.. code-block:: python

   >>> from codetransformer.transformers.literals import ordereddict_literals
   >>> @ordereddict_literals
   ... def f():
   ...     return {'a': 1, 'b': 2, 'c': 3}
   >>> f()
   OrderedDict([('a', 1), ('b', 2), ('c', 3)])

This also supports dictionary comprehensions:

.. code-block:: python

   >>> @ordereddict_literals
   ... def f():
   ...     return {k: v for k, v in zip('abc', (1, 2, 3))}
   >>> f()
   OrderedDict([('a', 1), ('b', 2), ('c', 3)])

The next block overrides ``float`` literals with ``decimal.Decimal``
objects. These objects support arbitrary precision arithmetic.

.. code-block:: python

   >>> from codetransformer.transformers.literals import decimal_literals
   >>> @decimal_literals
   ... def f():
   ...     return 1.5
   >>> f()
   Decimal('1.5')

Pattern Matched Exceptions
~~~~~~~~~~~~~~~~~~~~~~~~~~

Pattern matched exceptions are a good example of a ``CodeTransformer`` that
would be very complicated to implement at the AST level. This transformation
extends the ``try/except`` syntax to accept instances of ``BaseException`` as
well subclasses of ``BaseException``. When excepting an instance, the ``args``
of the exception will be compared for equality to determine which exception
handler should be invoked. For example:

.. code-block:: python

   >>> @pattern_matched_exceptions()
   ... def foo():
   ...     try:
   ...         raise ValueError('bar')
   ...     except ValueError('buzz'):
   ...         return 'buzz'
   ...     except ValueError('bar'):
   ...         return 'bar'
   >>> foo()
   'bar'

This function raises an instance of ``ValueError`` and attempts to catch it. The
first check looks for instances of ``ValueError`` that were constructed with an
argument of ``'buzz'``. Because our custom exception is raised with ``'bar'``,
these are not equal and we do not enter this handler. The next handler looks for
``ValueError('bar')`` which does match the exception we raised. We then enter
this block and normal python rules take over.

We may also pass their own exception matching function:

.. code-block:: python

    >>> def match_greater(match_expr, exc_type, exc_value, exc_traceback):
    ...     return math_expr > exc_value.args[0]

    >>> @pattern_matched_exceptions(match_greater)
    ... def foo():
    ...     try:
    ...         raise ValueError(5)
    ...     except 4:
    ...         return 4
    ...     except 5:
    ...         return 5
    ...     except 6:
    ...         return 6
    >>> foo()
    6

This matches on when the match expression is greater in value than the first
argument of any exception type that is raised. This particular behavior would be
very hard to mimic through AST level transformations.

Core Abstractions
-----------------

The three core abstractions of ``codetransformer`` are:

1. The ``Instruction`` object which represents an opcode_ which may be paired
   with some argument.
2. The ``Code`` object which represents a collection of ``Instruction``\s.
3. The ``CodeTransformer`` object which represents a set of rules for
   manipulating ``Code`` objects.

Instructions
~~~~~~~~~~~~

The ``Instruction`` object represents an atomic operation that can be performed
by the CPython virtual machine. These are things like ``LOAD_NAME`` which loads
a name onto the stack, or ``ROT_TWO`` which rotates the top two stack elements.

Some instructions accept an argument, for example ``LOAD_NAME``, which modifies
the behavior of the instruction. This is much like a function call where some
functions accept arguments. Because the bytecode is always packed as raw bytes,
the argument must be some integer (CPython stores all arguments two in bytes).
This means that things that need a more rich argument system (like ``LOAD_NAME``
which needs the actual name to look up) must carry around the actual arguments
in some table and use the integer as an offset into this array. One of the key
abstractions of the ``Instruction`` object is that the argument is always some
python object that represents the actual argument. Any lookup table management
is handled for the user. This is helpful because some arguments share this table
so we don't want to add extra entries or forget to add them at all.

Another annoyance is that the instructions that handle control flow use their
argument to say what bytecode offset to jump to. Some jumps use the absolute
index, others use a relative index. This also makes it hard if you want to add
or remove instructions because all of the offsets must be recomputed. In
``codetransformer``, the jump instructions all accept another ``Instruction`` as
the argument so that the assembler can manage this for the user. We also provide
an easy way for new instructions to "steal" jumps that targeted another
instruction so that can manage altering the bytecode around jump targets.

Code
~~~~

``Code`` objects are a nice abstraction over python's
``types.CodeType``. Quoting the ``CodeType`` constructor docstring:

::

   code(argcount, kwonlyargcount, nlocals, stacksize, flags, codestring,
         constants, names, varnames, filename, name, firstlineno,
         lnotab[, freevars[, cellvars]])

   Create a code object.  Not for the faint of heart.

The ``codetransformer`` abstraction is designed to make it easy to dynamically
construct and inspect these objects. This allows us to easy set things like the
argument names, and manipulate the line number mappings.

The ``Code`` object provides methods for converting to and from Python's code
representation:

1. ``from_pycode``
2. ``to_pycode``.

This allows us to take an existing function, parse the meaning from it, modify
it, and then assemble this back into a new python code object.

.. note::

   ``Code`` objects are immutable. When we say "modify", we mean create a copy
   with different values.

CodeTransformers
----------------

This is the set of rules that are used to actually modify the ``Code``
objects. These rules are defined as a set of ``patterns`` which are a DSL used
to define a DFA for matching against sequences of ``Instruction`` objects. Once
we have matched a segment, we yield new instructions to replace what we have
matched. A simple codetransformer looks like:

.. code-block:: python

   from codetransformer import CodeTransformer, instructions

   class FoldNames(CodeTransformer):
       @pattern(
           instructions.LOAD_GLOBAL,
           instructions.LOAD_GLOBAL,
           instructions.BINARY_ADD,
       )
       def _load_fast(self, a, b, add):
           yield instructions.LOAD_FAST(a.arg + b.arg).steal(a)

This ``CodeTransformer`` uses the ``+`` operator to implement something like
``CPP``\s token pasting for local variables. We read this pattern as a sequence
of two ``LOAD_GLOBAL`` (global name lookups) followed by a ``BINARY_ADD``
instruction (``+`` operator call). This will then call the function with the
three instructions passed positionally. This handler replaces this sequence with
a single instruction that emits a ``LOAD_FAST`` (local name lookup) that is the
result of adding the two names together. We then steal any jumps that used to
target the first ``LOAD_GLOBAL``.

We can execute this transformer by calling an instance of it on a
function object, or using it like a decorator. For example:

.. code-block:: python

   >>> @FoldNames()
   ... def f():
   ...     ab = 3
   ...     return a + b
   >>> f()
   3


License
-------

``codetransformer`` is free software, licensed under the GNU General Public
License, version 2. For more information see the ``LICENSE`` file.


Source
------

Source code is hosted on github at
https://github.com/llllllllll/codetransformer.


.. _lazy: https://github.com/llllllllll/lazy_python
.. _opcode: https://docs.python.org/3.5/library/dis.html#opcode-NOP
.. |build status| image:: https://travis-ci.org/llllllllll/codetransformer.svg?branch=master
   :target: https://travis-ci.org/llllllllll/codetransformer
.. |documentation| image:: https://readthedocs.org/projects/codetransformer/badge/?version=stable
   :target: http://codetransformer.readthedocs.io/en/stable/?badge=stable
   :alt: Documentation Status
