import toolz.curried.operator as op

from codetransformer import Code, CodeTransformer, pattern
from codetransformer.instructions import Instruction
from codetransformer.utils.instance import instance


def test_inherit_patterns():
    class C(CodeTransformer):
        matched = False

        @pattern(...)
        def _(self, instr):
            self.matched = True
            yield instr

    class D(C):
        pass

    d = D()
    assert not d.matched

    @d
    def f():
        pass

    assert d.matched


def test_override_patterns():
    class C(CodeTransformer):
        matched_super = False
        matched_sub = False

        @pattern(...)
        def _(self, instr):
            self.matched_super = True
            yield instr

    class D(C):
        @pattern(...)
        def _(self, instr):
            self.matched_sub = True
            yield instr

    d = D()
    assert not d.matched_super
    assert not d.matched_sub

    @d
    def f():
        pass

    assert d.matched_sub
    assert not d.matched_super


def test_updates_lnotab():
    @instance
    class c(CodeTransformer):
        @pattern(...)
        def _(self, instr):
            yield type(instr)(instr.arg).steal(instr)

    def f():  # pragma: no cover
        # this function has irregular whitespace for testing the lnotab
        a = 1
        # intentional line
        b = 2
        # intentional line
        c = 3
        # intentional line
        return a, b, c

    original = Code.from_pyfunc(f)
    post_transform = c.transform(original)

    # check that something happened
    assert original.lnotab != post_transform.lnotab
    # check that we preserved the line numbers
    assert (
        original.lnotab.keys() ==
        post_transform.lnotab.keys() ==
        set(map(op.add(original.firstlineno), (2, 4, 6, 8)))
    )

    def sorted_instrs(lnotab):
        order = sorted(lnotab.keys())
        for idx in order:
            yield lnotab[idx]

    # check that the instrs are correct
    assert all(map(
        Instruction.equiv,
        sorted_instrs(original.lnotab),
        sorted_instrs(post_transform.lnotab),
    ))

    # sanity check that the function is correct
    assert f() == c(f)()
