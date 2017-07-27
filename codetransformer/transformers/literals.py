from collections import OrderedDict
from decimal import Decimal
from itertools import islice
import sys
from textwrap import dedent

from .. import instructions
from ..core import CodeTransformer
from ..patterns import pattern,  matchany, var
from ..utils.instance import instance


IN_COMPREHENSION = 'in_comprehension'


class overloaded_dicts(CodeTransformer):
    """Transformer that allows us to overload dictionary literals.

    This acts by creating an empty map and then inserting every
    key value pair in order.

    The code that is generated will turn something like::

        {k_0: v_0, k_1: v_1, ..., k_n: v_n}

    into::

        _tmp = astype()
        _tmp[k_0] = v_0
        _tmp[k_1] = v_1
        ...
        _tmp[k_n] = v_n
        _tmp  # leaves the map on the stack.

    Parameters
    ----------
    astype : callable
        The constructor for the type to create.

    Examples
    --------
    >>> from collections import OrderedDict
    >>> ordereddict_literals = overloaded_dicts(OrderedDict)
    >>> @ordereddict_literals
    ... def f():
    ...     return {'a': 1, 'b': 2, 'c': 3}
    ...
    >>> f()
    OrderedDict([('a', 1), ('b', 2), ('c', 3)])
    """
    def __init__(self, astype):
        super().__init__()
        self.astype = astype

    @pattern(instructions.BUILD_MAP, matchany[var], instructions.MAP_ADD)
    def _start_comprehension(self, instr, *instrs):
        yield instructions.LOAD_CONST(self.astype).steal(instr)
        # TOS  = self.astype

        yield instructions.CALL_FUNCTION(0)
        # TOS  = m = self.astype()

        yield instructions.STORE_FAST('__map__')

        *body, map_add = instrs
        yield from self.patterndispatcher(body)
        # TOS  = k
        # TOS1 = v

        yield instructions.LOAD_FAST('__map__').steal(map_add)
        # TOS  = __map__
        # TOS1 = k
        # TOS2 = v

        yield instructions.ROT_TWO()
        # TOS  = k
        # TOS1 = __map__
        # TOS2 = v

        yield instructions.STORE_SUBSCR()
        self.begin(IN_COMPREHENSION)

    @pattern(instructions.RETURN_VALUE, startcodes=(IN_COMPREHENSION,))
    def _return_value(self, instr):
        yield instructions.LOAD_FAST('__map__').steal(instr)
        # TOS  = __map__

        yield instr

    if sys.version_info[:2] <= (3, 4):
        # Python 3.4

        @pattern(instructions.BUILD_MAP)
        def _build_map(self, instr):
            yield instructions.LOAD_CONST(self.astype).steal(instr)
            # TOS  = self.astype

            yield instructions.CALL_FUNCTION(0)
            # TOS  = m = self.astype()

            yield from (instructions.DUP_TOP(),) * instr.arg
            # TOS  = m
            # ...
            # TOS[instr.arg] = m

        @pattern(instructions.STORE_MAP)
        def _store_map(self, instr):
            # TOS  = k
            # TOS1 = v
            # TOS2 = m
            # TOS3 = m

            yield instructions.ROT_THREE().steal(instr)
            # TOS  = v
            # TOS1 = m
            # TOS2 = k
            # TOS3 = m

            yield instructions.ROT_THREE()
            # TOS  = m
            # TOS1 = k
            # TOS2 = v
            # TOS3 = m

            yield instructions.ROT_TWO()
            # TOS  = k
            # TOS1 = m
            # TOS2 = v
            # TOS3 = m

            yield instructions.STORE_SUBSCR()
            # TOS  = m

    else:
        # Python 3.5 and beyond!

        def _construct_map(self, key_value_pairs):
            mapping = self.astype()
            for key, value in zip(key_value_pairs[::2], key_value_pairs[1::2]):
                mapping[key] = value
            return mapping

        @pattern(instructions.BUILD_MAP)
        def _build_map(self, instr):
            # TOS      = vn
            # TOS1     = kn
            # ...
            # TOSN     = v0
            # TOSN + 1 = k0
            # Construct a tuple of (k0, v0, k1, v1, ..., kn, vn) for
            # each of the key: value pairs in the dictionary.
            yield instructions.BUILD_TUPLE(instr.arg * 2).steal(instr)
            # TOS  = (k0, v0, k1, v1, ..., kn, vn)

            yield instructions.LOAD_CONST(self._construct_map)
            # TOS  = self._construct_map
            # TOS1 = (k0, v0, k1, v1, ..., kn, vn)

            yield instructions.ROT_TWO()
            # TOS  = (k0, v0, k1, v1, ..., kn, vn)
            # TOS1 = self._construct_map

            yield instructions.CALL_FUNCTION(1)

    if sys.version_info >= (3, 6):
        def _construct_const_map(self, values, keys):
            mapping = self.astype()
            for key, value in zip(keys, values):
                mapping[key] = value
            return mapping

        @pattern(instructions.LOAD_CONST, instructions.BUILD_CONST_KEY_MAP)
        def _build_const_map(self, keys, instr):
            yield instructions.BUILD_TUPLE(len(keys.arg)).steal(keys)
            # TOS  = (v0, v1, ..., vn)

            yield keys
            # TOS  = (k0, k1, ..., kn)
            # TOS1 = (v0, v1, ..., vn)

            yield instructions.LOAD_CONST(self._construct_const_map)
            # TOS  = self._construct_const_map
            # TOS1 = (k0, k1, ..., kn)
            # TOS2 = (v0, v1, ..., vn)

            yield instructions.ROT_THREE()
            # TOS  = (k0, k1, ..., kn)
            # TOS1 = (v0, v1, ..., vn)
            # TOS2 = self._construct_const_map

            yield instructions.CALL_FUNCTION(2)


