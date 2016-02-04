from operator import methodcaller, index, attrgetter
import re
from types import MethodType

from .utils.instance import instance
from .utils.immutable import immutable


#: The default startcode for patterns.
DEFAULT_STARTCODE = 0
mcompile = methodcaller('mcompile')


def _prepr(m):
    if isinstance(m, or_):
        return '(%r)' % m

    return repr(m)


def coerce_ellipsis(p):
    """Convert ... into a matchany
    """
    if p is ...:
        return matchany

    return p


class matchable:
    """Mixin for defining the operators on patterns.
    """
    def __or__(self, other):
        other = coerce_ellipsis(other)
        if self is other:
            return self

        if not isinstance(other, matchable):
            return NotImplemented

        patterns = []
        if isinstance(self, or_):
            patterns.extend(self.matchables)
        else:
            patterns.append(self)
        if isinstance(other, or_):
            patterns.extend(other.matchables)
        else:
            patterns.append(other)

        return or_(*patterns)

    def __ror__(self, other):
        # Flip the order on the or method
        if not isinstance(other, matchable):
            return NotImplemented

        return type(self).__or__(coerce_ellipsis(other), self)

    def __invert__(self):
        return not_(self)

    def __getitem__(self, key):
        try:
            n = index(key)
        except TypeError:
            pass
        else:
            return matchrange(self, n)

        if isinstance(key, tuple) and len(key) in (1, 2):
            return matchrange(self, *key)

        if isinstance(key, modifier):
            return postfix_modifier(self, key)

        raise TypeError('invalid modifier: {0}'.format(key))


class postfix_modifier(immutable, matchable):
    """A pattern with a modifier paired with it.
    """
    __slots__ = 'matchable', 'modifier'

    def mcompile(self):
        return self.matchable.mcompile() + self.modifier.mcompile()

    def __repr__(self):
        return '%r[%r]' % (self.matchable, self.modifier)
    __str__ = __repr__


class meta(matchable):
    """Class for meta patterns and pattern likes. for example: ``matchany``.
    """
    def mcompile(self):
        return self._token

    def __repr__(self):
        return self._token.decode('utf-8')
    __str__ = __repr__


class modifier(meta):
    """Marker class for modifier types.
    """
    pass


@instance
class var(modifier):
    """Modifier that matches zero or more of a pattern.
    """
    _token = b'*'


@instance
class plus(modifier):
    """Modifier that matches one or more of a pattern.
    """
    _token = b'+'


@instance
class option(modifier):
    """Modifier that matches zero or one of a pattern.
    """
    _token = b'?'


class matchrange(immutable, meta, defaults={'m': None}):
    __slots__ = 'matchable', 'n', 'm'

    def mcompile(self):
        m = self.m
        return (
            self.matchable.mcompile() +
            b'{' +
            bytes(str(self.n), 'utf-8') +
            b',' + (b'' if m is None else (b', ' + bytes(str(m), 'utf-8'))) +
            b'}'
        )

    def __repr__(self):
        return '{matchable}[{args}]'.format(
            matchable=_prepr(self.matchable),
            args=', '.join(map(str, filter(bool, (self.n, self.m)))),
        )


@instance
class matchany(meta):
    """Matchable that matches any instruction.
    """
    _token = b'.'

    def __repr__(self):
        return '...'


class seq(immutable, matchable):
    """A sequence of matchables to match in order.

    Parameters
    ----------
    \*matchables : iterable of matchable
        The matchables to match against.
    """
    __slots__ = 'matchables',

    def __new__(cls, *matchables):
        if not matchables:
            raise TypeError('cannot create an empty sequence')

        if len(matchables) == 1:
            return coerce_ellipsis(matchables[0])
        return super().__new__(cls)

    def __init__(self, *matchables):
        self.matchables = tuple(map(coerce_ellipsis, matchables))

    def mcompile(self):
        return b''.join(map(mcompile, self.matchables))

    def __repr__(self):
        return '{cls}({args})'.format(
            cls=type(self).__name__,
            args=', '.join(map(_prepr, self.matchables))
        )


class or_(immutable, matchable):
    """Logical or of multiple matchables.

    Parameters
    ----------
    *matchables : iterable of matchable
        The matchables to or together.
    """
    __slots__ = '*matchables',

    def mcompile(self):
        return b'(' + b'|'.join(map(mcompile, self.matchables)) + b')'

    def __repr__(self):
        return ' | '.join(map(_prepr, self.matchables))


