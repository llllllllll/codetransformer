from operator import methodcaller
import re
from types import MethodType

from .utils.immutable import immutable


mcompile = methodcaller('mcompile')


class matchable:
    """Mixin for defining the operators on patterns.
    """
    def __or__(self, other):
        if self is other:
            return self

        if not isinstance(other, matchable):
            return NotImplemented

        patterns = []
        if isinstance(self, or_):
            patterns.extend(self.patterns)
        else:
            patterns.append(self)
        if isinstance(other, or_):
            patterns.extend(other.patterns)
        else:
            patterns.append(other)

        return or_(*patterns)

    def __ror__(self, other):
        # Flip the order on the or method
        return type(self).__or__(other, self)

    def __invert__(self):
        return not_(self)


class seq(immutable, matchable):
    """A sequence of matchables to match in order.

    Parameters
    ----------
    *matchables : iterable of matchable
        The matchables to match against.
    """
    __slots__ = '*matchables',

    def mcompile(self):
        return b''.join(map(mcompile, self.matchables))


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


class not_(immutable):
    """Logical not of a matchable.
    """
    __slots__ = 'matchable',

    def mcompile(self):
        matchable = self.matchable
        if isinstance(matchable, (seq, or_, not_)):
            return b'((?!(' + matchable.mcompile() + b')).)*'

        return b'[^' + matchable.mcompile() + b']'


class pattern(immutable, defaults={'startcodes': (0,)}):
    """A pattern of instructions that can be matched against.

    Parameters
    ----------
    *matchables : iterable of matchable
        The type of instructions to match against.
    startcode : container of any
        The startcodes where this pattern should be tried.
    """
    __slots__ = 'compiled', 'startcodes'

    def __new__(cls, *matchables, startcodes=(0,)):
        if not matchables:
            raise TypeError('expected at least one matchable')

        self = super().__new__(cls)
        self.__init__(
            re.compile(
                (seq(*matchables)
                 if len(matchables) > 1 else
                 matchables[0]).mcompile(),
            ),
            startcodes,
        )
        return self

    def __call__(self, f):
        return boundpattern(self.compiled, self.startcodes, f)


class boundpattern(immutable):
    """A pattern bound to a function.
    """
    __slots__ = '_compiled', '_startcodes', '_f'

    def __get__(self, instance, owner):
        return type(self)(
            self._compiled,
            self._startcodes,
            MethodType(self._f, instance)
        )

    def __call__(self, compiled_instrs, instrs, startcode):
        match = self._compiled.match(compiled_instrs)
        if match is None or match.end is 0:
            raise KeyError(compiled_instrs, startcode)

        mend = match.end()
        return self._f(*instrs[:mend]), mend


class patterndispatcher(immutable):
    """A set of boundpatterns that can dispatch onto instrs.
    """
    __slots__ = '*_boundpatterns',

    def __get__(self, instance, owner):
        return type(self)(*map(
            methodcaller('__get__', instance, owner),
            self._boundpatterns,
        ))

    def __call__(self, compiled_instrs, instrs, startcode):
        for p in self._boundpatterns:
            try:
                return p(compiled_instrs, instrs, startcode)
            except KeyError:
                pass

        raise KeyError(instrs, startcode)
