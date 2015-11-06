from codetransformer import CodeTransformer, pattern


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