class not_(immutable, matchable):
    """Logical not of a matchable.
    """
    __slots__ = 'matchable',

    def mcompile(self):
        matchable = self.matchable
        if isinstance(matchable, (seq, or_, not_)):
            return b'((?!(' + matchable.mcompile() + b')).)*'

        return b'[^' + matchable.mcompile() + b']'

    def __repr__(self):
        return '~' + _prepr(self.matchable)


class pattern(immutable):
    """
    A pattern of instructions that can be matched against.

    This class is intended to be used as a decorator on methods of
    CodeTransformer subclasses.  It is used to mark that a given method should
    be called on sequences of instructions that match the pattern described by
    the inputs.

    Parameters
    ----------
    \*matchables : iterable of matchable
        The type of instructions to match against.
    startcodes : container of any
        The startcodes where this pattern should be tried.

    Examples
    --------
    Match a single BINARY_ADD instruction::

        pattern(BINARY_ADD)

    Match a single BINARY_ADD followed by a RETURN_VALUE::

        pattern(BINARY_ADD, RETURN_VALUE)

    Match a single BINARY_ADD followed by any other single instruction::

        pattern(BINARY_ADD, matchany)

    Match a single BINARY_ADD followed by any number of instructions::

        pattern(BINARY_ADD, matchany[var])
    """
    __slots__ = 'matchable', 'startcodes', '_compiled'

    def __init__(self, *matchables, startcodes=(DEFAULT_STARTCODE,)):
        if not matchables:
            raise TypeError('expected at least one matchable')
        self.matchable = matchable = seq(*matchables)
        self.startcodes = startcodes
        self._compiled = re.compile(matchable.mcompile())

    def __call__(self, f):
        return boundpattern(self._compiled, self.startcodes, f)

    def __repr__(self):
        return '{cls}(matchable={m!r}, startcodes={s})'.format(
            cls=type(self).__name__,
            m=self.matchable,
            s=self.startcodes,
        )


class boundpattern(immutable):
    """A pattern bound to a function.
    """
    __slots__ = '_compiled', '_startcodes', '_f'

    def __get__(self, instance, owner):
        if instance is None:
            return self

        return type(self)(
            self._compiled,
            self._startcodes,
            MethodType(self._f, instance)
        )

    def __call__(self, compiled_instrs, instrs, startcode):
        if startcode not in self._startcodes:
            raise NoMatch(compiled_instrs, startcode)

        match = self._compiled.match(compiled_instrs)
        if match is None or match.end is 0:
            raise NoMatch(compiled_instrs, startcode)

        mend = match.end()
        return self._f(*instrs[:mend]), mend


class NoMatch(Exception):
    """Indicates that there was no match found in this dispatcher.
    """
    pass


class patterndispatcher(immutable):
    """A set of patterns that can dispatch onto instrs.
    """
    __slots__ = '*patterns',

    def __get__(self, instance, owner):
        if instance is None:
            return self

        return boundpatterndispatcher(
            instance,
            *map(
                methodcaller('__get__', instance, owner),
                self.patterns,
            )
        )


class boundpatterndispatcher(immutable):
    """A set of patterns bound to a transformer.
    """
    __slots__ = 'transformer', '*patterns'

    def _dispatch(self, compiled_instrs, instrs, startcode):
        for p in self.patterns:
            try:
                return p(compiled_instrs, instrs, startcode)
            except NoMatch:
                pass

        raise NoMatch(instrs, startcode)

    def __call__(self, instrs):
        opcodes = bytes(map(attrgetter('opcode'), instrs))
        idx = 0  # The current index into the pre-transformed instrs.
        post_transform = []  # The instrs that have been transformed.
        transformer = self.transformer
        while idx < len(instrs):
            try:
                processed, nconsumed = self._dispatch(
                    opcodes[idx:],
                    instrs[idx:],
                    # NOTE: do not remove this attribute access
                    # self._dispatch can mutate the value of the startcode
                    transformer.startcode,
                )
            except NoMatch:
                post_transform.append(instrs[idx])
                idx += 1
            else:
                post_transform.extend(processed)
                idx += nconsumed
        return tuple(post_transform)