ordereddict_literals = overloaded_dicts(OrderedDict)


def _format_constant_docstring(type_):
    return dedent(
        """
        Transformer that applies a callable to each {type_} constant in the
        transformed code object.

        Parameters
        ----------
        xform : callable
            A callable to be applied to {type_} literals.

        See Also
        --------
        codetransformer.transformers.literals.overloaded_strs
        """
    ).format(type_=type_.__name__)


class _ConstantTransformerBase(CodeTransformer):

    def __init__(self, xform):
        super().__init__()
        self.xform = xform

    def transform_consts(self, consts):
        # This is all one expression.
        return super().transform_consts(
            tuple(
                frozenset(self.transform_consts(tuple(const)))
                if isinstance(const, frozenset)
                else self.transform_consts(const)
                if isinstance(const, tuple)
                else self.xform(const)
                if isinstance(const, self._type)
                else const
                for const in consts
            )
        )


def overloaded_constants(type_, __doc__=None):
    """A factory for transformers that apply functions to literals.

    Parameters
    ----------
    type_ : type
        The type to overload.
    __doc__ : str, optional
        Docstring for the generated transformer.

    Returns
    -------
    transformer : subclass of CodeTransformer
        A new code transformer class that will overload the provided
        literal types.
    """
    typename = type_.__name__
    if typename.endswith('x'):
        typename += 'es'
    elif not typename.endswith('s'):
        typename += 's'

    if __doc__ is None:
        __doc__ = _format_constant_docstring(type_)

    return type(
        "overloaded_" + typename,
        (_ConstantTransformerBase,), {
            '_type': type_,
            '__doc__': __doc__,
        },
    )


overloaded_strs = overloaded_constants(
    str,
    __doc__=dedent(
        """
        A transformer that overloads string literals.

        Rewrites all constants of the form::

            "some string"

        as::

            xform("some string")

        Parameters
        ----------
        xform : callable
            Function to call on all string literals in the transformer target.

        Examples
        --------
        >>> @overloaded_strs(lambda x: "ayy lmao ")
        ... def prepend_foo(s):
        ...     return "foo" + s
        ...
        >>> prepend_foo("bar")
        'ayy lmao bar'
        """
    )
)
overloaded_bytes = overloaded_constants(bytes)
overloaded_floats = overloaded_constants(float)
overloaded_ints = overloaded_constants(int)
overloaded_complexes = overloaded_constants(complex)

haskell_strs = overloaded_strs(tuple)
bytearray_literals = overloaded_bytes(bytearray)
decimal_literals = overloaded_floats(Decimal)


def _start_comprehension(self, *instrs):
    self.begin(IN_COMPREHENSION)
    yield from self.patterndispatcher(instrs)


