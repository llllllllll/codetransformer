from types import FunctionType

import toolz

from ..code import Code
from ..core import CodeTransformer
from .. import instructions as instrs
from ..patterns import (
    DEFAULT_STARTCODE,
    end,
    matchany,
    option,
    or_,
    pattern,
    seq,
    var,
    var_nongreedy,
)


METHOD_DEF_PATTTERN = (
    seq(instrs.LOAD_CLOSURE[var], instrs.BUILD_TUPLE)[option],
    instrs.LOAD_CONST,
    instrs.LOAD_CONST,
    instrs.MAKE_FUNCTION,
    instrs.STORE_FAST,
)


def selfless(f):
    xform = _selfless_xform()
    xformed = xform(f)
    return xform.finalize(f)


class _selfless_xform(CodeTransformer):

    def __init__(self):
        super().__init__()
        self.init = None
        self.attrs = None
        self.methods = {}

    @pattern(matchany[var_nongreedy],
             *METHOD_DEF_PATTTERN,
             startcodes=(DEFAULT_STARTCODE,))
    def first_block(self, *match):
        init, name, closure_loads, code = self._parse_method_def(match)

        self._add_init(init)
        self._add_method(name, closure_loads, code)

        self.begin('after_init')

        return ()

    @pattern(*METHOD_DEF_PATTTERN, startcodes=('after_init',))
    def method(self, *match):
        head, name, closure_loads, code = self._parse_method_def(match)
        assert len(head) == 0, head

        self._add_method(name, closure_loads, code)

        return ()

    def finalize(self, f):
        init = FunctionType(
            self.init.to_pycode(),
            f.__globals__,
            f.__name__,
            f.__defaults__,
            f.__closure__,
        )

        def make_method(name):
            return FunctionType(
                self.methods[name].to_pycode(),
                f.__globals__,
                name,
                None,
                (),
            )

        methods = {'__init__': init}
        for name, code in self.methods.items():
            methods[name] = FunctionType(
                code.to_pycode(),
                f.__globals__,
                name,
                None,
                (),
            )

        return type(f.__name__, (object,), methods)

    def _parse_method_def(self, match):
        *prefix, load_code, load_name, make_func, store = match
        if prefix and isinstance(prefix[-1], instrs.BUILD_TUPLE):
            *prefix, build_tup = prefix
            prefix, closures = prefix[:-build_tup.arg], prefix[-build_tup.arg:]
            for instr in closures:
                assert isinstance(instr, instrs.LOAD_CLOSURE), instr
        else:
            closures = ()

        return prefix, store.arg, [a.arg for a in closures], load_code.arg

    def _add_init(self, match):
        if self.init is not None:
            raise RuntimeError("Already added an init")

        xform = _init_transformer(self.code.cellvars)
        to_xform = Code(
            match,
            argnames=('self',) + self.code.argnames,
            name='__init__',
            filename=self.code.filename,
            cellvars=self.code.cellvars,
            freevars=(),
        )
        self.init = xform.transform(to_xform)
        self.attrs = xform.attrs

    def _add_method(self, name, closure_loads, code):
        xform = _method_transformer(self.attrs)
        to_xform = Code.from_pycode(code)
        self.methods[name] = xform.transform(to_xform)


class _init_transformer(CodeTransformer):

    def __init__(self, cellvars):
        super().__init__()
        self.attrs = set(cellvars)

    def transform_cellvars(self, *args, **kwargs):
        return ()

    def transform_freevars(self, *args, **kwargs):
        return ()

    @pattern(matchany, end)
    def _last_instr(self, instr):
        if isinstance(instr, (instrs.STORE_FAST, instrs.STORE_DEREF)):
            yield instrs.LOAD_FAST('self').steal(instr)
            yield instrs.STORE_ATTR(instr.arg)
        yield instrs.LOAD_CONST(None)
        yield instrs.RETURN_VALUE()

    @pattern(instrs.LOAD_DEREF)
    def _rewrite_load_deref(self, load):
        if load.arg in self.code.argnames:
            yield instrs.LOAD_FAST(load.arg).steal(load)

    @pattern(instrs.STORE_FAST)
    def _rewrite_store_fast(self, store):
        self.attrs.add(store.attr)
        yield instrs.LOAD_FAST('self').steal(store)
        yield instrs.STORE_ATTR(store.arg)

    @pattern(instrs.STORE_DEREF)
    def _rewrite_store_deref(self, store):
        assert store.arg in self.attrs
        yield instrs.LOAD_FAST('self').steal(store)
        yield instrs.STORE_ATTR(store.arg)


class _method_transformer(CodeTransformer):

    def __init__(self, attrs):
        super().__init__()
        self.attrs = set(attrs)

    def transform_argnames(self, names):
        return ('self',) + names

    def transform_cellvars(self, *args, **kwargs):
        return ()

    def transform_freevars(self, *args, **kwargs):
        return ()

    @pattern(or_(instrs.LOAD_FAST, instrs.LOAD_GLOBAL))
    def _rewrite_load_fast(self, load):
        if load.arg in self.attrs and load.arg not in self.code.argnames:
            yield instrs.LOAD_FAST('self').steal(load)
            yield instrs.LOAD_ATTR(load.arg)
        else:
            yield load

    @pattern(instrs.LOAD_DEREF)
    def _rewrite_load_deref(self, load):
        assert load.arg in self.attrs
        yield instrs.LOAD_FAST('self').steal(load)
        yield instrs.LOAD_ATTR(load.arg)

    @pattern(instrs.STORE_FAST)
    def _rewrite_store_fast(self, store):
        # TODO: Handle argnames that are the same as local variables.
        if store.arg in self.attrs:
            yield instrs.LOAD_FAST('self').steal(store)
            yield instrs.STORE_ATTR(store.arg)
        else:
            yield store

    @pattern(instrs.STORE_DEREF)
    def _rewrite_store_deref(self, store):
        assert store.arg in self.attrs
        yield instrs.LOAD_FAST('self')
        yield instrs.STORE_ATTR(store.arg)
