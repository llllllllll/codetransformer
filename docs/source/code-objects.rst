===========================
 Working with Code Objects
===========================

The :class:`~codetransformer.code.Code` type is the foundational abstraction in
``codetransformer``.  It provides high-level APIs for working with
logically-grouped sets of instructions and for converting to and from CPython's
native :class:`code <types.CodeType>` type.

Constructing Code Objects
=========================

The most common way constructing a Code object is to use the
:meth:`~codetransformer.code.Code.from_pycode` classmethod, which accepts a
CPython :class:`code <types.CodeType>` object.

There are two common ways of building raw code objects:

- CPython functions have a ``__code__`` attribute, which contains the bytecode
  executed by the function.
- The :func:`compile` builtin can compile a string of Python source code into a
  code object.

Using :meth:`~codetransformer.code.Code.from_pycode`, we can build a Code
object and inspect its contents::

    >>> from codetransformer import Code
    >>> def add2(x):
    ...     return x + 2
    ...
    >>> co = Code.from_pycode(add.__code__)
    >>> co.instrs
    (LOAD_FAST('x'), LOAD_CONST(2), BINARY_ADD, RETURN_VALUE)
    >>> co.argnames
    ('x',)
    >>> c.consts
    (2,)

We can convert our Code object back into its raw form via the
:meth:`~codetransformer.code.Code.to_bytecode` method::

    >>> co.to_pycode()
    <code object add2 at 0x7f6ba05f2030, file "<stdin>", line 1>

Building Transformers
=====================

Once we have the ability to convert to and from an abstract code
representation, we gain the ability to perform transformations on that abtract
representation.

Let's say that we want to replace the addition operation in our ``add2``
function with a multiplication. We could try to mutate our
:class:`~codetransformer.code.Code` object directly before converting back to
Python bytecode, but there are many subtle invariants [#f1] between the
instructions and the other pieces of metadata that must be maintained to ensure
that the generated output can be executed correctly.

Rather than encourage users to mutate Code objects in place,
``codetransformer`` provides the :class:`~codetransformer.core.CodeTransformer`
class, which allows users to declaratively describe operations to perform on
sequences of instructions.

Implemented as a :class:`~codetransformer.core.CodeTransformer`, our "replace
additions with multiplications" operation looks like this:

.. literalinclude:: add2mul.py
   :language: python
   :lines: 10-

The important piece here is the ``_add2mul`` method, which has been decorated
with a :class:`~codetransformer.patterns.pattern`. Patterns provide an API for
describing sequences of instructions to match against for replacement and/or
modification.  The :class:`~codetransformer.core.CodeTransformer` base class
looks at methods with registered patterns and compares them against the
instructions of the Code object under transformation.  For each matching
sequence of instructions, the decorated method is called with all matching
instructions \*-unpacked into the method.  The method's job is to take the
input instructions and return an iterable of new instructions to serve as
replacements. It is often convenient to implement transformer methods as
`generator functions`_, as we've done here.

In this example, we've supplied the simplest possible pattern: a single
instruction type to match. [#f2] Our transformer method will be called on every
``BINARY_ADD`` instruction in the target code object, and it will yield a
``BINARY_MULTIPLY`` as replacement each time.

Applying Transformers
=====================

To apply a :class:`~codetransformer.core.CodeTransformer` to a function, we
construct an instance of the transformer and call it on the function we want to
modify.  The result is a new function whose instructions have been rewritten
applying our transformer's methods to matched sequences of the input function's
instructions.  The original function is not mutated in place.

**Example:**

.. code-block:: python

  >>> transformer = add2mul()
  >>> mul2 = transformer(add2) # mult2 is a brand-new function
  >>> mul2(5)
  10

When we don't care about having access to the pre-transformed version of a
function, it's convenient and idiomatic to apply transformers as decorators::

 >>> @add2mul()
 ... def mul2(x):
 ...     return x + 2
 ...
 >>> mul2(5)
 10

.. [#f1] For example, if we add a new constant, we have to ensure that we
         correctly maintain the indices of existing constants in the generated
         code's ``co_consts``, and if we replace an instruction that was the
         target of a jump, we have to make sure that the jump instruction
         resolves correctly to our new instruction.

.. [#f2] Many more complex patterns are possible.  See the docs for
         :class:`codetransformer.patterns.pattern` for more examples.
.. _`generator functions` : https://docs.python.org/2/tutorial/classes.html#generators