def _return_value(self, instr):
    # TOS  = collection

    yield instructions.LOAD_CONST(self.xform).steal(instr)
    # TOS  = self.xform
    # TOS1 = collection

    yield instructions.ROT_TWO()
    # TOS  = collection
    # TOS1 = self.xform

    yield instructions.CALL_FUNCTION(1)
    # TOS  = self.xform(collection)

    yield instr


# Added as a method for overloaded_build
def _build(self, instr):
    yield instr
    # TOS  = new_list

    yield instructions.LOAD_CONST(self.xform)
    # TOS  = astype
    # TOS1 = new_list

    yield instructions.ROT_TWO()
    # TOS  = new_list
    # TOS1 = astype

    yield instructions.CALL_FUNCTION(1)
    # TOS  = astype(new_list)


def overloaded_build(type_, add_name=None):
    """Factory for constant transformers that apply to a given
    build instruction.

    Parameters
    ----------
    type_ : type
        The object type to overload the construction of. This must be one of
        "buildable" types, or types with a "BUILD_*" instruction.
    add_name : str, optional
        The suffix of the instruction tha adds elements to the collection.
        For example: 'add' or 'append'

    Returns
    -------
    transformer : subclass of CodeTransformer
        A new code transformer class that will overload the provided
        literal types.
    """
    typename = type_.__name__
    instrname = 'BUILD_' + typename.upper()
    dict_ = OrderedDict(
        __doc__=dedent(
            """
            A CodeTransformer for overloading {name} instructions.
            """.format(name=instrname)
        )
    )

    try:
        build_instr = getattr(instructions, instrname)
    except AttributeError:
        raise TypeError("type %s is not buildable" % typename)

    if add_name is not None:
        try:
            add_instr = getattr(
                instructions,
                '_'.join((typename, add_name)).upper(),
            )
        except AttributeError:
            TypeError("type %s is not addable" % typename)

        dict_['_start_comprehension'] = pattern(
            build_instr, matchany[var], add_instr,
        )(_start_comprehension)
        dict_['_return_value'] = pattern(
            instructions.RETURN_VALUE, startcodes=(IN_COMPREHENSION,),
        )(_return_value)
    else:
        add_instr = None

    dict_['_build'] = pattern(build_instr)(_build)

    if not typename.endswith('s'):
        typename = typename + 's'

    return type(
        'overloaded_' + typename,
        (overloaded_constants(type_),),
        dict_,
    )


overloaded_slices = overloaded_build(slice)
overloaded_lists = overloaded_build(list, 'append')
overloaded_sets = overloaded_build(set, 'add')


# Add a special method for set overloader.
def transform_consts(self, consts):
    consts = super(overloaded_sets, self).transform_consts(consts)
    return tuple(
        # Always pass a thawed set so mutations can happen inplace.
        self.xform(set(const)) if isinstance(const, frozenset) else const
        for const in consts
    )


overloaded_sets.transform_consts = transform_consts
del transform_consts
frozenset_literals = overloaded_sets(frozenset)


overloaded_tuples = overloaded_build(tuple)


# Add a special method for the tuple overloader.
def transform_consts(self, consts):
    consts = super(overloaded_tuples, self).transform_consts(consts)
    return tuple(
        self.xform(const) if isinstance(const, tuple) else const
        for const in consts
    )


overloaded_tuples.transform_consts = transform_consts
del transform_consts


@instance
class islice_literals(CodeTransformer):
    """Transformer that turns slice indexing into an islice object.

    Examples
    --------
    >>> from codetransformer.transformers.literals import islice_literals
    >>> @islice_literals
    ... def f():
    ...     return map(str, (1, 2, 3, 4))[:2]
    ...
    >>> f()
    <itertools.islice at ...>
    >>> tuple(f())
    ('1', '2')
    """
    @pattern(instructions.BINARY_SUBSCR)
    def _binary_subscr(self, instr):
        yield instructions.LOAD_CONST(self._islicer).steal(instr)
        # TOS  = self._islicer
        # TOS1 = k
        # TOS2 = m

        yield instructions.ROT_THREE()
        # TOS  = k
        # TOS1 = m
        # TOS2 = self._islicer

        yield instructions.CALL_FUNCTION(2)
        # TOS  = self._islicer(m, k)

    @staticmethod
    def _islicer(m, k):
        if isinstance(k, slice):
            return islice(m, k.start, k.stop, k.step)

        return m[k]
