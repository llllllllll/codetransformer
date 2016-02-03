Codetransformer API Reference
-----------------------------

``codetransformer.transformers``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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


``codetransformer.code``
~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: codetransformer.code.Code
   :members:

.. autoclass:: codetransformer.code.Flag
   :members:
   :undoc-members:


``codetransformer.instructions``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: codetransformer.instructions

.. py:class:: codetransformer.instructions.Instruction

   Base class for all Instructions.

   For details on particular instructions, see `the dis stdlib module docs.`_

   .. automethod:: from_bytes
   .. automethod:: from_opcode

   .. automethod:: steal
   .. automethod:: equiv

   .. autoattribute:: stack_effect

   :members:
   :undoc-members:
   :exclude-members: Instruction

.. _`the dis stdlib module docs.` : https://docs.python.org/3.4/library/dis.html#python-bytecode-instructions

``codetransformer.utils``
~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: codetransformer.utils.pretty
   :members:

.. automodule:: codetransformer.utils.immutable
   :members: immutable, lazyval, immutableattr

.. automodule:: codetransformer.utils.functional
   :members:
