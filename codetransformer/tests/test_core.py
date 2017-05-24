import pytest
import toolz.curried.operator as op

from codetransformer import CodeTransformer, Code, pattern
from codetransformer.core import Context, NoContext
from codetransformer.instructions import Instruction
from codetransformer.patterns import DEFAULT_STARTCODE
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


def test_context():
    def f():  # pragma: no cover
        pass

    code = Code.from_pyfunc(f)
    c = Context(code)

    # check default attributes
    assert c.code is code
    assert c.startcode == DEFAULT_STARTCODE

    # check that the object acts like a namespace
    c.attr = 'test'
    assert c.attr == 'test'


def test_no_context():
    @instance
    class c(CodeTransformer):
        pass

    with pytest.raises(NoContext) as e:
        c.context

    assert str(e.value) == 'no active transformation context'
