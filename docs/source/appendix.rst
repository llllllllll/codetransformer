API Reference
=============

``codetransformer.code``
------------------------

.. autoclass:: codetransformer.code.Code
   :members:

.. autoclass:: codetransformer.code.Flag
   :members:
   :undoc-members:

``codetransformer.core``
------------------------

.. autoclass:: codetransformer.core.CodeTransformer
   :members:

``codetransformer.instructions``
--------------------------------

For details on particular instructions, see `the dis stdlib module docs.`_

.. automodule:: codetransformer.instructions
   :members:
   :undoc-members:


``codetransformer.transformers``
--------------------------------

.. automodule:: codetransformer.transformers
   :members:

.. automodule:: codetransformer.transformers.literals
   :members:
   :exclude-members: patterndispatcher

.. autoclass:: codetransformer.transformers.literals.overloaded_strs
.. autoclass:: codetransformer.transformers.literals.overloaded_floats
.. autoclass:: codetransformer.transformers.literals.overloaded_ints
.. autoclass:: codetransformer.transformers.literals.overloaded_complexes

.. autoclass:: codetransformer.transformers.literals.haskell_strs
.. autoclass:: codetransformer.transformers.literals.bytearray_literals
.. autoclass:: codetransformer.transformers.literals.decimal_literals

.. autoclass:: codetransformer.transformers.exc_patterns.pattern_matched_exceptions


``codetransformer.utils``
-------------------------

.. automodule:: codetransformer.utils.pretty
   :members:

.. automodule:: codetransformer.utils.immutable
   :members: immutable, lazyval, immutableattr

.. automodule:: codetransformer.utils.functional
   :members:


``codetransformer.decompiler``
------------------------------

.. automodule:: codetransformer.decompiler
   :members: decompile, pycode_to_body, DecompilationContext, DecompilationError

.. _`the dis stdlib module docs.` : https://docs.python.org/3.4/library/dis.html#python-bytecode-instructions
