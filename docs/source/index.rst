codetransformer
===============

Bytecode transformers for CPython inspired by the ``ast`` module's
``NodeTransformer``.

``codetransformer`` is a library that provides utilities for working with
CPython bytecode at runtime.  Among other things, it provides:

- A :class:`~codetransformer.code.Code` type for representing and manipulating
  Python bytecode.
- An :class:`~codetransformer.instructions.Instruction` type, with
  :class:`subclasses <codetransformer.instructions.BINARY_ADD>` for each opcode
  used by the CPython interpreter.
- A :class:`~codetransformer.core.CodeTransformer` type providing a
  pattern-based API for describing transformations on
  :class:`~codetransformer.code.Code` objects.  Example transformers can be
  found in :mod:`codetransformer.transformers`.
- An experimental :mod:`decompiler <codetransformer.decompiler>` for
  determining the AST tree that would generate a code object.

The existence of ``codetransformer`` is motivated by the desire to override
parts of the python language that cannot be easily hooked via more standard
means. Examples of program transformations made possible using code
transformers include:

* Overriding the ``is`` and ``not`` operators.
* `Overloading Python's data structure literals`_.
* `Optimizing functions by freezing globals as constants`_.
* `Exception handlers that match on exception instances`_.

Contents:

.. toctree::
   :maxdepth: 2

   appendix.rst


Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

.. _lazy: https://github.com/llllllllll/lazy_python
.. _Overloading Python's data structure literals: appendix.html\#codetransformer.transformers.literals.overloaded_dicts
.. _Optimizing functions by freezing globals as constants: appendix.html#codetransformer.transformers.asconstants
.. _Exception handlers that match on exception instances: appendix.html#codetransformer.transformers.exc_patterns.pattern_matched_exceptions
