============
 Pattern API
============

Most bytecode transformations are best expressed by identifying a pattern in the
bytecode and emitting some replacement. ``codetransformer`` makes it easy to
express and work on these patterns by defining a small dsl for use in
:class:`~codetransformer.core.CodeTransformer` classes.

Matchables
==========

A pattern is expressed by a sequence of matchables paired with the startcode. A
matchable is anything that we can compare a sequence of bytecode to.

Instructions
------------

The most atomic matchable is any
:class:`~codetransformer.instructions.Instruction` class. These classes each can
be used to define a pattern that matches instances of that instruction. For
example, the pattern::

  LOAD_CONST

will match a single :class:`~codetransformer.instructions.LOAD_CONST` instance.

All matchables support the following operations:

``or``
------

Matchables can be or'd together to create a new matchable that matches either
the lhs or the rhs. For example::

  LOAD_CONST | LOAD_FAST

will match a either a single :class:`~codetransformer.instructions.LOAD_CONST`
or a :class:`~codetransformer.instructions.LOAD_FAST`.

``not``
-------

Matchables may be negated to create a new matchable that matches anything the
original did not match. For example::

  ~LOAD_CONST

will match any instruction except an instance of
:class:`~codetransformer.instructions.LOAD_CONST`.

``matchrange``
--------------

It is possible to create a matchable from another such that it matches the same
pattern repeated multiple times. For example::

  LOAD_CONST[3]

will match exactly three :class:`~codetransformer.instructions.LOAD_CONST`
instances in a row. This will not match on any less than three and will match on
the first three if there are more than three
:class:`~codetransformer.instructions.LOAD_CONST` instructions in a row.

This can be specified with an upper bound also like::

  LOAD_CONST[3, 5]

This matches between three and five
:class:`~codetransformer.instructions.LOAD_CONST` instructions. This is greedy
meaning that if four or five :class:`~codetransformer.instructions.LOAD_CONST`
instructions exist it will consume as many as possible up to five.

``var``
-------

:data:`~codetransformer.patterns.var` is a modifier that matches zero or more
instances of another matchable. For example::

  LOAD_CONST[var]

will match as many :class:`~codetransformer.instructions.LOAD_CONST`
instructions appear in a row or an empty instruction set.

``plus``
--------

:data:`~codetransformer.patterns.plus` is a modifier that matches one or more
instances of another matchable. For example::

  LOAD_CONST[plus]

will match as many :class:`~codetransformer.instructions.LOAD_CONST`
instructions appear in a row as long as there is at least one.

``option``
----------

:data:`~codetransformer.patterns.option` is a modifier that matches zero or one
instance of another matchable. For example::

  LOAD_CONST[option]

will match either an empty instruction set or exactly one
:class:`~codetransformer.instructions.LOAD_CONST`.

``matchany``
------------

:data:`~codetransformer.patterns.matchany` is a special matchable that matches
any single instruction. ``...`` is an alias for
:data:`~codetransformer.patterns.matchany`.

``seq``
-------

:class:`~codetransformer.patterns.seq` is a matchable that matches a sequence of
other matchables. For example::

  seq(LOAD_CONST, ..., ~LOAD_CONST)

will match a single :class:`~codetransformer.instructions.LOAD_CONST` followed
by any instruction followed by any instruction that is not a
:class:`~codetransformer.instructions.LOAD_CONST`. This example show how we can
compose all of our matchable together to build more complex matchables.

``pattern``
===========

In order to use our DSL we need a way to register transformations to these
matchables. To do this we may decorate methods of a
:class:`~codetransformer.core.CodeTransformer` with
:class:`~codetransformer.patterns.pattern`. This registers the function to the
pattern. For example::

  class MyTransformer(CodeTransformer):
      @pattern(LOAD_CONST, ..., ~LOAD_CONST)
      def _f(self, load_const, any, not_load_const):
          ...

The argument list of a :class:`~codetransformer.patterns.pattern` is implicitly
made into a `seq`_. When using ``MyTransformer`` to transform some bytecode
``_f`` will be called  only when we see a
:class:`~codetransformer.instructions.LOAD_CONST` followed by any instruction
followed by any instruction that is not a
:class:`~codetransformer.instructions.LOAD_CONST`. This function will be passed
these three instruction objects positionally and should yield the instructions
to replace them with.

Resolution Order
----------------

Patterns are checked in the order they are defined in the class body. This is
because some patterns may overlap with eachother. For example, given the two
classes::

  class OrderOne(CodeTransformer):
      @pattern(LOAD_CONST)
      def _load_const(self, instr):
          print('LOAD_CONST')
          yield instr

      @pattern(...)
      def _any(self, instr):
          print('...')
          yield instr


  class OrderTwo(CodeTransformer):
      @pattern(...)
      def _any(self, instr):
          print('...')
          yield instr

      @pattern(LOAD_CONST)
      def _load_const(self, instr):
          print('LOAD_CONST')
          yield instr




and the following bytecode sequence::

  LOAD_CONST POP_TOP LOAD_CONST RETURN_VALUE

When running with ``OrderOne`` we would see::


  LOAD_CONST
  ...
  LOAD_CONST
  ...

but when running with ``OrderTwo``::

  ...
  ...
  ...
  ...

This is because we will always match on the ``...`` pattern where ``OrderOne``
will check against :class:`~codetransformer.instructions.LOAD_CONST` before
falling back to the :data:`~codetransformer.instructions.matchany`.

Contextual Patterns
-------------------

Sometimes a pattern should only be matched given that some condition has been
met. An example of this is that you want to modify comprehensions. In order to
be sure that you are only modifying the bodies of the comprehensions we must
only match when we know we are in
one. :class:`~codetransformer.patterns.pattern` accepts a keyword only argument
``startcodes`` which is a set of contexts where this pattern should apply. By
default this is :data:`~codetransformer.patterns.DEFAULT_STARTCODE` which is the
default state. A startcode may be anything hashable; however it is best to use
strings or integer constants to make it easy to debug.

The :meth:`~codetransformer.core.CodeTransformer.begin` method enters a new
startcode. For example::

  class FindDictComprehensions(CodeTransformer):
      @pattern(BUILD_MAP, matchany[var], MAP_ADD)
      def _start_comprehension(self, *instrs):
          print('starting dict comprehension')
          self.begin('in_comprehension')
          yield from instrs

      @pattern(RETURN_VALUE, startcodes=('in_comprehension',))
      def _return_from_comprehension(self, instr):
          print('returning from comprehension')
          yield instr

      @pattern(RETURN_VALUE)
      def _return_default(self, instr):
          print('returning from non-comprehension')
          yield instr


This transformer will find dictionary comprehensions and enter a new
startcode. Inside this startcode we will handle
:class:`~codetransformer.instructions.RETURN_VALUE` instructions differently.

.. code-block:: python

   >>> @FindDictComprehensions()
   ... def f():
   ...     pass
   ...
   returning from non-comprehension

   >>> @FindDictComprehensions()
   ... def g():
   ...     {a: b for a, b in it}
   ...
   starting dict comprehension
   returning from comprehension
   returning from non-comprehension


It is important to remember that when we recurse into a nested code object (like
a comprehension) that we do not inherit the startcode from our parent. Instead
it always starts at :data:`~codetransformer.patterns.DEFAULT_STARTCODE`.
