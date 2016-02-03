"""
add2mul
--------

A transformer that replaces BINARY_ADD instructions with BINARY_MULTIPLY
instructions.

This isn't useful, but it's good introductory example/tutorial material.
"""
from codetransformer import CodeTransformer, pattern
from codetransformer.instructions import BINARY_ADD, BINARY_MULTIPLY


class add2mul(CodeTransformer):
    @pattern(BINARY_ADD)
    def _add2mul(self, add_instr):
        yield BINARY_MULTIPLY().steal(add_instr)
