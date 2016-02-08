API Reference
=============

``codetransformer.transformers``
--------------------------------

.. automodule:: codetransformer.transformers
   :members:

.. autodata:: islice_literals
   :annotation:

.. data:: bytearray_literals

   A transformer that converts :class:`bytes` literals to :class:`bytearray`.

.. data:: decimal_literals

   A transformer that converts :class:`float` literals to :class:`~decimal.Decimal`.

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


``codetransformer.patterns``
----------------------------

.. autoclass:: codetransformer.patterns.pattern

.. autodata:: codetransformer.patterns.DEFAULT_STARTCODE

DSL Objects
~~~~~~~~~~~

.. autodata:: codetransformer.patterns.matchany
.. autoclass:: codetransformer.patterns.seq
.. autodata:: codetransformer.patterns.var
.. autodata:: codetransformer.patterns.plus
.. autodata:: codetransformer.patterns.option

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
